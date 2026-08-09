
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtGui import QFont, QFontDatabase, QPainter, QPixmap, QColor
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QMainWindow, QMessageBox, QPushButton, QProgressBar, QVBoxLayout,
    QWidget, QDialog, QDialogButtonBox, QStackedWidget
)

APP_NAME = "Westside Stories"
APP_VERSION = "1.0"
MODEL = "mlx-community/whisper-turbo"

INK_BLACK = "#252525"
DAWN_GOLD_LIGHTEST = "#F4EEDB"
DAWN_GOLD_MEDIUM = "#CEBD74"
DAWN_GOLD_DEEP = "#B89F4C"
PANEL = "#F8F4E8"

APP_HOME = Path.home() / ".westside-stories"
LOG_PATH = Path.home() / "Desktop" / "WestsideStories.log"

BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
STONE_IMAGE = BASE_DIR / "assets" / "temple-stone.png"

os.environ["PATH"] = (
    "/opt/homebrew/bin:/opt/homebrew/opt/ffmpeg-full/bin:"
    + os.environ.get("PATH", "")
)

WORKER_CODE = r"""
import json, sys, traceback
import mlx_whisper

video = sys.argv[1]
out_json = sys.argv[2]
model = sys.argv[3]
language = sys.argv[4]

try:
    kwargs = dict(
        audio=video,
        path_or_hf_repo=model,
        verbose=False,
        condition_on_previous_text=True,
    )
    if language != "auto":
        kwargs["language"] = language

    result = mlx_whisper.transcribe(**kwargs)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
except Exception:
    traceback.print_exc()
    raise
"""

def log(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {msg}\n")

def reset_log() -> None:
    LOG_PATH.write_text(
        f"{APP_NAME} {APP_VERSION}\nStarted: {datetime.now().isoformat()}\n\n",
        encoding="utf-8",
    )

def find_python():
    for p in ["/opt/homebrew/bin/python3", shutil.which("python3")]:
        if p and Path(p).exists():
            return p
    return None

def find_ffmpeg():
    for p in [
        "/opt/homebrew/bin/ffmpeg",
        "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg",
        shutil.which("ffmpeg"),
    ]:
        if p and Path(p).is_file():
            return str(p)
    return None

def has_subtitles_filter(ffmpeg: str) -> bool:
    p = subprocess.run(
        [ffmpeg, "-hide_banner", "-filters"],
        text=True,
        capture_output=True,
    )
    output = (p.stdout or "") + "\n" + (p.stderr or "")
    return any("subtitles" in line.split() for line in output.splitlines())

class StoneBackground(QWidget):
    """Very light temple-stone texture under the Dawn Gold field."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(DAWN_GOLD_LIGHTEST))

        if STONE_IMAGE.exists():
            pix = QPixmap(str(STONE_IMAGE))
            if not pix.isNull():
                scaled = pix.scaled(
                    self.size(),
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )
                painter.setOpacity(0.12)
                x = (self.width() - scaled.width()) // 2
                y = (self.height() - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)

        painter.setOpacity(1.0)
        super().paintEvent(event)


LEADING_PUNCTUATION = "，。！？：；、…,.!?;:"

def clean_subtitle_text(text: str) -> str:
    """Minimal 1.0 post-processing: never allow a subtitle line to begin with punctuation."""
    lines = (text or "").splitlines() or [text or ""]
    cleaned = []
    for line in lines:
        line = line.strip()
        while line and line[0] in LEADING_PUNCTUATION:
            line = line[1:].lstrip()
        cleaned.append(line)
    return "\n".join(cleaned).strip()

class Worker(QObject):
    status = Signal(str, str)
    progress = Signal(int)
    finished = Signal(str, str)
    failed = Signal(str)

    def __init__(self, video, language, use_existing, burn_video):
        super().__init__()
        self.video = Path(video)
        self.language = language
        self.use_existing = use_existing
        self.burn_video = burn_video

    def ensure_whisper_env(self):
        py = find_python()
        if not py:
            raise RuntimeError(
                "找不到 Python 3。\nPython 3 was not found.\n\n"
                "請先安裝 Homebrew Python / Please install Homebrew Python."
            )

        venv = APP_HOME / "venv"
        APP_HOME.mkdir(parents=True, exist_ok=True)

        if not (venv / "bin" / "python").exists():
            self.status.emit("正在建立本地 Whisper 環境…", "Preparing local Whisper environment…")
            self.progress.emit(10)
            p = subprocess.run([py, "-m", "venv", str(venv)], text=True, capture_output=True)
            log("venv stdout: " + (p.stdout or ""))
            log("venv stderr: " + (p.stderr or ""))
            if p.returncode != 0:
                raise RuntimeError("建立 Whisper 環境失敗。\nFailed to create Whisper environment.")

        vpy = str(venv / "bin" / "python")
        test = subprocess.run(
            [vpy, "-c", "import mlx_whisper, mlx; print('ok')"],
            text=True,
            capture_output=True,
            env=os.environ.copy(),
        )
        log("import test stdout: " + (test.stdout or ""))
        log("import test stderr: " + (test.stderr or ""))

        if test.returncode != 0:
            self.status.emit("第一次使用：正在安裝 mlx-whisper…", "First run: installing mlx-whisper…")
            self.progress.emit(15)
            p = subprocess.run(
                [vpy, "-m", "pip", "install", "mlx-whisper"],
                text=True,
                capture_output=True,
                env=os.environ.copy(),
            )
            log("install stdout: " + (p.stdout or ""))
            log("install stderr: " + (p.stderr or ""))
            if p.returncode != 0:
                raise RuntimeError("mlx-whisper 安裝失敗。\nmlx-whisper installation failed.")

        return vpy

    def transcribe(self, vpy: str, result_json: Path):
        self.status.emit("正在辨識語音並產生字幕…", "Transcribing and generating subtitles…")
        self.progress.emit(30)

        p = subprocess.run(
            [vpy, "-c", WORKER_CODE, str(self.video), str(result_json), MODEL, self.language],
            text=True,
            capture_output=True,
            env=os.environ.copy(),
        )
        log("transcribe stdout:\n" + (p.stdout or ""))
        log("transcribe stderr:\n" + (p.stderr or ""))

        if p.returncode != 0:
            raise RuntimeError(
                "Whisper 執行失敗。\nWhisper failed.\n\n"
                "請查看桌面 WestsideStories.log。"
            )

    def write_srt(self, result_json: Path, srt_path: Path):
        self.status.emit("正在寫入字幕檔…", "Writing SRT file…")
        self.progress.emit(65)

        data = json.loads(result_json.read_text(encoding="utf-8"))
        segments = data.get("segments") or []
        log(f"segments count: {len(segments)}")

        if not segments:
            raise RuntimeError("Whisper 沒有返回字幕片段。\nWhisper returned no subtitle segments.")

        def ts(sec):
            total = int(round(float(sec) * 1000))
            h, rem = divmod(total, 3600000)
            m, rem = divmod(rem, 60000)
            s, ms = divmod(rem, 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        with srt_path.open("w", encoding="utf-8", newline="\n") as f:
            n = 1
            for seg in segments:
                text = clean_subtitle_text(seg.get("text") or "")
                if not text:
                    continue
                start = float(seg.get("start", 0))
                end = float(seg.get("end", start))
                f.write(f"{n}\n{ts(start)} --> {ts(end)}\n{text}\n\n")
                n += 1

    def burn(self, ffmpeg: str, srt: Path, output: Path):
        self.status.emit("正在燒錄字幕到影片…", "Burning subtitles into video…")
        self.progress.emit(75)

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            shutil.copyfile(srt, tmp_path)

            cmd = [
                ffmpeg, "-y",
                "-i", str(self.video),
                "-vf", "subtitles=filename='" + str(tmp_path) + "'",
                "-c:v", "libx264",
                "-crf", "18",
                "-preset", "medium",
                "-c:a", "copy",
                str(output),
            ]

            p = subprocess.run(cmd, text=True, capture_output=True, env=os.environ.copy())
            log("ffmpeg stdout:\n" + (p.stdout or ""))
            log("ffmpeg stderr:\n" + (p.stderr or ""))

            if p.returncode != 0:
                raise RuntimeError(
                    "FFmpeg 燒錄失敗。\nFFmpeg burn-in failed.\n\n"
                    "請查看桌面 WestsideStories.log。"
                )
        finally:
            if tmp_path:
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass

    def run(self):
        reset_log()
        try:
            srt = self.video.with_suffix(".srt")
            output = self.video.with_name(self.video.stem + "_字幕版.mp4")
            result_json = APP_HOME / "last_result.json"

            ffmpeg = find_ffmpeg()
            if not ffmpeg:
                raise RuntimeError("找不到 ffmpeg-full。\nffmpeg-full was not found.")
            if not has_subtitles_filter(ffmpeg):
                raise RuntimeError(
                    "目前 FFmpeg 沒有 subtitles 濾鏡。\n"
                    "The current FFmpeg build has no subtitles filter."
                )

            self.progress.emit(5)

            if srt.exists() and self.use_existing:
                self.status.emit("使用現有字幕檔。", "Using existing SRT.")
                self.progress.emit(70)
            else:
                vpy = self.ensure_whisper_env()
                self.transcribe(vpy, result_json)
                self.write_srt(result_json, srt)

            if self.burn_video:
                self.burn(ffmpeg, srt, output)
                self.progress.emit(100)
                self.status.emit("完成。", "Completed.")
                self.finished.emit(str(srt), str(output))
            else:
                self.progress.emit(100)
                self.status.emit("字幕已完成。", "Subtitle completed.")
                self.finished.emit(str(srt), "")

        except Exception as exc:
            log("EXCEPTION:\n" + traceback.format_exc())
            self.failed.emit(str(exc))

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("關於 Westside Stories / About")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 30, 34, 28)
        layout.setSpacing(12)

        title = QLabel("Westside Stories")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("aboutTitle")
        layout.addWidget(title)

        version = QLabel(f"Version {APP_VERSION}")
        version.setAlignment(Qt.AlignCenter)
        version.setObjectName("small")
        layout.addWidget(version)

        verse = QLabel("Write the vision,\nand make it plain.")
        verse.setAlignment(Qt.AlignCenter)
        verse.setObjectName("verse")
        layout.addWidget(verse)

        ref = QLabel("<i>Habakkuk 2:2</i>")
        ref.setAlignment(Qt.AlignCenter)
        ref.setTextFormat(Qt.RichText)
        ref.setObjectName("small")
        layout.addWidget(ref)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setObjectName("goldLine")
        layout.addWidget(divider)

        dev = QLabel(
            "Developed for\n\n"
            "神召會活水堂西區教會\n"
            "P.A.O.C. Living Water Assembly West"
        )
        dev.setAlignment(Qt.AlignCenter)
        layout.addWidget(dev)

        motto = QLabel("Built to serve the Church.\nShared with everyone.")
        motto.setAlignment(Qt.AlignCenter)
        motto.setObjectName("small")
        layout.addWidget(motto)

        copyright_label = QLabel(
            "Copyright © 2026\n"
            "P.A.O.C. Living Water Assembly West"
        )
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setObjectName("small")
        layout.addWidget(copyright_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Close).setText("關閉 / Close")
        layout.addWidget(buttons)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.video_path = ""
        self.thread = None
        self.worker = None

        self.setWindowTitle(f"{APP_NAME} — {APP_VERSION}")
        self.resize(760, 680)
        self.setMinimumSize(700, 620)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.welcome = self.build_welcome()
        self.main_page = self.build_main_page()

        self.stack.addWidget(self.welcome)
        self.stack.addWidget(self.main_page)
        self.stack.setCurrentWidget(self.welcome)

        self.apply_style()

    def english_font(self, size=14, bold=False):
        f = QFont("Cormorant Garamond", size)
        if QFontDatabase.hasFamily("Cormorant Garamond"):
            f.setFamily("Cormorant Garamond")
        else:
            f.setFamily("Georgia")
        f.setBold(bold)
        return f

    def chinese_font(self, size=13, bold=False):
        f = QFont("Noto Serif TC", size)
        if QFontDatabase.hasFamily("Noto Serif TC"):
            f.setFamily("Noto Serif TC")
        else:
            f.setFamily("Songti TC")
        f.setBold(bold)
        return f

    def build_welcome(self):
        page = StoneBackground()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(64, 52, 64, 44)
        layout.setSpacing(12)

        layout.addStretch(1)

        title = QLabel("Westside Stories")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(self.english_font(32, True))
        title.setObjectName("brandTitle")
        layout.addWidget(title)

        layout.addSpacing(18)

        verse = QLabel("Write the vision,\nand make it plain.")
        verse.setAlignment(Qt.AlignCenter)
        verse.setFont(self.english_font(22, False))
        verse.setObjectName("heroVerse")
        layout.addWidget(verse)

        ref = QLabel("<i>Habakkuk 2:2</i>")
        ref.setAlignment(Qt.AlignCenter)
        ref.setTextFormat(Qt.RichText)
        ref.setFont(self.english_font(13, False))
        ref.setObjectName("heroRef")
        layout.addWidget(ref)

        layout.addSpacing(18)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("goldLine")
        layout.addWidget(line)

        layout.addSpacing(18)

        zh = QLabel("將這默示明明地寫在版上，\n使讀的人容易讀。")
        zh.setAlignment(Qt.AlignCenter)
        zh.setFont(self.chinese_font(18))
        zh.setObjectName("heroZh")
        layout.addWidget(zh)

        zh_ref = QLabel('哈巴谷書 <i>2:2</i>')
        zh_ref.setAlignment(Qt.AlignCenter)
        zh_ref.setTextFormat(Qt.RichText)
        zh_ref.setFont(self.chinese_font(12))
        zh_ref.setObjectName("heroRef")
        layout.addWidget(zh_ref)

        layout.addStretch(1)

        start = QPushButton("開始  Start")
        start.setMinimumHeight(44)
        start.setMaximumWidth(220)
        start.clicked.connect(lambda: self.stack.setCurrentWidget(self.main_page))
        layout.addWidget(start, alignment=Qt.AlignCenter)

        footer = QLabel("Westside Watch  ·  P.A.O.C. Living Water Assembly West")
        footer.setAlignment(Qt.AlignCenter)
        footer.setFont(self.english_font(11))
        footer.setObjectName("footer")
        layout.addWidget(footer)

        return page

    def build_main_page(self):
        page = StoneBackground()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(36, 28, 36, 24)
        outer.setSpacing(16)

        top = QHBoxLayout()
        brand = QLabel("Westside Stories")
        brand.setFont(self.english_font(24, True))
        brand.setObjectName("brandTitle")
        top.addWidget(brand)
        top.addStretch()
        about = QPushButton("關於  About")
        about.setObjectName("secondary")
        about.clicked.connect(self.show_about)
        top.addWidget(about)
        outer.addLayout(top)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("goldLine")
        outer.addWidget(line)

        section1 = QLabel("影片  Video")
        section1.setFont(self.chinese_font(13, True))
        outer.addWidget(section1)

        file_row = QHBoxLayout()
        self.select_btn = QPushButton("選擇影片…  Select Video…")
        self.select_btn.clicked.connect(self.choose_video)
        file_row.addWidget(self.select_btn)

        self.file_label = QLabel("尚未選擇影片  No video selected")
        self.file_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.file_label.setObjectName("muted")
        file_row.addWidget(self.file_label, 1)
        outer.addLayout(file_row)

        section2 = QLabel("語言  Language")
        section2.setFont(self.chinese_font(13, True))
        outer.addWidget(section2)

        self.lang = QComboBox()
        self.lang.addItem("中文 / 粵語  Chinese / Cantonese", "zh")
        self.lang.addItem("自動偵測  Auto Detect", "auto")
        self.lang.addItem("英文  English", "en")
        outer.addWidget(self.lang)

        section3 = QLabel("輸出  Output")
        section3.setFont(self.chinese_font(13, True))
        outer.addWidget(section3)

        self.use_existing = QCheckBox("若已有同名 SRT，直接使用  ·  Use existing SRT if available")
        self.use_existing.setChecked(True)
        outer.addWidget(self.use_existing)

        self.burn = QCheckBox("完成後自動燒錄字幕影片  ·  Burn subtitles into video")
        self.burn.setChecked(True)
        outer.addWidget(self.burn)

        ai = QCheckBox("AI 字幕校訂  ·  AI Proofreading  (Coming later)")
        ai.setEnabled(False)
        outer.addWidget(ai)

        outer.addSpacing(8)

        status_header = QLabel("狀態  Status")
        status_header.setFont(self.chinese_font(13, True))
        outer.addWidget(status_header)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        outer.addWidget(self.progress)

        self.status_zh = QLabel("等待開始。")
        self.status_en = QLabel("Ready.")
        self.status_zh.setObjectName("status")
        self.status_en.setObjectName("muted")
        outer.addWidget(self.status_zh)
        outer.addWidget(self.status_en)

        bottom = QHBoxLayout()
        back = QPushButton("返回  Back")
        back.setObjectName("secondary")
        back.clicked.connect(lambda: self.stack.setCurrentWidget(self.welcome))
        bottom.addWidget(back)

        bottom.addStretch()

        self.start_btn = QPushButton("開始  Start")
        self.start_btn.setMinimumWidth(150)
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start)
        bottom.addWidget(self.start_btn)
        outer.addLayout(bottom)

        outer.addStretch()

        footer_line = QFrame()
        footer_line.setFrameShape(QFrame.HLine)
        footer_line.setObjectName("goldLine")
        outer.addWidget(footer_line)

        footer = QLabel(
            "Write the vision, and make it plain.   "
            "·   Habakkuk 2:2   ·   Westside Watch"
        )
        footer.setAlignment(Qt.AlignCenter)
        footer.setFont(self.english_font(11))
        footer.setObjectName("footer")
        outer.addWidget(footer)

        return page

    def apply_style(self):
        self.setStyleSheet(f"""
            QMainWindow, QDialog {{
                background: {DAWN_GOLD_LIGHTEST};
                color: {INK_BLACK};
            }}
            QWidget, QLabel, QPushButton, QComboBox, QCheckBox, QProgressBar {{
                font-family: "Noto Serif TC", "Songti TC";
            }}
            QLabel {{
                color: {INK_BLACK};
            }}
            QLabel#muted, QLabel#footer {{
                color: rgba(37,37,37,170);
            }}
            QLabel#brandTitle {{
                color: {INK_BLACK};
                font-family: "Cormorant Garamond", "Georgia";
            }}
            QLabel#heroVerse, QLabel#heroRef, QLabel#footer {{
                font-family: "Cormorant Garamond", "Georgia";
            }}
            QLabel#heroVerse, QLabel#heroZh {{
                color: {INK_BLACK};
            }}
            QFrame#goldLine {{
                color: {DAWN_GOLD_MEDIUM};
                background: {DAWN_GOLD_MEDIUM};
                max-height: 1px;
                border: none;
            }}
            QPushButton {{
                background: {INK_BLACK};
                color: {DAWN_GOLD_LIGHTEST};
                border: 1px solid {INK_BLACK};
                border-radius: 8px;
                padding: 9px 16px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: #3A3A3A;
            }}
            QPushButton:disabled {{
                background: #9C9A91;
                border-color: #9C9A91;
                color: #EFEBDD;
            }}
            QPushButton#secondary {{
                background: transparent;
                color: {INK_BLACK};
                border: 1px solid {DAWN_GOLD_MEDIUM};
            }}
            QPushButton#secondary:hover {{
                background: rgba(206,189,116,50);
            }}
            QComboBox {{
                background: rgba(255,255,255,150);
                border: 1px solid {DAWN_GOLD_MEDIUM};
                border-radius: 7px;
                padding: 8px 10px;
                color: {INK_BLACK};
            }}
            QCheckBox {{
                spacing: 9px;
                color: {INK_BLACK};
            }}
            QProgressBar {{
                height: 10px;
                border: 1px solid {DAWN_GOLD_MEDIUM};
                border-radius: 5px;
                background: rgba(255,255,255,100);
                text-align: center;
                color: transparent;
            }}
            QProgressBar::chunk {{
                background: {DAWN_GOLD_DEEP};
                border-radius: 4px;
            }}
        """)

    def show_about(self):
        dialog = AboutDialog(self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def choose_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇影片 / Select Video",
            str(Path.home()),
            "Video Files (*.mp4 *.mov *.m4v *.mkv);;All Files (*)"
        )
        if path:
            self.video_path = path
            self.file_label.setText(Path(path).name)
            self.status_zh.setText("已選擇影片。")
            self.status_en.setText("Video selected.")
            self.start_btn.setEnabled(True)

    def update_status(self, zh, en):
        self.status_zh.setText(zh)
        self.status_en.setText(en)

    def start(self):
        if not self.video_path:
            return

        self.select_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.lang.setEnabled(False)
        self.use_existing.setEnabled(False)
        self.burn.setEnabled(False)
        self.progress.setValue(0)

        self.thread = QThread()
        self.worker = Worker(
            self.video_path,
            self.lang.currentData(),
            self.use_existing.isChecked(),
            self.burn.isChecked(),
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.status.connect(self.update_status)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)

        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.cleanup_thread)
        self.thread.start()

    def cleanup_thread(self):
        self.select_btn.setEnabled(True)
        self.start_btn.setEnabled(True)
        self.lang.setEnabled(True)
        self.use_existing.setEnabled(True)
        self.burn.setEnabled(True)
        self.worker = None
        self.thread = None

    def on_finished(self, srt, output):
        if output:
            subprocess.run(["/usr/bin/open", "-R", output])
            QMessageBox.information(
                self,
                APP_NAME,
                f"完成！ / Completed\n\n"
                f"字幕 / Subtitle:\n{Path(srt).name}\n\n"
                f"影片 / Video:\n{Path(output).name}"
            )
        else:
            subprocess.run(["/usr/bin/open", "-R", srt])
            QMessageBox.information(
                self,
                APP_NAME,
                f"字幕已完成 / Subtitle completed\n\n{Path(srt).name}"
            )

    def on_failed(self, message):
        self.update_status("失敗。", "Failed.")
        QMessageBox.critical(
            self,
            APP_NAME,
            message + "\n\n完整日誌 / Full log:\nDesktop/WestsideStories.log"
        )

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("P.A.O.C. Living Water Assembly West")

    # Match the Westside Watch Join page:
    # Traditional Chinese UI uses a serif family.
    ui_font = QFont("Noto Serif TC", 13)
    if QFontDatabase.hasFamily("Noto Serif TC"):
        ui_font.setFamily("Noto Serif TC")
    else:
        ui_font.setFamily("Songti TC")
    app.setFont(ui_font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
