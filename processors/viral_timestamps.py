import os
import json
import pandas as pd

from .base import ProcessingStep, Colors
from gemini_interaction import get_viral_timestamps_gemini


class ViralTimestampsStep(ProcessingStep):
    def __init__(self, entry, args):
        super().__init__(entry, args)
        self.timestamps_dir = os.path.join(self.args.output, "viral_clip_timestamps")
        self.timestamp_file_path = os.path.join(
            self.timestamps_dir, f"{self.base_name}_timestamps.json"
        )

    @property
    def is_complete(self):
        return os.path.exists(self.timestamp_file_path)

    def process(self):
        srt_path = self.entry.get("caption_srt_path")
        analysis_path = self.entry.get("analysis_path")

        if pd.isna(srt_path) or not os.path.exists(srt_path):
            print(f"{Colors.ERROR}[ERROR]{Colors.RESET} SRT file not found for timestamp extraction.")
            return self.entry
        if pd.isna(analysis_path) or not os.path.exists(analysis_path):
            print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Analysis file not found for timestamp extraction.")
            return self.entry

        with open(srt_path, "r", encoding="utf-8") as f:
            srt_content = f.read()
        with open(analysis_path, "r", encoding="utf-8") as f:
            analysis_content = f.read()

        timestamps_json = get_viral_timestamps_gemini(
            srt_content, analysis_content, self.args.clip_identifier_model
        )

        if timestamps_json:
            os.makedirs(self.timestamps_dir, exist_ok=True)
            with open(self.timestamp_file_path, "w", encoding="utf-8") as f:
                json.dump(timestamps_json, f, indent=4)
            print(f"{Colors.SUCCESS}[SUCCESS]{Colors.RESET} Viral timestamps saved to: {self.timestamp_file_path}")
        else:
            print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Could not retrieve viral timestamps.")
        return self.entry