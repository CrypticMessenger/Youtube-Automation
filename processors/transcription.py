
import os
import pandas as pd

from .base import ProcessingStep
from audio_processing import transcribe_audio_stable_ts


class TranscriptionStep(ProcessingStep):
    @property
    def is_complete(self):
        return (
            self.entry.get("status_transcript_generated") is True
            and pd.notna(self.entry.get("transcript_path"))
            and os.path.exists(self.entry.get("transcript_path"))
        )

    def process(self):
        mp3_path = self.entry.get("mp3_path")
        if pd.isna(mp3_path) or not os.path.exists(mp3_path):
            print("[ERROR] MP3 file not available for transcription.")
            self.entry["status_transcript_generated"] = False
            return self.entry

        os.makedirs(self.args.effective_transcript_dir, exist_ok=True)
        transcript_path = transcribe_audio_stable_ts(
            mp3_path,
            self.args.effective_transcript_dir,
            self.base_name,
            self.args.whisper_model,
        )

        if transcript_path:
            self.entry["transcript_path"] = transcript_path
            self.entry["status_transcript_generated"] = True
        else:
            self.entry["transcript_path"] = pd.NA
            self.entry["status_transcript_generated"] = False
        return self.entry
