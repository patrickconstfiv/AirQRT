<p align="center">
  <img src="icon.png" width="128" alt="AirQRT logo">
</p>

<h1 align="center">AirQRT</h1>

<p align="center">
  <b>通过二维码实现 Windows 电脑间的完全离线文件传输</b><br>
  无需网络，无需数据线，无需 U 盘。只需屏幕和摄像头。
</p>

<p align="center">
  <a href="README.md">English</a> · <b>中文</b> · <a href="README.ja.md">日本語</a> · <a href="README.ru.md">Русский</a>
</p>

---

## 工作原理

一台电脑作为**发送端**，在屏幕上高速显示二维码流；  
另一台电脑作为**接收端**，用摄像头对准屏幕扫描二维码。

数据经过压缩、分帧，并使用 **Reed-Solomon FEC（前向纠错码）** 保护——即使摄像头漏扫了部分帧，文件仍能完整恢复。

## 下载

**只想直接使用？** 下载打包好的 `.exe`，无需安装 Python：

> **[⬇ 下载 AirQRT (Windows .exe)](../../releases/latest)**

解压后双击运行即可。

## 功能特性

- **完全离线** — 不需要 Wi-Fi、蓝牙或任何网络连接
- **一键图形界面** — 暗色终端风格 UI，支持拖拽文件
- **FEC 纠错恢复** — 基于 GF(256) 上的 Reed-Solomon 编码，容忍丢帧
- **跨块交织** — 连续丢帧分散到不同块，提升恢复能力
- **帧率可调** — 根据摄像头扫描速度动态调整
- **按块定向补发** — 点击指定块重新发送缺失帧
- **多语言界面** — English、中文、Русский、日本語

## 快速开始（源码运行）

### 环境要求

- Python 3.9+
- 接收端需要摄像头

### 安装

```bash
git clone https://github.com/YOUR_USERNAME/AirQRT.git
cd AirQRT
pip install -r requirements.txt
```

### 运行

```bash
python app.py
```

启动后 GUI 包含两个标签页：**发送** 和 **接收**。

#### 发送文件

1. 切换到 **发送** 标签页
2. 点击 **添加文件**（或拖拽文件到窗口）
3. 根据需要调整帧率
4. 点击 **[ 开始发送 ]**

#### 接收文件

1. 切换到 **接收** 标签页
2. 将摄像头对准发送端屏幕
3. 点击 **[ 开始接收 ]**
4. 传输完成后文件保存在 `received_files/` 目录

## 打包为可执行文件

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "AirQRT" --icon=icon.ico --hidden-import=windnd app.py
```

生成的 `.exe` 位于 `dist/` 目录下。

## FEC 纠错机制

系统使用基于 Reed-Solomon 码的块级 FEC：

| 参数 | 默认值 |
|------|--------|
| 每块数据帧数 | 50 |
| 冗余比例 | 30% |
| 二维码纠错等级 | M (15%) |

**示例：** 一个包含 50 个数据帧的块会额外生成 15 个冗余帧（共 65 帧）。  
只要扫到其中**任意** 50 帧，即可恢复全部数据——无论漏掉的是哪些帧。

## 性能参考

| 文件大小 | 大约耗时 |
|---------|---------|
| 10 KB | ~30 秒 |
| 50 KB | ~2 分钟 |
| 100 KB | ~4 分钟 |

适合传输小文件（< 500 KB）。较大文件建议先压缩再传输。

## 参数调优

编辑 `sender.py` 调整以下参数：

```python
CHUNK_SIZE = 300            # 每个数据分片的字节数（越小越容易扫描）
FRAME_FPS = 20              # 默认帧率
FEC_DATA_SHARDS = 50        # 每个 FEC 块的数据帧数
FEC_REDUNDANCY_RATIO = 0.30 # 30% 冗余开销
QR_ERROR_LEVEL = 'M'        # L / M / Q / H
```

## 常见问题

| 问题 | 解决方法 |
|------|---------|
| 摄像头无法打开 | 修改 `receiver_camera.py` 中的 `CAMERA_INDEX` 为 `1` 或 `2` |
| 扫描率低 | 减小 `CHUNK_SIZE`，降低帧率，或增大 `FEC_REDUNDANCY_RATIO` |
| 大文件传输太慢 | 先压缩文件（zip/7z），再传输压缩包 |

## 项目结构

```
├── app.py               # 图形界面应用 (Tkinter)
├── sender.py            # 文件压缩、二维码编码、FEC 分帧
├── receiver_camera.py   # 摄像头扫描、二维码解码、FEC 恢复
├── fec_utils.py         # GF(256) 上的 Reed-Solomon 编解码器
├── icon.png             # 应用图标
├── build_exe.bat        # 一键打包脚本
├── requirements.txt     # Python 依赖
└── received_files/      # 接收文件输出目录
```

## 许可证

本项目开源。详情见 [LICENSE](LICENSE)。

---

<p align="center"><i>为那些找不到 U 盘的时刻而生。</i></p>
