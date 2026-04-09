"""
AirQRT - 摄像头接收端 (FEC版)
使用物理摄像头扫描二维码
支持 FEC 丢帧恢复、帧变化检测、崩溃保护
"""

import os
import json
import gzip
import base64
import hashlib
import cv2
import time
import math
import shutil

from fec_utils import recover_data_shards

# ===== 配置 =====
OUTPUT_DIR = "./received_files"
CAMERA_INDEX = 0  # 默认摄像头索引
MAX_CONSECUTIVE_READ_FAILURES = 15   # 连续读帧失败多少次后重开摄像头
CAMERA_REOPEN_DELAY_SEC = 1.0       # 重开摄像头前等待秒数
MAX_DECODE_ERRORS = 50               # 连续解码异常上限（达到后仅打印警告）

# =================

def clean_output_dir():
    """清空并重建输出目录，确保接收前没有旧文件"""
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def ensure_output_dir():
    """确保输出目录存在"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def compute_checksum(data):
    """计算校验和"""
    if isinstance(data, str):
        data = data.encode()
    return hashlib.md5(data).hexdigest()[:6]

class QRReceiver:
    def __init__(self):
        self.current_session = None
        self.total_blocks = 0
        self.total_data_shards = 0
        self.payload_length = 0
        self.shard_size = 0
        self.received_count = 0
        self.last_data_hash = ""
        self.blocks = {}            # {block_index: {"k": int, "m": int, "shards": {idx: bytes}, "decoded": [bytes]}}
        self.decoded_blocks = 0

        # 统计信息
        self.scan_count = 0
        self.valid_count = 0
        self.duplicate_count = 0
        self.error_count = 0

    def process_frame(self, frame_data):
        """处理接收到的帧数据"""
        self.scan_count += 1

        try:
            # 检测数据是否变化（避免处理相同的二维码）
            data_hash = hashlib.md5(frame_data.encode()).hexdigest()[:8]
            if data_hash == self.last_data_hash:
                self.duplicate_count += 1
                return {"status": "duplicate"}

            self.last_data_hash = data_hash

            data = json.loads(frame_data)

            session = data["s"]
            block_index = data["b"]
            shard_index = data["x"]
            data_shards = data["k"]
            parity_shards = data["m"]
            total_blocks = data["t"]
            total_data_shards = data["n"]
            payload_length = data["l"]
            shard_size = data["z"]
            chunk = data["d"]
            checksum = data.get("c", "")

            # 验证校验和
            if checksum and compute_checksum(chunk) != checksum:
                self.error_count += 1
                return {"status": "checksum_error", "index": shard_index}

            shard_bytes = base64.b64decode(chunk)
            if len(shard_bytes) != shard_size:
                self.error_count += 1
                return {"status": "size_error", "index": shard_index}

            # 如果是新会话，重置
            if self.current_session != session:
                self.current_session = session
                self.total_blocks = total_blocks
                self.total_data_shards = total_data_shards
                self.payload_length = payload_length
                self.shard_size = shard_size
                self.received_count = 0
                self.last_data_hash = data_hash
                self.blocks = {}
                self.decoded_blocks = 0
                print(f"\n{'='*50}")
                print(f"检测到新会话: {session}")
                print(f"总块数: {total_blocks}")
                print(f"数据帧数: {total_data_shards}")
                print(f"冗余比例: 每块 {data_shards} 数据 + {parity_shards} 冗余")
                print(f"{'='*50}")

            # 初始化块
            block = self.blocks.setdefault(
                block_index,
                {"k": data_shards, "m": parity_shards, "shards": {}, "decoded": None},
            )

            # 存储该帧（避免重复）
            if shard_index not in block["shards"]:
                block["shards"][shard_index] = shard_bytes
                self.received_count = sum(len(item["shards"]) for item in self.blocks.values())
                self.valid_count += 1

                # 尝试恢复该块
                if block["decoded"] is None and len(block["shards"]) >= block["k"]:
                    try:
                        block["decoded"] = recover_data_shards(
                            block["shards"],
                            block["k"],
                            block["m"],
                            self.shard_size,
                        )
                        self.decoded_blocks = sum(1 for item in self.blocks.values() if item["decoded"] is not None)
                    except Exception:
                        block["decoded"] = None

                progress = (self.decoded_blocks / self.total_blocks) * 100 if self.total_blocks > 0 else 0
                missing = self.get_missing_blocks()

                print(f"\r接收块: {self.decoded_blocks}/{self.total_blocks} ({progress:.1f}%) "
                      f"| 块#{block_index+1} 分片#{shard_index+1} | 待恢复: {len(missing)}块", end='')

                # 检查是否接收完成
                if self.decoded_blocks == self.total_blocks:
                    print(f"\n\n所有块接收完成！")
                    self.print_statistics()
                    print("正在重组数据...")
                    result = self.reconstruct_files()
                    return result

                return {"status": "new_frame", "index": shard_index, "progress": progress, "block": block_index}
            else:
                self.duplicate_count += 1
                return {"status": "duplicate", "index": shard_index, "block": block_index}

        except json.JSONDecodeError:
            self.error_count += 1
            return {"status": "json_error"}
        except Exception as e:
            self.error_count += 1
            return {"status": "error", "message": str(e)}

    def get_missing_blocks(self):
        """获取尚未可恢复的块列表"""
        missing = []
        for block_index in range(self.total_blocks):
            block = self.blocks.get(block_index)
            if not block or block["decoded"] is None:
                missing.append(block_index)
        return missing

    def get_missing_frames_display(self):
        """获取格式化的缺失块显示字符串"""
        if not self.current_session or self.total_blocks == 0:
            return ""
        missing = self.get_missing_blocks()
        if not missing:
            return "All blocks recoverable!"
        parts = []
        for block_index in missing[:5]:
            block = self.blocks.get(block_index)
            if not block:
                need = "?"
            else:
                need = max(0, block["k"] - len(block["shards"]))
            parts.append(f"B{block_index + 1}:need {need}")
        more = f"... (+{len(missing)-5} more)" if len(missing) > 5 else ""
        return f"Pending: {', '.join(parts)} {more}".strip()

    def print_statistics(self):
        """打印统计信息"""
        print(f"\n统计信息:")
        print(f"  总扫描次数: {self.scan_count}")
        print(f"  有效帧数: {self.valid_count}")
        print(f"  重复帧数: {self.duplicate_count}")
        print(f"  错误帧数: {self.error_count}")
        if self.scan_count > 0:
            efficiency = (self.valid_count / self.scan_count) * 100
            print(f"  扫描效率: {efficiency:.1f}%")

    def reconstruct_files(self):
        """从 FEC 恢复的块中重组文件"""
        try:
            recovered_chunks = []
            for block_index in range(self.total_blocks):
                block = self.blocks.get(block_index)
                if not block or block["decoded"] is None:
                    raise ValueError(f"块 {block_index + 1} 尚未恢复")
                recovered_chunks.extend(block["decoded"])

            # 只取实际的数据分片数
            recovered_chunks = recovered_chunks[:self.total_data_shards]
            payload = b"".join(recovered_chunks)[:self.payload_length]

            # 解压 gzip
            raw = gzip.decompress(payload)
            files_dict = json.loads(raw)

            ensure_output_dir()

            file_count = 0
            total_bytes = 0
            for filename, b64_content in files_dict.items():
                filepath = os.path.join(OUTPUT_DIR, filename)
                content = base64.b64decode(b64_content)

                with open(filepath, "wb") as f:
                    f.write(content)

                file_count += 1
                total_bytes += len(content)
                print(f"  已保存: {filename} ({len(content)} 字节)")

            print(f"\n成功保存 {file_count} 个文件 (共 {total_bytes} 字节)")
            print(f"保存位置: {os.path.abspath(OUTPUT_DIR)}")
            return {"status": "completed", "success": True, "file_count": file_count, "total_bytes": total_bytes}

        except Exception as e:
            print(f"\n重组文件时出错: {e}")
            return {"status": "error", "success": False, "message": str(e)}

    def reset(self):
        """重置接收器状态"""
        self.current_session = None
        self.total_blocks = 0
        self.total_data_shards = 0
        self.payload_length = 0
        self.shard_size = 0
        self.received_count = 0
        self.last_data_hash = ""
        self.blocks = {}
        self.decoded_blocks = 0
        self.scan_count = 0
        self.valid_count = 0
        self.duplicate_count = 0
        self.error_count = 0

def open_camera():
    """打开摄像头并设置参数"""
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        return None

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    return cap

def draw_progress_bar(frame, progress, x, y, width, height):
    """在画面上绘制进度条"""
    cv2.rectangle(frame, (x, y), (x + width, y + height), (50, 50, 50), -1)
    fill_width = int(width * progress)
    color = (0, 255, 0) if progress < 1 else (0, 200, 255)
    cv2.rectangle(frame, (x, y), (x + fill_width, y + height), color, -1)
    cv2.rectangle(frame, (x, y), (x + width, y + height), (255, 255, 255), 1)

def main():
    print("=" * 60)
    print("AirQRT - 摄像头接收端 (FEC版)")
    print("=" * 60)
    print(f"\n接收到的文件将保存到: {OUTPUT_DIR}")
    print("按 'Q' 键或 'ESC' 键退出")
    print("按 'R' 键重置接收器\n")

    clean_output_dir()
    print("已清空接收文件夹，准备接收新文件")

    cap = open_camera()
    if cap is None:
        print(f"错误: 无法打开摄像头 (索引 {CAMERA_INDEX})")
        print("请尝试修改 CAMERA_INDEX 为其他值 (0, 1, 2...)")
        return

    # 创建二维码检测器
    detector = cv2.QRCodeDetector()

    receiver = QRReceiver()

    # 帧率计算
    fps_time = time.time()
    fps_count = 0
    current_fps = 0
    consecutive_read_failures = 0
    consecutive_decode_errors = 0

    print("摄像头已启动，等待扫描二维码...")

    try:
        while True:
            # === 读帧（带崩溃保护） ===
            try:
                ret, frame = cap.read()
            except Exception as e:
                print(f"\n警告: 摄像头读取异常: {e}")
                ret = False

            if not ret:
                consecutive_read_failures += 1
                if consecutive_read_failures == 1:
                    print("警告: 摄像头读取失败，正在重试...")
                if consecutive_read_failures >= MAX_CONSECUTIVE_READ_FAILURES:
                    print("警告: 摄像头连续读取失败，正在尝试重新打开...")
                    try:
                        cap.release()
                    except Exception:
                        pass
                    time.sleep(CAMERA_REOPEN_DELAY_SEC)
                    cap = open_camera()
                    consecutive_read_failures = 0
                    if cap is None:
                        print("警告: 摄像头重新打开失败，将继续重试...")
                        time.sleep(CAMERA_REOPEN_DELAY_SEC)
                        cap = cv2.VideoCapture(CAMERA_INDEX)
                    continue
                time.sleep(0.05)
                continue

            consecutive_read_failures = 0

            # 计算FPS
            fps_count += 1
            if time.time() - fps_time >= 1.0:
                current_fps = fps_count
                fps_count = 0
                fps_time = time.time()

            # === 二维码解码（带崩溃保护） ===
            data = None
            bbox = None
            try:
                data, bbox, _ = detector.detectAndDecode(frame)
            except Exception as e:
                consecutive_decode_errors += 1
                if consecutive_decode_errors <= 3:
                    print(f"\n警告: 二维码解码异常: {e}")
                elif consecutive_decode_errors == MAX_DECODE_ERRORS:
                    print(f"\n警告: 已累计 {MAX_DECODE_ERRORS} 次解码异常，后续将静默忽略")
                # 不退出，继续下一帧

            frame_height, frame_width = frame.shape[:2]
            status_text = ""
            status_color = (255, 255, 255)

            if data:
                consecutive_decode_errors = 0  # 成功解码则重置计数器

                try:
                    result = receiver.process_frame(data)
                except Exception as e:
                    # 兜底保护：process_frame 不应该抛异常，但以防万一
                    print(f"\n警告: 帧处理异常: {e}")
                    result = {"status": "error", "message": str(e)}

                if result["status"] == "new_frame":
                    status_text = f"New Shard B{result['block']+1} #{result['index']+1}"
                    status_color = (0, 255, 0)
                elif result["status"] == "duplicate":
                    status_text = "Duplicate (waiting...)"
                    status_color = (0, 255, 255)
                elif result["status"] == "completed":
                    # 显示完成信息
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (50, frame_height//2 - 60),
                                  (frame_width - 50, frame_height//2 + 60), (0, 100, 0), -1)
                    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

                    cv2.putText(frame, "Transfer Complete!",
                                (frame_width//2 - 200, frame_height//2),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
                    cv2.putText(frame, "Press any key to continue, Q to quit",
                                (frame_width//2 - 220, frame_height//2 + 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

                    cv2.imshow("QR Code Receiver - Camera", frame)
                    key = cv2.waitKey(0)

                    if key in [ord('q'), ord('Q'), 27]:
                        break
                    else:
                        receiver.reset()
                        print("\n等待下一个传输...\n")
                        continue
                elif result["status"] == "error":
                    status_text = f"Error: {result.get('message', '?')[:30]}"
                    status_color = (0, 0, 255)

                # 绘制检测框
                if bbox is not None:
                    try:
                        bbox_int = bbox.astype(int)
                        cv2.polylines(frame, [bbox_int], True, (0, 255, 0), 3)
                    except Exception:
                        pass

            # 绘制界面
            top_bar_height = 100 if receiver.current_session else 70
            cv2.rectangle(frame, (0, 0), (frame_width, top_bar_height), (40, 40, 40), -1)

            if receiver.current_session:
                session_text = f"Session: {receiver.current_session}"
                cv2.putText(frame, session_text, (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                progress = receiver.decoded_blocks / receiver.total_blocks if receiver.total_blocks > 0 else 0
                progress_text = f"{receiver.decoded_blocks}/{receiver.total_blocks} blocks ({progress*100:.0f}%)"
                cv2.putText(frame, progress_text, (10, 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

                draw_progress_bar(frame, progress, 250, 40, 300, 20)

                stats_text = f"Scans: {receiver.scan_count} | Valid: {receiver.valid_count} | Dup: {receiver.duplicate_count}"
                cv2.putText(frame, stats_text, (570, 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

                missing_text = receiver.get_missing_frames_display()
                if missing_text:
                    missing_color = (0, 255, 255) if "Pending" in missing_text else (0, 255, 0)
                    cv2.putText(frame, missing_text, (10, 90),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, missing_color, 2)
            else:
                cv2.putText(frame, "Waiting for QR Code...", (10, 45),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 255), 2)

            if status_text:
                cv2.putText(frame, status_text, (frame_width - 350, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

            # 底部信息栏
            cv2.rectangle(frame, (0, frame_height - 35), (frame_width, frame_height), (40, 40, 40), -1)
            cv2.putText(frame, f"FPS: {current_fps} | Camera Mode | Press 'Q' to Quit, 'R' to Reset",
                        (10, frame_height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

            cv2.imshow("QR Code Receiver - Camera", frame)

            key = cv2.waitKey(1)
            if key in [ord('q'), ord('Q'), 27]:
                print("\n\n用户停止接收")
                if receiver.current_session:
                    receiver.print_statistics()
                break
            elif key in [ord('r'), ord('R')]:
                receiver.reset()
                print("\n接收器已重置\n")

    except KeyboardInterrupt:
        print("\n\n检测到 Ctrl+C，停止接收")
        if receiver.current_session:
            receiver.print_statistics()
    except Exception as e:
        # 全局兜底：任何未预期的异常都不应该让程序无声死亡
        print(f"\n\n严重错误: {e}")
        print("程序将安全退出...")
        if receiver.current_session:
            receiver.print_statistics()
    finally:
        try:
            cap.release()
        except Exception:
            pass
        cv2.destroyAllWindows()
        print("程序已退出")

if __name__ == "__main__":
    main()
