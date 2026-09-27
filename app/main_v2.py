"""Westside Stories production entrypoint: stable ASR + local Church Corrector."""
from __future__ import annotations
import shutil, subprocess, tempfile
from pathlib import Path
import main as stable_main
from main import Worker, log
from subtitle_style import profile_for_video
stable_main.APP_VERSION = "1.2"
_original_transcribe = Worker.transcribe
_original_write_srt = Worker.write_srt


def _transcribe_production(self, vpy: str, result_json: Path):
    return _original_transcribe(self, vpy, result_json)


def _write_srt_production(self, result_json, srt_path):
    _original_write_srt(self, result_json, srt_path)
    from church_corrector import apply_to_srt_text
    original = Path(srt_path).read_text(encoding="utf-8")
    corrected, summary = apply_to_srt_text(original)
    Path(srt_path).write_text(corrected, encoding="utf-8")
    log(f"CHURCH CORRECTOR: changed_lines={summary['changed_lines']} corrections={summary['corrections']}")


def _probe_video_size(ffmpeg: str, video: Path):
    ffprobe = str(Path(ffmpeg).with_name("ffprobe"))
    if not Path(ffprobe).is_file(): return None, None
    try:
        p = subprocess.run([ffprobe,"-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","csv=s=x:p=0",str(video)],text=True,capture_output=True,env=stable_main.os.environ.copy()); w,h=(p.stdout or "").strip().split("x",1); return int(w),int(h)
    except Exception: return None,None


def _burn_with_style(self, ffmpeg: str, srt: Path, output: Path):
    self.status.emit("正在使用 Mac 硬體快速燒錄字幕…", "Burning subtitles with Mac hardware acceleration…"); self.progress.emit(75); tmp_path=None
    try:
        with tempfile.NamedTemporaryFile(suffix=".srt",delete=False) as tmp: tmp_path=Path(tmp.name)
        shutil.copyfile(srt,tmp_path); width,height=_probe_video_size(ffmpeg,self.video); style=profile_for_video(width,height); force_style=style.ass_force_style().replace("'","\\'"); subtitle_filter="subtitles=filename='"+str(tmp_path).replace("'","\\'")+"':force_style='"+force_style+"'"; log(f"subtitle style: {width}x{height}; {style.ass_force_style()}")
        cmd=[ffmpeg,"-y","-i",str(self.video),"-vf",subtitle_filter,"-c:v","h264_videotoolbox","-q:v","65","-allow_sw","1","-c:a","copy","-movflags","+faststart",str(output)]; p=subprocess.run(cmd,text=True,capture_output=True,env=stable_main.os.environ.copy()); log("ffmpeg stdout:\n"+(p.stdout or "")); log("ffmpeg stderr:\n"+(p.stderr or ""))
        if p.returncode!=0: raise RuntimeError("FFmpeg 硬體燒錄失敗。\nFFmpeg hardware burn-in failed.\n\n請查看桌面 WestsideStories.log。")
    finally:
        if tmp_path:
            try: tmp_path.unlink(missing_ok=True)
            except Exception: pass


def _safe_cleanup_thread(self):
    """Do not drop the last Python reference while Qt is emitting QThread.finished."""
    thread = self.thread
    worker = self.worker
    self.select_btn.setEnabled(True)
    self.start_btn.setEnabled(True)
    self.lang.setEnabled(True)
    self.use_existing.setEnabled(True)
    self.burn.setEnabled(True)
    self.worker = None
    if worker is not None:
        worker.deleteLater()
    if thread is not None:
        thread.deleteLater()
    # Keep self.thread referenced until Qt owns/deletes the stopped thread.


Worker.transcribe=_transcribe_production
Worker.write_srt=_write_srt_production
Worker.burn=_burn_with_style
stable_main.MainWindow.cleanup_thread=_safe_cleanup_thread
if __name__=="__main__": stable_main.main()
