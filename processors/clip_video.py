import os
import json
import subprocess
import pandas as pd

from .base import ProcessingStep, Colors


class ClipVideoStep(ProcessingStep):
    @staticmethod
    def _time_to_seconds(time_str):
        time_str = time_str.split(",")[0] if "," in time_str else time_str
        h, m, s = map(float, time_str.split(":"))
        return h * 3600 + m * 60 + s
    def __init__(self, entry, args):
        super().__init__(entry, args)
        self.clips_output_dir = os.path.join(self.args.output, "viral_clips")
        self.video_path = self.entry.get("video_path")
        self.timestamp_file_path = os.path.join(
            self.args.output, "viral_clip_timestamps", f"{self.base_name}_timestamps.json"
        )

    @property
    def is_complete(self):
        if not os.path.exists(self.clips_output_dir):
            return False
        for f in os.listdir(self.clips_output_dir):
            if f.startswith(self.base_name) and f.endswith(".mp4"):
                return True
        return False

    def process(self):
        if not os.path.exists(self.video_path):
            print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Video not found at: {self.video_path}")
            return self.entry
        if not os.path.exists(self.timestamp_file_path):
            print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Timestamps JSON not found at: {self.timestamp_file_path}")
            return self.entry

        with open(self.timestamp_file_path, "r") as f:
            timestamps_data = json.load(f)

        os.makedirs(self.clips_output_dir, exist_ok=True)

        for i, segment in enumerate(timestamps_data.get("segments", [])):
            start_time = segment.get("start_time")
            end_time = segment.get("end_time")
            clip_output_path = os.path.join(
                self.clips_output_dir, f"{self.base_name}_clip_{i+1}.mp4"
            )

            if not start_time or not end_time:
                print(f"{Colors.WARNING}[WARNING]{Colors.RESET} Skipping segment {i+1} due to missing timestamps.")
                continue

            # Convert to seconds, round to nearest second, and convert back to string
            start_time_sec = str(int(round(self._time_to_seconds(start_time))))
            end_time_sec = str(int(round(self._time_to_seconds(end_time))))

            # add -1 to start time and +1 to end time
            start_time_sec = str(int(start_time_sec) - 1)
            end_time_sec = str(int(end_time_sec) + 1)
            # Ensure the start time is not negative
            if int(start_time_sec) < 0:
                start_time_sec = "0"

            print(f"{Colors.INFO}[INFO]{Colors.RESET} Clipping segment {i+1}: {start_time_sec} -> {end_time_sec}")
            try:
                if getattr(self.args, 'no_reel', False):
                    print(f"{Colors.INFO}[INFO]{Colors.RESET} Re-encoding to 16:9 horizontal aspect ratio.")
                    command = [
                        "ffmpeg", "-y",
                        "-i", self.video_path,
                        "-ss", start_time_sec,
                        "-to", end_time_sec,
                        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                        "-c:v", "libx264",
                        "-preset", "veryfast",
                        "-crf", "23",
                        "-c:a", "aac",
                        "-b:a", "128k",
                        "-avoid_negative_ts", "make_zero",
                        clip_output_path,
                    ]
                else:
                    print(f"{Colors.INFO}[INFO]{Colors.RESET} Re-encoding to 9:16 vertical aspect ratio for Reels/Shorts.")
                    command = [
                        "ffmpeg", "-y",
                        "-i", self.video_path,
                        "-ss", start_time_sec,
                        "-to", end_time_sec,
                        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
                        "-c:v", "libx264",
                        "-preset", "veryfast",
                        "-crf", "23",
                        "-c:a", "aac",
                        "-b:a", "128k",
                        "-avoid_negative_ts", "make_zero",
                        clip_output_path,
                    ]
                subprocess.run(
                    command, check=True
                )
                print(f"{Colors.SUCCESS}[SUCCESS]{Colors.RESET} Saved clip to {clip_output_path}")
            except subprocess.CalledProcessError as e:
                print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Failed to clip video for segment {i+1}.")
                print(f"ffmpeg stderr: {e.stderr.decode()}")
            except Exception as e:
                print(f"{Colors.ERROR}[ERROR]{Colors.RESET} An unexpected error occurred during clipping: {e}")
        return self.entry