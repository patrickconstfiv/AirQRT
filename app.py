"""
AirQRT — 统一 GUI (暗色终端风格 · 多语言)
"""

import os
import sys
import json
import uuid
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import threading
import time

from sender import (
    read_and_compress_files,
    build_transport_frames,
    create_qr_pil_image,
    FRAME_FPS,
    FRAME_MIN_FPS,
    FRAME_MAX_FPS,
    FRAME_STEP_FPS,
)
from receiver_camera import QRReceiver, clean_output_dir, OUTPUT_DIR


# ══════════════════════════════════════════════════════════════
#  颜色主题 (终端机风格 — 纯单色系)
# ══════════════════════════════════════════════════════════════
C = {
    "bg":           "#0c0c0c",
    "bg_secondary": "#1a1a2e",
    "bg_input":     "#16213e",
    "fg":           "#e0e0e0",
    "fg_dim":       "#7a7a8e",
    "fg_bright":    "#ffffff",
    "accent":       "#00ff41",
    "accent_dim":   "#00cc33",
    "yellow":       "#ffcc00",
    "border":       "#2a2a3e",
    "tab_active":   "#00ff41",
    "tab_inactive": "#7a7a8e",
    "block_normal": "#2a2a3e",
    "block_active": "#00ff41",
    "btn":          "#1a1a2e",
    "btn_hl":       "#2a2a3e",
    "progress_bg":  "#1a1a2e",
    "progress_fg":  "#00ff41",
}

FONT = "Consolas"
FONT_CN = "Microsoft YaHei UI"

# ══════════════════════════════════════════════════════════════
#  国际化 (i18n) — EN / 中文 / Русский / 日本語
# ══════════════════════════════════════════════════════════════
LANGUAGES = [
    ("en", "EN"),
    ("zh", "中文"),
    ("ru", "RU"),
    ("ja", "JA"),
]

I18N = {
    "en": {
        "title":             "AirQRT",
        "tab_send":          "SEND",
        "tab_recv":          "RECV",
        "send_title":        "[ SENDER ]",
        "recv_title":        "[ RECEIVER ]",
        "drop_hint":         'Click "Add Files" or drag files here',
        "no_files":          "No files added",
        "add_file":          "Add Files",
        "add_folder":        "Add Folder",
        "remove_sel":        "Remove",
        "clear_all":         "Clear All",
        "fps_label":         "FPS",
        "start_send":        "[ START SEND ]",
        "stop_send":         "[ STOP ]",
        "preparing":         "[ PREPARING... ]",
        "status_ready":      "> Ready",
        "status_reading":    "> Reading and compressing files...",
        "status_building":   "> Building transport frames...",
        "status_qr_gen":     "> Generating QR codes {}%...",
        "status_stopped":    "> Stopped",
        "sending_title":     "[ SENDING... ]",
        "block_play_title":  "Block Playback",
        "block_play_hint":   "Click block to target. 'ALL' for full loop.",
        "play_all":          "ALL",
        "cycle_fmt":         "Cycle {}  |  {}  |  Frame {}/{}  |  B{} S{}  |  {}%",
        "session_fmt":       "Session: {}  |  {} FPS  |  {} frames / {} blocks",
        "start_recv":        "[ START RECV ]",
        "stop_recv":         "[ STOP ]",
        "recv_hint":         "Click button below to start camera",
        "cam_starting":      "> Camera started, scanning...",
        "cam_error":         "Cannot open camera!\nCheck your connection.",
        "recv_stats":        "Blocks: {}/{} ({}%)  |  Valid: {}  |  Dup: {}  |  Err: {}",
        "recv_progress":     "> Receiving...  Session {}",
        "recv_done_stats":   "Done!  Valid: {}  |  Dup: {}",
        "recv_done_status":  "> Transfer complete!",
        "recv_done_msg":     "Files received!\nSaved to: {}",
        "recv_done_title":   "Transfer Complete",
        "recv_waiting":      "> Waiting...",
        "recv_stopped":      "> Stopped",
        "warn_no_files":     "Please add files first!",
        "err_prep":          "Preparation failed:\n{}",
        "err_no_payload":    "No files to send",
        "file_count_fmt":    "{} files, total: {}",
        "file_dialog":       "Select files to send",
        "folder_dialog":     "Select folder to send",
    },
    "zh": {
        "title":             "AirQRT — 二维码文件传输",
        "tab_send":          "发 送",
        "tab_recv":          "接 收",
        "send_title":        "[ 发 送 端 ]",
        "recv_title":        "[ 接 收 端 ]",
        "drop_hint":         '点击 "添加文件" 或将文件拖拽到此处',
        "no_files":          "尚未添加文件",
        "add_file":          "添加文件",
        "add_folder":        "添加文件夹",
        "remove_sel":        "移除选中",
        "clear_all":         "清空列表",
        "fps_label":         "帧率",
        "start_send":        "[ 开始发送 ]",
        "stop_send":         "[ 停止 ]",
        "preparing":         "[ 准备中... ]",
        "status_ready":      "> 就绪",
        "status_reading":    "> 正在读取和压缩文件…",
        "status_building":   "> 正在构建传输帧…",
        "status_qr_gen":     "> 预生成二维码 {}%…",
        "status_stopped":    "> 已停止",
        "sending_title":     "[ 正在发送… ]",
        "block_play_title":  "按块定向播放",
        "block_play_hint":   "点击块号定向补漏，「ALL」恢复全部播放",
        "play_all":          "ALL",
        "cycle_fmt":         "轮 {}  |  {}  |  帧 {}/{}  |  B{} S{}  |  {}%",
        "session_fmt":       "Session: {}  |  {} FPS  |  {} 帧 / {} 块",
        "start_recv":        "[ 开始接收 ]",
        "stop_recv":         "[ 停止 ]",
        "recv_hint":         "点击下方按钮启动摄像头",
        "cam_starting":      "> 摄像头已启动，等待扫描…",
        "cam_error":         "无法打开摄像头！\n请检查摄像头连接。",
        "recv_stats":        "块: {}/{} ({}%)  |  有效: {}  |  重复: {}  |  错误: {}",
        "recv_progress":     "> 正在接收…  会话 {}",
        "recv_done_stats":   "接收完成!  有效帧: {}  |  重复: {}",
        "recv_done_status":  "> 传输完成！",
        "recv_done_msg":     "文件已成功接收！\n保存位置: {}",
        "recv_done_title":   "传输完成",
        "recv_waiting":      "> 等待开始…",
        "recv_stopped":      "> 已停止",
        "warn_no_files":     "请先添加要发送的文件！",
        "err_prep":          "准备失败:\n{}",
        "err_no_payload":    "没有可发送的文件",
        "file_count_fmt":    "{} 个文件，总大小: {}",
        "file_dialog":       "选择要发送的文件",
        "folder_dialog":     "选择要发送的文件夹",
    },
    "ru": {
        "title":             "AirQRT — Передача файлов",
        "tab_send":          "ОТПР",
        "tab_recv":          "ПРИЁМ",
        "send_title":        "[ ОТПРАВКА ]",
        "recv_title":        "[ ПРИЁМ ]",
        "drop_hint":         'Нажмите "Добавить" или перетащите файлы',
        "no_files":          "Файлы не добавлены",
        "add_file":          "Добавить",
        "add_folder":        "Папка",
        "remove_sel":        "Удалить",
        "clear_all":         "Очистить",
        "fps_label":         "FPS",
        "start_send":        "[ НАЧАТЬ ОТПРАВКУ ]",
        "stop_send":         "[ СТОП ]",
        "preparing":         "[ ПОДГОТОВКА... ]",
        "status_ready":      "> Готово",
        "status_reading":    "> Чтение и сжатие файлов…",
        "status_building":   "> Построение кадров…",
        "status_qr_gen":     "> Генерация QR-кодов {}%…",
        "status_stopped":    "> Остановлено",
        "sending_title":     "[ ОТПРАВКА… ]",
        "block_play_title":  "Воспроизведение блоков",
        "block_play_hint":   "Нажмите блок для повтора. 'ALL' — все.",
        "play_all":          "ALL",
        "cycle_fmt":         "Цикл {}  |  {}  |  Кадр {}/{}  |  B{} S{}  |  {}%",
        "session_fmt":       "Сессия: {}  |  {} FPS  |  {} кадров / {} блоков",
        "start_recv":        "[ НАЧАТЬ ПРИЁМ ]",
        "stop_recv":         "[ СТОП ]",
        "recv_hint":         "Нажмите кнопку для запуска камеры",
        "cam_starting":      "> Камера запущена, сканирование…",
        "cam_error":         "Не удалось открыть камеру!\nПроверьте подключение.",
        "recv_stats":        "Блоки: {}/{} ({}%)  |  Принято: {}  |  Дубли: {}  |  Ошибки: {}",
        "recv_progress":     "> Приём…  Сессия {}",
        "recv_done_stats":   "Готово!  Принято: {}  |  Дубли: {}",
        "recv_done_status":  "> Передача завершена!",
        "recv_done_msg":     "Файлы получены!\nСохранено: {}",
        "recv_done_title":   "Передача завершена",
        "recv_waiting":      "> Ожидание…",
        "recv_stopped":      "> Остановлено",
        "warn_no_files":     "Сначала добавьте файлы!",
        "err_prep":          "Ошибка подготовки:\n{}",
        "err_no_payload":    "Нет файлов для отправки",
        "file_count_fmt":    "{} файл(ов), всего: {}",
        "file_dialog":       "Выберите файлы",
        "folder_dialog":     "Выберите папку",
    },
    "ja": {
        "title":             "AirQRT — QRコード転送",
        "tab_send":          "送信",
        "tab_recv":          "受信",
        "send_title":        "[ 送 信 ]",
        "recv_title":        "[ 受 信 ]",
        "drop_hint":         '「ファイル追加」をクリック またはドラッグ＆ドロップ',
        "no_files":          "ファイルなし",
        "add_file":          "ファイル追加",
        "add_folder":        "フォルダ追加",
        "remove_sel":        "削除",
        "clear_all":         "全削除",
        "fps_label":         "FPS",
        "start_send":        "[ 送信開始 ]",
        "stop_send":         "[ 停止 ]",
        "preparing":         "[ 準備中... ]",
        "status_ready":      "> 準備完了",
        "status_reading":    "> ファイルを読み込み中…",
        "status_building":   "> フレームを構築中…",
        "status_qr_gen":     "> QRコード生成 {}%…",
        "status_stopped":    "> 停止",
        "sending_title":     "[ 送信中… ]",
        "block_play_title":  "ブロック再生",
        "block_play_hint":   "ブロックをクリックで再生。'ALL'で全体。",
        "play_all":          "ALL",
        "cycle_fmt":         "周期 {}  |  {}  |  フレーム {}/{}  |  B{} S{}  |  {}%",
        "session_fmt":       "セッション: {}  |  {} FPS  |  {} フレーム / {} ブロック",
        "start_recv":        "[ 受信開始 ]",
        "stop_recv":         "[ 停止 ]",
        "recv_hint":         "ボタンを押してカメラを起動",
        "cam_starting":      "> カメラ起動、スキャン中…",
        "cam_error":         "カメラを開けません！\n接続を確認してください。",
        "recv_stats":        "ブロック: {}/{} ({}%)  |  有効: {}  |  重複: {}  |  エラー: {}",
        "recv_progress":     "> 受信中…  セッション {}",
        "recv_done_stats":   "完了!  有効: {}  |  重複: {}",
        "recv_done_status":  "> 転送完了！",
        "recv_done_msg":     "ファイルを受信しました！\n保存先: {}",
        "recv_done_title":   "転送完了",
        "recv_waiting":      "> 待機中…",
        "recv_stopped":      "> 停止",
        "warn_no_files":     "ファイルを追加してください！",
        "err_prep":          "準備に失敗:\n{}",
        "err_no_payload":    "送信するファイルがありません",
        "file_count_fmt":    "{} ファイル、合計: {}",
        "file_dialog":       "送信ファイルを選択",
        "folder_dialog":     "送信フォルダを選択",
    },
}


# ── 工具 ─────────────────────────────────────────────────────

def _fmt_size(n):
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n / 1024:.1f} KB"
    return f"{n / 1024 ** 2:.1f} MB"


def _make_btn(parent, text, command, bg, fg=C["fg_bright"], font_size=10, padx=10, pady=4, **kw):
    """生成统一风格的按钮"""
    b = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
        relief="flat", cursor="hand2", bd=0,
        font=(FONT_CN, font_size, "bold"),
        padx=padx, pady=pady, **kw,
    )
    return b


# ══════════════════════════════════════════════════════════════
#  自定义 TabBar (JS 风格)
# ══════════════════════════════════════════════════════════════

class TabBar(tk.Canvas):
    """居中的滑动下划线式标签栏"""

    TAB_PAD_X = 30
    TAB_H = 40
    LINE_H = 3

    def __init__(self, parent, tabs, on_switch, **kw):
        super().__init__(parent, height=self.TAB_H + self.LINE_H, bg=C["bg"], highlightthickness=0, **kw)
        self.tabs = tabs          # [(key, label), ...]
        self.on_switch = on_switch
        self.active = 0
        self.tab_coords = []      # [(x_start, x_end), ...]
        self.bind("<Configure>", self._draw)
        self.bind("<Button-1>", self._click)

    def _draw(self, _event=None):
        self.delete("all")
        w = self.winfo_width()

        # 计算每个标签的宽度
        widths = []
        for _, label in self.tabs:
            tw = self.tk.call("font", "measure", f"{FONT} 13 bold", label)
            widths.append(tw + self.TAB_PAD_X * 2)

        total_w = sum(widths)
        start_x = (w - total_w) // 2

        # 底部基线
        self.create_line(0, self.TAB_H, w, self.TAB_H, fill=C["border"], width=1)

        self.tab_coords = []
        x = start_x
        for i, (_, label) in enumerate(self.tabs):
            tw = widths[i]
            cx = x + tw // 2
            cy = self.TAB_H // 2

            color = C["tab_active"] if i == self.active else C["tab_inactive"]
            self.create_text(cx, cy, text=label, fill=color, font=(FONT, 13, "bold"))

            if i == self.active:
                self.create_rectangle(x + 4, self.TAB_H, x + tw - 4, self.TAB_H + self.LINE_H,
                                      fill=C["accent"], outline="")

            self.tab_coords.append((x, x + tw))
            x += tw

    def _click(self, event):
        for i, (x0, x1) in enumerate(self.tab_coords):
            if x0 <= event.x <= x1 and i != self.active:
                self.active = i
                self._draw()
                self.on_switch(i)
                return

    def set_labels(self, labels):
        for i, label in enumerate(labels):
            if i < len(self.tabs):
                self.tabs[i] = (self.tabs[i][0], label)
        self._draw()


# ══════════════════════════════════════════════════════════════
#  自定义进度条
# ══════════════════════════════════════════════════════════════

class TermProgressBar(tk.Canvas):
    def __init__(self, parent, **kw):
        super().__init__(parent, height=14, bg=C["progress_bg"], highlightthickness=0, **kw)
        self._pct = 0

    def set(self, pct):
        self._pct = max(0, min(100, pct))
        self._redraw()

    def _redraw(self, _e=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 2:
            return
        # 背景槽
        self.create_rectangle(0, 2, w, h - 2, fill=C["bg_secondary"], outline=C["border"])
        # 填充
        fw = int(w * self._pct / 100)
        if fw > 0:
            self.create_rectangle(0, 2, fw, h - 2, fill=C["progress_fg"], outline="")

    def bind_redraw(self):
        self.bind("<Configure>", self._redraw)


# ══════════════════════════════════════════════════════════════
#  终端风格语言选择器
# ══════════════════════════════════════════════════════════════

class LangSelector(tk.Frame):
    """终端风格的语言下拉选择器"""

    def __init__(self, parent, current, on_change, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        self.on_change = on_change
        self.current = current
        self._popup = None

        self.btn = tk.Label(
            self, text=self._display(current),
            font=(FONT, 9, "bold"), bg=C["btn_hl"], fg=C["accent"],
            padx=8, pady=3, cursor="hand2",
        )
        self.btn.pack()
        self.btn.bind("<Button-1>", self._toggle)

    def _display(self, code):
        for c, name in LANGUAGES:
            if c == code:
                return f"[ {name} ]"
        return f"[ {code} ]"

    def _toggle(self, _event=None):
        if self._popup:
            self._close()
            return
        self._popup = tk.Toplevel(self)
        self._popup.overrideredirect(True)
        self._popup.configure(bg=C["border"])

        x = self.btn.winfo_rootx()
        y = self.btn.winfo_rooty() + self.btn.winfo_height() + 2
        self._popup.geometry(f"+{x}+{y}")

        for code, name in LANGUAGES:
            fg = C["accent"] if code == self.current else C["fg_dim"]
            lbl = tk.Label(
                self._popup, text=f"  {name}  ", font=(FONT, 9),
                bg=C["bg_secondary"], fg=fg, padx=10, pady=5,
                cursor="hand2", anchor="w",
            )
            lbl.pack(fill="x", padx=1, pady=(1, 0))
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(bg=C["btn_hl"]))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(bg=C["bg_secondary"]))
            lbl.bind("<Button-1>", lambda e, c=code: self._select(c))

        self._popup.focus_set()
        self._popup.bind("<FocusOut>", lambda e: self.btn.after(80, self._close))

    def _select(self, code):
        self.current = code
        self.btn.config(text=self._display(code))
        self._close()
        self.on_change(code)

    def _close(self):
        if self._popup:
            try:
                self._popup.destroy()
            except Exception:
                pass
            self._popup = None

    def update_display(self, code):
        self.current = code
        self.btn.config(text=self._display(code))


# ══════════════════════════════════════════════════════════════
#  发送 Tab
# ══════════════════════════════════════════════════════════════

class SenderTab:
    QR_DISPLAY_SIZE = 460

    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.Frame(parent, bg=C["bg"])

        self.file_paths = []
        self.sending = False
        self.preparing = False
        self.fps = FRAME_FPS
        self.qr_pil_images = []
        self.transport_frames = []
        self.current_frame_idx = 0
        self.cycle = 0
        self.total_frames = 0
        self.total_blocks = 0
        self.after_id = None
        self.active_block = None
        self.block_frame_indices = {}
        self.block_buttons = []

        self._build_file_view()
        self._build_send_view()
        self._show_file_view()

    def t(self, key, *args):
        return self.app.t(key, *args)

    # ── 文件选择界面 ─────────────────────────────────────────

    def _build_file_view(self):
        self.file_view = tk.Frame(self.frame, bg=C["bg"], padx=15, pady=10)

        # 标题
        self.title_lbl = tk.Label(self.file_view, text="", font=(FONT, 14, "bold"),
                                  bg=C["bg"], fg=C["accent"])
        self.title_lbl.pack(pady=(0, 8))

        # 文件列表区
        self.drop_frame = tk.Frame(self.file_view, bg=C["bg_input"], bd=1,
                                   highlightbackground=C["border"], highlightthickness=1)
        self.drop_frame.pack(fill="both", expand=True, pady=4)

        self.drop_hint = tk.Label(self.drop_frame, text="", font=(FONT_CN, 11),
                                  bg=C["bg_input"], fg=C["fg_dim"])
        self.drop_hint.pack(expand=True)

        self.file_listbox = tk.Listbox(
            self.drop_frame, font=(FONT, 10), selectmode="extended",
            bg=C["bg_input"], fg=C["accent"], selectbackground=C["border"],
            selectforeground=C["fg_bright"], activestyle="none",
            highlightthickness=0, bd=0, relief="flat",
        )

        self.info_lbl = tk.Label(self.file_view, text="", font=(FONT, 10),
                                 bg=C["bg"], fg=C["fg_dim"])
        self.info_lbl.pack(pady=4)

        # 按钮行
        self.btn_row = tk.Frame(self.file_view, bg=C["bg"])
        self.btn_row.pack(pady=4)
        self._file_btns = []
        for key, cmd in [
            ("add_file", self._add_files),
            ("add_folder", self._add_folder),
            ("remove_sel", self._remove_selected),
            ("clear_all", self._clear_files),
        ]:
            b = _make_btn(self.btn_row, "", cmd, bg=C["bg_secondary"], font_size=9, padx=8, pady=3)
            b.pack(side="left", padx=3)
            self._file_btns.append((b, key))

        # 帧率
        fps_frame = tk.Frame(self.file_view, bg=C["bg_secondary"], bd=0)
        fps_frame.pack(fill="x", pady=8, ipady=6)

        self.fps_title = tk.Label(fps_frame, text="", font=(FONT, 10), bg=C["bg_secondary"], fg=C["fg_dim"])
        self.fps_title.pack(side="left", padx=(12, 4))
        _make_btn(fps_frame, " − ", self._fps_down, bg=C["border"], font_size=10, padx=6, pady=1).pack(side="left", padx=2)
        self.fps_var = tk.StringVar(value=f"{self.fps}")
        tk.Label(fps_frame, textvariable=self.fps_var, font=(FONT, 14, "bold"),
                 bg=C["bg_secondary"], fg=C["accent"]).pack(side="left", padx=8)
        _make_btn(fps_frame, " + ", self._fps_up, bg=C["border"], font_size=10, padx=6, pady=1).pack(side="left", padx=2)
        tk.Label(fps_frame, text="FPS", font=(FONT, 10), bg=C["bg_secondary"], fg=C["fg_dim"]).pack(side="left")

        # 开始按钮
        self.start_btn = _make_btn(self.file_view, "", self._start_sending,
                                   bg=C["btn"], fg=C["accent"], font_size=13, padx=10, pady=10)
        self.start_btn.pack(fill="x", pady=8)

        # 状态
        self.status_lbl = tk.Label(self.file_view, text="", font=(FONT, 9),
                                   bg=C["bg"], fg=C["fg_dim"], anchor="w")
        self.status_lbl.pack(fill="x")

    # ── 发送中界面 ───────────────────────────────────────────

    def _build_send_view(self):
        self.send_view = tk.Frame(self.frame, bg=C["bg"], padx=10, pady=6)

        self.send_title_lbl = tk.Label(self.send_view, text="", font=(FONT, 13, "bold"),
                                       bg=C["bg"], fg=C["yellow"])
        self.send_title_lbl.pack(pady=(0, 4))

        # QR 码
        qr_frame = tk.Frame(self.send_view, bg=C["border"], bd=2)
        qr_frame.pack(pady=4)
        self.qr_label = tk.Label(qr_frame, bg="white")
        self.qr_label.pack()

        # 进度条
        self.send_progress = TermProgressBar(self.send_view)
        self.send_progress.pack(fill="x", pady=6)
        self.send_progress.bind_redraw()

        self.progress_lbl = tk.Label(self.send_view, text="", font=(FONT, 10),
                                     bg=C["bg"], fg=C["fg"])
        self.progress_lbl.pack()

        # 帧率控制
        ctrl = tk.Frame(self.send_view, bg=C["bg"])
        ctrl.pack(pady=3)
        _make_btn(ctrl, " − ", self._fps_down, bg=C["border"], font_size=10, padx=6, pady=1).pack(side="left", padx=2)
        self.send_fps_var = tk.StringVar(value=f"{self.fps}")
        tk.Label(ctrl, textvariable=self.send_fps_var, font=(FONT, 14, "bold"),
                 bg=C["bg"], fg=C["accent"]).pack(side="left", padx=8)
        _make_btn(ctrl, " + ", self._fps_up, bg=C["border"], font_size=10, padx=6, pady=1).pack(side="left", padx=2)
        tk.Label(ctrl, text="FPS", font=(FONT, 10), bg=C["bg"], fg=C["fg_dim"]).pack(side="left")

        # 块选择区
        self.block_frame = tk.Frame(self.send_view, bg=C["bg_secondary"], bd=0)
        self.block_frame.pack(fill="x", pady=6, ipady=4)

        self.block_title = tk.Label(self.block_frame, text="", font=(FONT, 9, "bold"),
                                    bg=C["bg_secondary"], fg=C["fg_dim"])
        self.block_title.pack(anchor="w", padx=8)
        self.block_hint_lbl = tk.Label(self.block_frame, text="", font=(FONT, 8),
                                       bg=C["bg_secondary"], fg=C["fg_dim"])
        self.block_hint_lbl.pack(anchor="w", padx=8)
        self.block_btn_container = tk.Frame(self.block_frame, bg=C["bg_secondary"])
        self.block_btn_container.pack(fill="x", padx=6, pady=2)

        # 停止
        self.stop_btn = _make_btn(self.send_view, "", self._stop_sending,
                                  bg=C["btn"], fg=C["accent"], font_size=13, padx=10, pady=10)
        self.stop_btn.pack(fill="x", pady=8)

        self.send_status_lbl = tk.Label(self.send_view, text="", font=(FONT, 9),
                                        bg=C["bg"], fg=C["fg_dim"], anchor="w")
        self.send_status_lbl.pack(fill="x")

    # ── 语言刷新 ─────────────────────────────────────────────

    def refresh_lang(self):
        self.title_lbl.config(text=self.t("send_title"))
        self.drop_hint.config(text=self.t("drop_hint"))
        for b, key in self._file_btns:
            b.config(text=self.t(key))
        self.fps_title.config(text=self.t("fps_label"))
        if not self.sending and not self.preparing:
            self.start_btn.config(text=self.t("start_send"))
            self.status_lbl.config(text=self.t("status_ready"))
        if not self.file_paths:
            self.info_lbl.config(text=self.t("no_files"))
        else:
            self._refresh_file_list()
        self.send_title_lbl.config(text=self.t("sending_title"))
        self.stop_btn.config(text=self.t("stop_send"))
        self.block_title.config(text=self.t("block_play_title"))
        self.block_hint_lbl.config(text=self.t("block_play_hint"))

    # ── 视图切换 ─────────────────────────────────────────────

    def _show_file_view(self):
        self.send_view.pack_forget()
        self.file_view.pack(fill="both", expand=True)

    def _show_send_view(self):
        self.file_view.pack_forget()
        self.send_view.pack(fill="both", expand=True)

    # ── 文件管理 ─────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title=self.t("file_dialog"),
            filetypes=[("All Files", "*.*")],
        )
        for p in paths:
            if p not in self.file_paths:
                self.file_paths.append(p)
        self._refresh_file_list()

    def _add_folder(self):
        d = filedialog.askdirectory(title=self.t("folder_dialog"))
        if d:
            for name in os.listdir(d):
                full = os.path.join(d, name)
                if os.path.isfile(full) and full not in self.file_paths:
                    self.file_paths.append(full)
            self._refresh_file_list()

    def _remove_selected(self):
        for i in reversed(self.file_listbox.curselection()):
            del self.file_paths[i]
        self._refresh_file_list()

    def _clear_files(self):
        self.file_paths.clear()
        self._refresh_file_list()

    def _refresh_file_list(self):
        if self.file_paths:
            self.drop_hint.pack_forget()
            self.file_listbox.pack(fill="both", expand=True, padx=4, pady=4)
            self.file_listbox.delete(0, tk.END)
            total = 0
            for p in self.file_paths:
                sz = os.path.getsize(p)
                total += sz
                self.file_listbox.insert(tk.END, f"  {os.path.basename(p)}  ({_fmt_size(sz)})")
            self.info_lbl.config(text=self.t("file_count_fmt").format(len(self.file_paths), _fmt_size(total)))
        else:
            self.file_listbox.pack_forget()
            self.drop_hint.pack(expand=True)
            self.info_lbl.config(text=self.t("no_files"))

    # ── 帧率 ─────────────────────────────────────────────────

    def _fps_up(self):
        self.fps = min(FRAME_MAX_FPS, self.fps + FRAME_STEP_FPS)
        self._sync_fps()

    def _fps_down(self):
        self.fps = max(FRAME_MIN_FPS, self.fps - FRAME_STEP_FPS)
        self._sync_fps()

    def _sync_fps(self):
        self.fps_var.set(str(self.fps))
        self.send_fps_var.set(str(self.fps))

    # ── 发送流程 ─────────────────────────────────────────────

    def _start_sending(self):
        if not self.file_paths:
            messagebox.showwarning("", self.t("warn_no_files"))
            return
        if self.preparing:
            return
        self.preparing = True
        self.start_btn.config(state="disabled", text=self.t("preparing"))
        self.status_lbl.config(text=self.t("status_reading"))
        threading.Thread(target=self._prepare, daemon=True).start()

    def _prepare(self):
        try:
            payload = read_and_compress_files(self.file_paths)
            if payload is None:
                self._sched(lambda: self._prep_error(self.t("err_no_payload")))
                return

            session_id = str(uuid.uuid4())[:8]
            self._sched(lambda: self.status_lbl.config(text=self.t("status_building")))

            self.transport_frames, _, _, self.total_blocks = build_transport_frames(payload, session_id)
            self.total_frames = len(self.transport_frames)

            self.block_frame_indices.clear()
            for idx, frm in enumerate(self.transport_frames):
                self.block_frame_indices.setdefault(frm["b"], []).append(idx)

            qr_images = []
            for i, frm in enumerate(self.transport_frames):
                text = json.dumps(frm, separators=(",", ":"))
                pil_img = create_qr_pil_image(text).convert("RGB")
                pil_img = pil_img.resize((self.QR_DISPLAY_SIZE, self.QR_DISPLAY_SIZE), Image.NEAREST)
                qr_images.append(pil_img)
                if (i + 1) % 20 == 0 or i == self.total_frames - 1:
                    pct = int((i + 1) / self.total_frames * 100)
                    self._sched(lambda p=pct: self.status_lbl.config(text=self.t("status_qr_gen").format(p)))

            self.qr_pil_images = qr_images
            self._sched(self._begin_sending)
        except Exception as e:
            self._sched(lambda: self._prep_error(str(e)))

    def _sched(self, fn):
        self.frame.after(0, fn)

    def _prep_error(self, msg):
        self.preparing = False
        self.start_btn.config(state="normal", text=self.t("start_send"))
        self.status_lbl.config(text=self.t("status_ready"))
        messagebox.showerror("", self.t("err_prep").format(msg))

    def _begin_sending(self):
        self.preparing = False
        self.sending = True
        self.active_block = None
        self.current_frame_idx = 0
        self.cycle = 1
        self._show_send_view()
        self._build_block_buttons()
        self._tick()

    # ── 块按钮 ───────────────────────────────────────────────

    def _build_block_buttons(self):
        for w in self.block_btn_container.winfo_children():
            w.destroy()
        self.block_buttons = []

        self.all_btn = _make_btn(self.block_btn_container, self.t("play_all"),
                                 self._play_all, bg=C["accent"], fg=C["bg"],
                                 font_size=9, padx=6, pady=2)
        self.all_btn.pack(side="left", padx=2, pady=2)

        for b in range(self.total_blocks):
            btn = _make_btn(self.block_btn_container, f"B{b + 1}",
                            lambda blk=b: self._play_block(blk),
                            bg=C["block_normal"], fg=C["fg_dim"],
                            font_size=9, padx=5, pady=2)
            btn.pack(side="left", padx=1, pady=2)
            self.block_buttons.append(btn)

    def _play_all(self):
        self.active_block = None
        self.current_frame_idx = 0
        self.cycle = 1
        self._hl_blocks()

    def _play_block(self, idx):
        self.active_block = idx
        self.current_frame_idx = 0
        self.cycle = 1
        self._hl_blocks()

    def _hl_blocks(self):
        if self.active_block is None:
            self.all_btn.config(bg=C["accent"], fg=C["bg"])
        else:
            self.all_btn.config(bg=C["btn"], fg=C["fg_dim"])
        for i, btn in enumerate(self.block_buttons):
            if self.active_block == i:
                btn.config(bg=C["block_active"], fg=C["bg"])
            else:
                btn.config(bg=C["block_normal"], fg=C["fg_dim"])

    # ── 播放循环 ─────────────────────────────────────────────

    def _get_play_indices(self):
        if self.active_block is not None:
            return self.block_frame_indices.get(self.active_block, [])
        return list(range(self.total_frames))

    def _tick(self):
        if not self.sending:
            return
        indices = self._get_play_indices()
        if not indices:
            self.after_id = self.frame.after(100, self._tick)
            return

        if self.current_frame_idx >= len(indices):
            self.current_frame_idx = 0
            self.cycle += 1

        real_idx = indices[self.current_frame_idx]
        photo = ImageTk.PhotoImage(self.qr_pil_images[real_idx])
        self.qr_label.config(image=photo)
        self.qr_label._photo = photo

        meta = self.transport_frames[real_idx]
        pct = (self.current_frame_idx + 1) / len(indices) * 100
        self.send_progress.set(pct)

        block_info = f"B{meta['b']+1}" if self.active_block is not None else self.t("play_all")
        self.progress_lbl.config(
            text=self.t("cycle_fmt").format(
                self.cycle, block_info,
                self.current_frame_idx + 1, len(indices),
                meta["b"] + 1, meta["x"] + 1, f"{pct:.0f}",
            )
        )
        self.send_status_lbl.config(
            text=self.t("session_fmt").format(meta["s"], self.fps, self.total_frames, self.total_blocks)
        )

        self.current_frame_idx += 1
        self.after_id = self.frame.after(max(1, 1000 // self.fps), self._tick)

    def _stop_sending(self):
        self.sending = False
        if self.after_id:
            self.frame.after_cancel(self.after_id)
            self.after_id = None
        self.qr_pil_images.clear()
        self._show_file_view()
        self.start_btn.config(state="normal", text=self.t("start_send"))
        self.status_lbl.config(text=self.t("status_stopped"))


# ══════════════════════════════════════════════════════════════
#  接收 Tab
# ══════════════════════════════════════════════════════════════

class ReceiverTab:
    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.Frame(parent, bg=C["bg"])

        self.receiving = False
        self.cap = None
        self.receiver = QRReceiver()
        self.detector = cv2.QRCodeDetector()
        self.latest_frame = None
        self.completed = False

        self._build_ui()

    def t(self, key, *args):
        return self.app.t(key, *args)

    def _build_ui(self):
        self.title_lbl = tk.Label(self.frame, text="", font=(FONT, 14, "bold"),
                                  bg=C["bg"], fg=C["accent"])
        self.title_lbl.pack(pady=(10, 6))

        cam_frame = tk.Frame(self.frame, bg=C["bg_input"], bd=1,
                             highlightbackground=C["border"], highlightthickness=1)
        cam_frame.pack(fill="both", expand=True, padx=12)

        self.cam_label = tk.Label(cam_frame, bg=C["bg_input"], text="",
                                  font=(FONT_CN, 13), fg=C["fg_dim"])
        self.cam_label.pack(expand=True, fill="both")

        self.recv_progress = TermProgressBar(self.frame)
        self.recv_progress.pack(fill="x", padx=12, pady=(8, 4))
        self.recv_progress.bind_redraw()

        self.stats_lbl = tk.Label(self.frame, text="", font=(FONT, 10),
                                  bg=C["bg"], fg=C["fg_dim"])
        self.stats_lbl.pack()

        self.btn = _make_btn(self.frame, "", self._toggle,
                             bg=C["btn"], fg=C["accent"], font_size=13, padx=10, pady=10)
        self.btn.pack(fill="x", padx=60, pady=8)

        self.status_lbl = tk.Label(self.frame, text="", font=(FONT, 9),
                                   bg=C["bg"], fg=C["fg_dim"], anchor="w")
        self.status_lbl.pack(fill="x", padx=12, pady=2)

    def refresh_lang(self):
        self.title_lbl.config(text=self.t("recv_title"))
        if not self.receiving:
            self.cam_label.config(text=self.t("recv_hint"))
            self.btn.config(text=self.t("start_recv"))
            if not self.completed:
                self.stats_lbl.config(text=self.t("recv_waiting"))
                self.status_lbl.config(text=self.t("status_ready"))

    # ── 开始 / 停止 ─────────────────────────────────────────

    def _toggle(self):
        if self.receiving:
            self._stop()
        else:
            self._start()

    def _start(self):
        clean_output_dir()
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror("", self.t("cam_error"))
            return
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        self.receiver.reset()
        self.receiving = True
        self.completed = False
        self.latest_frame = None

        self.btn.config(text=self.t("stop_recv"), bg=C["btn"])
        self.status_lbl.config(text=self.t("cam_starting"))
        self.recv_progress.set(0)

        threading.Thread(target=self._cam_loop, daemon=True).start()
        self._ui_loop()

    def _stop(self):
        self.receiving = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.btn.config(text=self.t("start_recv"), bg=C["btn"])
        self.cam_label.config(image="", text=self.t("recv_hint"), fg=C["fg_dim"])
        if not self.completed:
            self.status_lbl.config(text=self.t("recv_stopped"))

    # ── 摄像头循环 ───────────────────────────────────────────

    def _cam_loop(self):
        while self.receiving:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.03)
                    continue
                data, bbox, _ = self.detector.detectAndDecode(frame)
                if bbox is not None and data:
                    try:
                        cv2.polylines(frame, [bbox.astype(int)], True, (0, 255, 0), 3)
                    except Exception:
                        pass
                if data:
                    result = self.receiver.process_frame(data)
                    if result.get("status") == "completed":
                        self.completed = True
                        self.latest_frame = frame
                        self.receiving = False
                        self.frame.after(0, self._on_complete)
                        return
                self.latest_frame = frame
            except Exception:
                time.sleep(0.03)

    def _ui_loop(self):
        if self.latest_frame is not None:
            rgb = cv2.cvtColor(self.latest_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            cw, ch = self.cam_label.winfo_width(), self.cam_label.winfo_height()
            if cw > 10 and ch > 10:
                iw, ih = img.size
                scale = min(cw / iw, ch / ih)
                nw, nh = int(iw * scale), int(ih * scale)
                if nw > 0 and nh > 0:
                    img = img.resize((nw, nh), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.cam_label.config(image=photo, text="")
            self.cam_label._photo = photo

        r = self.receiver
        if r.current_session and r.total_blocks > 0:
            pct = r.decoded_blocks / r.total_blocks * 100
            self.recv_progress.set(pct)
            self.stats_lbl.config(text=self.t("recv_stats").format(
                r.decoded_blocks, r.total_blocks, f"{pct:.0f}",
                r.valid_count, r.duplicate_count, r.error_count,
            ))
            self.status_lbl.config(text=self.t("recv_progress").format(r.current_session))

        if self.receiving:
            self.frame.after(33, self._ui_loop)

    def _on_complete(self):
        self.recv_progress.set(100)
        r = self.receiver
        self.stats_lbl.config(text=self.t("recv_done_stats").format(r.valid_count, r.duplicate_count))
        self.status_lbl.config(text=self.t("recv_done_status"))
        self.btn.config(text=self.t("start_recv"), bg=C["btn"])
        if self.cap:
            self.cap.release()
            self.cap = None
        abs_dir = os.path.abspath(OUTPUT_DIR)
        try:
            os.startfile(abs_dir)
        except Exception:
            pass
        messagebox.showinfo(self.t("recv_done_title"), self.t("recv_done_msg").format(abs_dir))

    def cleanup(self):
        self.receiving = False
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════
#  主应用
# ══════════════════════════════════════════════════════════════

class App:
    def __init__(self):
        self.lang = "en"
        self.root = tk.Tk()
        self.root.title(I18N[self.lang]["title"])
        self.root.geometry("720x840")
        self.root.minsize(620, 700)
        self.root.configure(bg=C["bg"])

        # ── 顶栏：语言选择器 + 自定义 TabBar ──
        top = tk.Frame(self.root, bg=C["bg"])
        top.pack(fill="x")

        self.lang_selector = LangSelector(top, self.lang, self._set_lang)
        self.lang_selector.pack(side="right", padx=10, pady=6)

        self.tab_bar = TabBar(top, [
            ("send", I18N[self.lang]["tab_send"]),
            ("recv", I18N[self.lang]["tab_recv"]),
        ], self._on_tab_switch)
        self.tab_bar.pack(fill="x", padx=60)

        # ── 内容容器 ──
        self.content = tk.Frame(self.root, bg=C["bg"])
        self.content.pack(fill="both", expand=True)

        self.sender_tab = SenderTab(self.content, self)
        self.receiver_tab = ReceiverTab(self.content, self)

        self._show_tab(0)
        self._refresh_all_lang()

        # 拖拽
        self._try_enable_dnd()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 暗色标题栏 (Windows 10/11)
        self.root.after(50, self._apply_dark_titlebar)

    # ── 暗色标题栏 (Windows DWM) ─────────────────────────────

    def _apply_dark_titlebar(self):
        """通过 DWM API 将原生标题栏设为暗色 (Windows 10/11)"""
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())

            # Windows 10/11: 启用深色模式标题栏
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(ctypes.c_int(1)),
                ctypes.sizeof(ctypes.c_int),
            )

            # Windows 11: 自定义标题栏背景色 (COLORREF = 0x00BBGGRR)
            DWMWA_CAPTION_COLOR = 35
            bg_colorref = 0x0C0C0C  # #0c0c0c → R=0x0c G=0x0c B=0x0c
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_CAPTION_COLOR,
                ctypes.byref(ctypes.c_int(bg_colorref)),
                ctypes.sizeof(ctypes.c_int),
            )

            # Windows 11: 自定义标题栏文字色
            DWMWA_TEXT_COLOR = 36
            text_colorref = 0x41FF00  # #00ff41 → R=0x00 G=0xFF B=0x41
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_TEXT_COLOR,
                ctypes.byref(ctypes.c_int(text_colorref)),
                ctypes.sizeof(ctypes.c_int),
            )
        except Exception:
            pass

    def t(self, key, *args):
        s = I18N[self.lang].get(key, key)
        return s.format(*args) if args else s

    # ── Tab 切换 ──────────────────────────────────────────────

    def _on_tab_switch(self, idx):
        self._show_tab(idx)

    def _show_tab(self, idx):
        self.sender_tab.frame.pack_forget()
        self.receiver_tab.frame.pack_forget()
        if idx == 0:
            self.sender_tab.frame.pack(fill="both", expand=True)
        else:
            self.receiver_tab.frame.pack(fill="both", expand=True)

    # ── 语言切换 ─────────────────────────────────────────────

    def _set_lang(self, lang_code):
        self.lang = lang_code
        self._refresh_all_lang()

    def _refresh_all_lang(self):
        self.root.title(self.t("title"))
        self.tab_bar.set_labels([self.t("tab_send"), self.t("tab_recv")])
        self.sender_tab.refresh_lang()
        self.receiver_tab.refresh_lang()

    # ── 拖拽 ─────────────────────────────────────────────────

    def _try_enable_dnd(self):
        try:
            import windnd
            windnd.hook_dropfiles(self.root, func=self._on_drop)
        except ImportError:
            pass

    def _on_drop(self, file_list):
        for raw in file_list:
            if isinstance(raw, bytes):
                try:
                    path = raw.decode("utf-8")
                except UnicodeDecodeError:
                    path = raw.decode("gbk", errors="replace")
            else:
                path = str(raw)
            if os.path.isfile(path):
                if path not in self.sender_tab.file_paths:
                    self.sender_tab.file_paths.append(path)
            elif os.path.isdir(path):
                for name in os.listdir(path):
                    full = os.path.join(path, name)
                    if os.path.isfile(full) and full not in self.sender_tab.file_paths:
                        self.sender_tab.file_paths.append(full)
        self.sender_tab._refresh_file_list()

    # ── 关闭 ─────────────────────────────────────────────────

    def _on_close(self):
        self.sender_tab.sending = False
        if self.sender_tab.after_id:
            self.root.after_cancel(self.sender_tab.after_id)
        self.receiver_tab.cleanup()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    App().run()


if __name__ == "__main__":
    main()
