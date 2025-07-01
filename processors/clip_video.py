import os
import json
import subprocess
import pandas as pd

from .base import ProcessingStep, Colors


class ClipVideoStep(ProcessingStep):
    def __init__(self, entry, args):
        super().__init__(entry, args)
        self.clips_output_dir = os.path.join(self.args.output, "viral_clips")
        self.burned_video_path = os.path.join(
            self.args.output, "captioned_videos", f"{self.base_name}_captioned.mp4"
        )
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
        if not os.path.exists(self.burned_video_path):
            print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Burned video not found at: {self.burned_video_path}")
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

            print(f"{Colors.INFO}[INFO]{Colors.RESET} Clipping segment {i+1}: {start_time} -> {end_time}")
            try:
                command = [
                    "ffmpeg", "-y",
                    "-i", self.burned_video_path,
                    "-ss", start_time.replace(",", "."),
                    "-to", end_time.replace(",", "."),
                    "-c", "copy",
                    clip_output_path,
                ]
                subprocess.run(
                    command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
                )
                print(f"{Colors.SUCCESS}[SUCCESS]{Colors.RESET} Saved clip to {clip_output_path}")
            except subprocess.CalledProcessError as e:
                print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Failed to clip video for segment {i+1}.")
                print(f"ffmpeg stderr: {e.stderr.decode()}")
            except Exception as e:
                print(f"{Colors.ERROR}[ERROR]{Colors.RESET} An unexpected error occurred during clipping: {e}")
        return self.entry