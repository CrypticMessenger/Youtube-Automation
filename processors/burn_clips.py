import os
import json
import subprocess
import re
from .base import ProcessingStep, Colors

class BurnClipsStep(ProcessingStep):
    def __init__(self, entry, args):
        super().__init__(entry, args)
        self.clips_dir = os.path.join(self.args.output, "viral_clips")
        self.captioned_clips_dir = os.path.join(self.args.output, "captioned_clips")
        self.timestamp_file_path = os.path.join(
            self.args.output, "viral_clip_timestamps", f"{self.base_name}_timestamps.json"
        )

    @property
    def is_complete(self):
        if not os.path.exists(self.captioned_clips_dir):
            return False
        
        try:
            with open(self.timestamp_file_path, "r") as f:
                timestamps_data = json.load(f)
            num_clips = len(timestamps_data.get("segments", []))
            
            captioned_clips = [f for f in os.listdir(self.captioned_clips_dir) if f.startswith(self.base_name) and f.endswith(".mp4")]
            return len(captioned_clips) >= num_clips
        except FileNotFoundError:
            return False

    @staticmethod
    def _time_to_seconds(time_str):
        if isinstance(time_str, (int, float)):
            return float(time_str)
        
        time_str = str(time_str).replace(",", ".")
        
        if ":" not in time_str:
            return float(time_str)
        
        parts = time_str.split(":")
        h, m, s = map(float, parts)
        return h * 3600 + m * 60 + s

    @staticmethod
    def _seconds_to_ass_time(seconds):
        h = int(seconds / 3600)
        m = int((seconds % 3600) / 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    def process(self):
        ass_path = os.path.join(
            self.args.effective_caption_dir, self.base_name + ".ass"
        )

        if not os.path.exists(ass_path):
            print(f"{Colors.ERROR}[ERROR]{Colors.RESET} ASS caption file not found: {ass_path}")
            return self.entry

        if not os.path.exists(self.timestamp_file_path):
            print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Timestamps JSON not found: {self.timestamp_file_path}")
            return self.entry

        with open(self.timestamp_file_path, "r") as f:
            timestamps_data = json.load(f)
        
        with open(ass_path, 'r', encoding='utf-8') as f:
            ass_content_lines = f.readlines()

        os.makedirs(self.captioned_clips_dir, exist_ok=True)

        for i, segment in enumerate(timestamps_data.get("segments", [])):
            start_time_sec = self._time_to_seconds(segment["start_time"]) - 1
            if start_time_sec < 0:
                start_time_sec = 0
            end_time_sec = self._time_to_seconds(segment["end_time"]) + 1
            
            clip_base_name = f"{self.base_name}_clip_{i+1}"
            clip_path = os.path.join(self.clips_dir, f"{clip_base_name}.mp4")
            
            if not os.path.exists(clip_path):
                print(f"{Colors.WARNING}[WARNING]{Colors.RESET} Clip not found, skipping: {clip_path}")
                continue

            temp_ass_path = os.path.join(self.captioned_clips_dir, f"temp_{clip_base_name}.ass")
            
            adjusted_ass_lines = []
            for line in ass_content_lines:
                if line.startswith("Style:"):
                    parts = line.strip().split(",", 3)
                    parts[2] = "16" # Change font size to 16
                    # Adjust MarginV (vertical margin) to move subtitles up
                    # MarginV is the 21st element (index 20) in the Style line
                    style_parts = line.strip().split(",")
                    if len(style_parts) > 20:
                        style_parts[20] = "50" # Set MarginV to 50 (adjust as needed)
                        adjusted_ass_lines.append(",".join(style_parts) + "\n")
                    else:
                        adjusted_ass_lines.append(line) # Fallback if format is unexpected
                elif line.startswith("Dialogue:"):
                    parts = line.strip().split(",", 9)
                    try:
                        start = self._time_to_seconds(parts[1])
                        end = self._time_to_seconds(parts[2])

                        # If the subtitle is within the clip's time range
                        if start >= start_time_sec and end <= end_time_sec:
                            new_start = start - start_time_sec
                            new_end = end - start_time_sec
                            
                            parts[1] = self._seconds_to_ass_time(new_start)
                            parts[2] = self._seconds_to_ass_time(new_end)
                            adjusted_ass_lines.append(",".join(parts) + "\n")

                    except (ValueError, IndexError):
                        adjusted_ass_lines.append(line) # Keep malformed lines as is
                else:
                    adjusted_ass_lines.append(line)

            with open(temp_ass_path, 'w', encoding='utf-8') as f:
                f.writelines(adjusted_ass_lines)

            captioned_clip_path = os.path.join(self.captioned_clips_dir, f"{clip_base_name}.mp4")
            
            command = [
                "ffmpeg", "-y",
                "-i", clip_path,
                "-vf", f"ass={temp_ass_path}",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                captioned_clip_path
            ]
            
            try:
                print(f"{Colors.INFO}[INFO]{Colors.RESET} Burning subtitles for {clip_base_name}...")
                subprocess.run(command, check=True, capture_output=True, text=True)
                print(f"{Colors.SUCCESS}[SUCCESS]{Colors.RESET} Created captioned clip: {captioned_clip_path}")
            except subprocess.CalledProcessError as e:
                print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Failed to burn subtitles for {clip_base_name}.")
                print(f"FFmpeg stdout: {e.stdout}")
                print(f"FFmpeg stderr: {e.stderr}")
            finally:
                if os.path.exists(temp_ass_path):
                    os.remove(temp_ass_path)
                    
        return self.entry
