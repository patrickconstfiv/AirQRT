import os
import json
import gzip
import base64
import uuid
import time
import hashlib
import math
import qrcode
import cv2
import numpy as np

from fec_utils import encode_parity_shards

# ===== 配置 =====
SOURCE_DIR = "./send_dir"
CHUNK_SIZE = 300      # 每个数据分片的原始字节数（减小以提高识别率）
FRAME_FPS = 20        # 默认帧率 (FPS)
FRAME_MIN_FPS = 5     # 最低帧率 (FPS)
FRAME_MAX_FPS = 60    # 最高帧率 (FPS)
FRAME_STEP_FPS = 5    # 每次调速步长 (FPS)
QR_WINDOW_SIZE = 700  # 二维码窗口大小（像素）
QR_ERROR_LEVEL = 'M'  # 纠错级别: L(7%), M(15%), Q(25%), H(30%)
FEC_DATA_SHARDS = 50  # 每个 FEC 块包含的数据帧数
FEC_REDUNDANCY_RATIO = 0.30  # FEC 冗余比例 30%

# =================

# 纠错级别映射
ERROR_LEVELS = {
    'L': qrcode.constants.ERROR_CORRECT_L,
    'M': qrcode.constants.ERROR_CORRECT_M,
    'Q': qrcode.constants.ERROR_CORRECT_Q,
    'H': qrcode.constants.ERROR_CORRECT_H,
}

def read_and_compress(directory):
    """读取目录中的所有文件并压缩"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"已创建目录: {directory}")
        print("请将要发送的文件放入此目录后重新运行程序")
        return None
    
    data = {}
    file_count = 0
    total_size = 0
    
    for name in os.listdir(directory):
        path = os.path.join(directory, name)
        if os.path.isfile(path):
            with open(path, "rb") as f:
                content = f.read()
                data[name] = content
                file_count += 1
                total_size += len(content)
    
    if not data:
        print(f"目录 {directory} 中没有文件！")
        return None
    
    print(f"共发现 {file_count} 个文件，总大小: {total_size} 字节")
    
    raw = json.dumps(
        {k: base64.b64encode(v).decode() for k, v in data.items()},
        separators=(',', ':'),
    ).encode()

    compressed = gzip.compress(raw, compresslevel=9)
    
    print(f"压缩后大小: {len(compressed)} 字节")
    
    return compressed

def read_and_compress_files(file_paths):
    """读取指定文件列表并压缩（供GUI使用）"""
    data = {}
    for path in file_paths:
        if os.path.isfile(path):
            name = os.path.basename(path)
            with open(path, "rb") as f:
                data[name] = f.read()
    if not data:
        return None
    raw = json.dumps(
        {k: base64.b64encode(v).decode() for k, v in data.items()},
        separators=(',', ':'),
    ).encode()
    return gzip.compress(raw, compresslevel=9)

def split_chunks(data, size):
    """将字节数据分块"""
    return [data[i:i + size] for i in range(0, len(data), size)]

def compute_checksum(data):
    """计算简单校验和（用于帧验证）"""
    if isinstance(data, str):
        data = data.encode()
    return hashlib.md5(data).hexdigest()[:6]

def pad_chunk(chunk, size):
    """将分片补齐到固定大小"""
    if len(chunk) >= size:
        return chunk
    return chunk + b"\0" * (size - len(chunk))

def build_transport_frames(payload, session_id):
    """
    构建带 FEC 的传输帧列表，并做跨块交织。

    将压缩后的原始字节数据切分为多个 FEC 块，每块包含数据帧和冗余帧。
    最终将所有块的帧交织排列，使得连续丢帧不会集中在同一个块上。
    """
    data_chunks = split_chunks(payload, CHUNK_SIZE)
    total_data_chunks = len(data_chunks)
    total_blocks = math.ceil(total_data_chunks / FEC_DATA_SHARDS)

    block_frames = []
    total_parity_frames = 0

    for block_index in range(total_blocks):
        start = block_index * FEC_DATA_SHARDS
        end = min(start + FEC_DATA_SHARDS, total_data_chunks)
        block_data = data_chunks[start:end]
        data_shards = len(block_data)
        parity_shards = max(1, math.ceil(data_shards * FEC_REDUNDANCY_RATIO))

        # 补齐到固定大小后生成冗余
        padded_data = [pad_chunk(chunk, CHUNK_SIZE) for chunk in block_data]
        parity_data = encode_parity_shards(padded_data, parity_shards)

        frames = []
        for shard_index, shard_bytes in enumerate(padded_data + parity_data):
            shard_b64 = base64.b64encode(shard_bytes).decode()
            frame = {
                "s": session_id,              # session
                "b": block_index,             # block index
                "x": shard_index,             # shard index in block
                "k": data_shards,             # data shards in block
                "m": parity_shards,           # parity shards in block
                "t": total_blocks,            # total blocks
                "n": total_data_chunks,       # total data shards across all blocks
                "l": len(payload),            # payload length (compressed bytes)
                "z": CHUNK_SIZE,              # shard size
                "c": compute_checksum(shard_b64),  # checksum
                "d": shard_b64,               # shard payload (base64)
            }
            frames.append(frame)

        block_frames.append(frames)
        total_parity_frames += parity_shards

    # 跨块交织：轮流从每个块取一帧
    interleaved_frames = []
    max_block_len = max(len(frames) for frames in block_frames)
    for round_index in range(max_block_len):
        for frames in block_frames:
            if round_index < len(frames):
                interleaved_frames.append(frames[round_index])

    return interleaved_frames, total_data_chunks, total_parity_frames, total_blocks

def create_qr_image(text):
    """创建二维码图像（返回 numpy 数组，供 CLI 使用）"""
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_LEVELS.get(QR_ERROR_LEVEL, qrcode.constants.ERROR_CORRECT_M),
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    return np.array(img.convert("RGB"))

def create_qr_pil_image(text):
    """创建二维码 PIL 图像（供 GUI 使用）"""
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_LEVELS.get(QR_ERROR_LEVEL, qrcode.constants.ERROR_CORRECT_M),
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white")

def show_frame(canvas, wait_ms):
    """显示帧并等待，返回按键值"""
    cv2.imshow("QR Code Sender", canvas)
    key = cv2.waitKey(wait_ms)
    return key

def create_qr_canvas(qr_img, frame_info, frame_num, total_frames, bg_color=(255, 255, 255)):
    """创建带边框和信息的二维码画布"""
    height, width = qr_img.shape[:2]
    scale = (QR_WINDOW_SIZE - 40) / max(height, width)
    new_width = int(width * scale)
    new_height = int(height * scale)
    qr_resized = cv2.resize(qr_img, (new_width, new_height), interpolation=cv2.INTER_NEAREST)

    canvas_height = QR_WINDOW_SIZE + 100
    canvas = np.ones((canvas_height, QR_WINDOW_SIZE, 3), dtype=np.uint8)
    canvas[:] = bg_color

    y_offset = 70
    x_offset = (QR_WINDOW_SIZE - new_width) // 2
    canvas[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = qr_resized

    # 进度条
    progress = (frame_num + 1) / total_frames
    bar_width = QR_WINDOW_SIZE - 40
    bar_height = 20
    bar_x = 20
    bar_y = 40

    cv2.rectangle(canvas, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (200, 200, 200), -1)
    fill_width = int(bar_width * progress)
    cv2.rectangle(canvas, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height), (0, 180, 0), -1)
    cv2.rectangle(canvas, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (0, 0, 0), 2)

    frame_text = f"Frame {frame_num + 1}/{total_frames}"
    cv2.putText(canvas, frame_text, (20, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    percent_text = f"{progress*100:.0f}%"
    text_size = cv2.getTextSize(percent_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
    cv2.putText(canvas, percent_text, (QR_WINDOW_SIZE - text_size[0] - 20, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    cv2.putText(canvas, frame_info, (10, canvas_height - 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 80, 80), 1)
    cv2.putText(canvas, "Q:Quit | +/-:Speed | S:Select | F:Segment", (10, canvas_height - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 200), 1)

    return canvas

def main():
    global FRAME_FPS

    print("=" * 60)
    print("AirQRT - 发送端 (FEC版)")
    print("=" * 60)

    payload = read_and_compress(SOURCE_DIR)

    if payload is None:
        return

    session_id = str(uuid.uuid4())[:8]

    transport_frames, total_data_chunks, total_parity_frames, total_blocks = \
        build_transport_frames(payload, session_id)
    total = len(transport_frames)

    full_checksum = compute_checksum(payload)

    print(f"\n会话ID: {session_id}")
    print(f"数据校验: {full_checksum}")
    print(f"数据帧数: {total_data_chunks}")
    print(f"冗余帧数: {total_parity_frames} (+{(total_parity_frames / max(1, total_data_chunks)) * 100:.0f}%)")
    print(f"传输帧总数: {total}")
    print(f"FEC 分块数: {total_blocks} (每块最多 {FEC_DATA_SHARDS} 数据帧)")
    print(f"每帧原始分片: {CHUNK_SIZE} 字节")
    print(f"默认帧率: {FRAME_FPS} FPS")
    print(f"纠错级别: {QR_ERROR_LEVEL}")
    print(f"\n按 'Q' 或 'ESC' 退出")
    print(f"按 '+' 加速 (最高 {FRAME_MAX_FPS} FPS) / '-' 减速 (最低 {FRAME_MIN_FPS} FPS)")
    print(f"开始播放...\n")

    # 预生成所有二维码图像
    print("正在预生成二维码...")
    qr_images = []
    for i, frame in enumerate(transport_frames):
        text = json.dumps(frame, separators=(',', ':'))
        qr_img = create_qr_image(text)
        qr_images.append(qr_img)

        if (i + 1) % 20 == 0 or i == total - 1:
            print(f"  预生成: {i+1}/{total}")

    print("预生成完成！\n")

    try:
        cycle = 0
        while True:
            cycle += 1
            print(f"第 {cycle} 轮播放...")

            for i in range(total):
                frame_meta = transport_frames[i]
                block_no = frame_meta["b"] + 1
                shard_no = frame_meta["x"] + 1
                block_total = frame_meta["k"] + frame_meta["m"]
                frame_info = (
                    f"Session:{session_id} | Cycle:{cycle} | "
                    f"B{block_no}/{total_blocks} S{shard_no}/{block_total}"
                )

                canvas = create_qr_canvas(qr_images[i], frame_info, i, total)
                key = show_frame(canvas, 1000 // FRAME_FPS)

                if key in [ord('q'), ord('Q'), 27]:
                    print("\n用户停止播放")
                    cv2.destroyAllWindows()
                    return

                if key == ord('+') or key == ord('='):
                    FRAME_FPS = min(FRAME_MAX_FPS, FRAME_FPS + FRAME_STEP_FPS)
                    print(f"  加速: {FRAME_FPS} FPS")
                elif key == ord('-') or key == ord('_'):
                    FRAME_FPS = max(FRAME_MIN_FPS, FRAME_FPS - FRAME_STEP_FPS)
                    print(f"  减速: {FRAME_FPS} FPS")

                if (i + 1) % 10 == 0 or i == total - 1:
                    print(f"  已播放: {i+1}/{total} 帧")

            print(f"第 {cycle} 轮播放完成\n")

    except KeyboardInterrupt:
        print("\n\n检测到 Ctrl+C，停止播放")
    finally:
        cv2.destroyAllWindows()
        print("程序已退出")

if __name__ == "__main__":
    main()
