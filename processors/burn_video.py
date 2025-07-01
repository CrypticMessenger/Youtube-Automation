
import os
import pandas as pd

from .base import ProcessingStep
from video_processing import generate_video_with_captions


class BurnVideoStep(ProcessingStep):
    def __init__(self, entry, args):
        super().__init__(entry, args)
        self.burned_video_dir = os.path.join(self.args.output, "captioned_videos")
        self.burned_video_path = os.path.join(
            self.burned_video_dir, f"{self.base_name}_captioned.mp4"
        )

    @property
    def is_complete(self):
        return os.path.exists(self.burned_video_path)

    def process(self):
        video_path = self.entry.get("video_path")
        audio_path = self.entry.get("mp3_path")
        ass_path = os.path.join(
            self.args.effective_caption_dir, self.base_name + ".ass"
        )

        if pd.isna(video_path) or not os.path.exists(video_path):
            print("[ERROR] Video file not available for burning subtitles.")
            return self.entry

        if pd.isna(audio_path) or not os.path.exists(audio_path):
            print("[ERROR] Audio file not available for burning subtitles.")
            return self.entry
        if not os.path.exists(ass_path):
            print(f"[ERROR] ASS caption file not found at expected path: {ass_path}")
            return self.entry

        os.makedirs(self.burned_video_dir, exist_ok=True)
        burned_path = generate_video_with_captions(
            video_path, audio_path, ass_path, self.burned_video_path
        )

        if burned_path:
            print(f"[SUCCESS] Video with burned subtitles created at: {burned_path}")
        else:
            print("[ERROR] Failed to burn subtitles.")
        return self.entry
