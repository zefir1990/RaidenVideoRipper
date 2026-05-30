import os
import sys
import subprocess
import threading
import uuid
from utils import get_asset_path
from constants import OUTPUT_FILE_SUFFIX

class VideoProcessingThread(threading.Thread):
    def __init__(self, start_position, end_position, video_path, output_formats, callback_progress, callback_finished, stabilize_video=False, crop_arguments=None, watermark_arguments=None, use_random_name=False):
        super().__init__()
        self.start_position = start_position
        self.end_position = end_position
        self.video_path = video_path
        self.output_formats = output_formats
        self.callback_progress = callback_progress
        self.callback_finished = callback_finished
        self.stabilize_video = stabilize_video
        self.crop_arguments = crop_arguments
        self.watermark_arguments = watermark_arguments
        self.use_random_name = use_random_name
        self.current_process = None
        self.is_cancelled = False
        self.ffmpeg_binary = get_asset_path(os.path.join("bin", "ffmpeg.exe"))

    def run(self):
        trf_filename = os.path.basename(self.video_path) + ".trf"
        working_directory = os.path.dirname(self.video_path)
        if self.stabilize_video:
            pass1_args = [
                self.ffmpeg_binary, "-y", "-i", self.video_path,
                "-ss", f"{self.start_position}ms", "-to", f"{self.end_position}ms",
                "-vf", f"vidstabdetect=shakiness=10:accuracy=15:result='{trf_filename}'",
                "-f", "null", "-"
            ]
            success = self.run_ffmpeg(pass1_args, "Stabilization Pass 1", working_directory)
            if not success or self.is_cancelled:
                self.callback_finished(False, self.is_cancelled)
                return

        random_prefix = uuid.uuid4().hex[:8]

        for output_format in self.output_formats:
            if self.is_cancelled:
                break
            directory = os.path.dirname(self.video_path)
            basename = os.path.basename(self.video_path)
            if self.use_random_name:
                output_filename = f"{random_prefix}_{basename}{OUTPUT_FILE_SUFFIX}.{output_format.extension}"
            else:
                output_filename = f"{basename}{OUTPUT_FILE_SUFFIX}.{output_format.extension}"
            output_path = os.path.join(directory, output_filename)
            arguments = [
                self.ffmpeg_binary,
                "-y",
                "-i", self.video_path
            ]
            if self.watermark_arguments:
                arguments.extend(["-i", self.watermark_arguments[0]])
            arguments.extend([
                "-ss", f"{self.start_position}ms",
                "-to", f"{self.end_position}ms"
            ])

            video_filters = []
            if self.stabilize_video:
                video_filters.append(f"vidstabtransform=input='{trf_filename}':zoom=5")
            if self.crop_arguments:
                width, height, x, y = self.crop_arguments
                video_filters.append(f"crop={width}:{height}:{x}:{y}")

            if self.watermark_arguments:
                watermark_path, w, h, x, y = self.watermark_arguments
                filter_parts = []
                if video_filters:
                    filter_parts.append(f"[0:v]{','.join(video_filters)}[main_video]")
                    video_source = "[main_video]"
                else:
                    video_source = "[0:v]"
                filter_parts.append(f"[1:v]scale={w}:{h}[watermark_scaled]")
                filter_parts.append(f"{video_source}[watermark_scaled]overlay={x}:{y}")
                arguments.extend(["-filter_complex", ";".join(filter_parts)])
            elif video_filters:
                arguments.extend(["-vf", ",".join(video_filters)])

            arguments.extend(output_format.custom_arguments)
            arguments.append(output_path)

            success = self.run_ffmpeg(arguments, output_format.title, working_directory)
            if not success or self.is_cancelled:
                self.callback_finished(False, self.is_cancelled)
                return
        self.callback_finished(True, False)

    def run_ffmpeg(self, arguments, format_title, working_directory=None):
        command = [arguments[0], "-progress", "-"] + arguments[1:]
        print(f"Executing FFmpeg command: {' '.join(command)}")
        startup_info = None
        if sys.platform == "win32":
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = subprocess.SW_HIDE

        try:
            self.current_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                startupinfo=startup_info,
                text=True,
                bufsize=1,
                cwd=working_directory
            )
        except Exception as e:
            print(f"Failed to start FFmpeg: {e}")
            return False

        duration_milliseconds = self.end_position - self.start_position
        if duration_milliseconds <= 0:
            duration_milliseconds = 1

        while True:
            line = self.current_process.stdout.readline()
            if not line:
                break
            line = line.strip()
            print(f"FFmpeg: {line}")
            if line.startswith("out_time_us="):
                try:
                    microseconds = int(line.split("=")[1])
                    milliseconds = microseconds // 1000
                    percentage = int((milliseconds / duration_milliseconds) * 100)
                    percentage = max(0, min(100, percentage))
                    self.callback_progress(format_title, percentage)
                except ValueError:
                    pass
            elif line.startswith("progress=end"):
                pass

        self.current_process.wait()
        print(f"FFmpeg process finished with return code: {self.current_process.returncode}")
        return self.current_process.returncode == 0

    def cancel(self):
        self.is_cancelled = True
        if self.current_process:
            try:
                self.current_process.terminate()
            except Exception:
                pass
