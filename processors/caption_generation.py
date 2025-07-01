import os
import pandas as pd

from .base import ProcessingStep, Colors
from audio_processing import generate_caption_files


class CaptionGenerationStep(ProcessingStep):
    @property
    def is_complete(self):
        return (
            self.entry.get("status_captions_generated") is True
            and pd.notna(self.entry.get("caption_srt_path"))
            and os.path.exists(self.entry.get("caption_srt_path"))
            and pd.notna(self.entry.get("transcript_path"))
            and os.path.exists(self.entry.get("transcript_path"))
        )

    def process(self):
        mp3_path = self.entry.get("mp3_path")
        if pd.isna(mp3_path) or not os.path.exists(mp3_path):
            print(f"{Colors.ERROR}[ERROR]{Colors.RESET} MP3 file not available for caption generation.")
            self.entry["status_captions_generated"] = False
            self.entry["status_transcript_generated"] = False
            return self.entry

        os.makedirs(self.args.effective_caption_dir, exist_ok=True)
        os.makedirs(self.args.effective_transcript_dir, exist_ok=True)

        caption_paths = generate_caption_files(
            mp3_path,
            self.args.effective_caption_dir,
            self.base_name,
            self.args.whisper_model,
            self.args.effective_transcript_dir, # Pass transcript dir
        )

        if caption_paths and "srt" in caption_paths:
            self.entry["caption_srt_path"] = caption_paths.get("srt")
            self.entry["status_captions_generated"] = True
        else:
            self.entry["caption_srt_path"] = pd.NA
            self.entry["status_captions_generated"] = False

        if caption_paths and "txt" in caption_paths:
            self.entry["transcript_path"] = caption_paths.get("txt")
            self.entry["status_transcript_generated"] = True
        else:
            self.entry["transcript_path"] = pd.NA
            self.entry["status_transcript_generated"] = False

        return self.entry
