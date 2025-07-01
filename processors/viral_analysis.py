import os
import pandas as pd

from .base import ProcessingStep, Colors
from gemini_interaction import identify_viral_clips_gemini


class ViralAnalysisStep(ProcessingStep):
    @property
    def is_complete(self):
        analysis_path = self.entry.get("analysis_path")
        return (
            self.entry.get("status_analysis_generated") is True
            and pd.notna(analysis_path)
            and os.path.exists(analysis_path)
            and os.path.getsize(analysis_path) > 0
        )

    def process(self):
        transcript_path = self.entry.get("transcript_path")
        if pd.isna(transcript_path) or not os.path.exists(transcript_path):
            print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Transcript not available for viral analysis.")
            self.entry["status_analysis_generated"] = False
            return self.entry

        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript_text = f.read()

        if not transcript_text.strip():
            print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Transcript file is empty, cannot perform analysis.")
            self.entry["status_analysis_generated"] = False
            return self.entry

        os.makedirs(self.args.effective_analysis_dir, exist_ok=True)
        analysis_path = identify_viral_clips_gemini(
            transcript_text,
            self.args.number_of_sections,
            self.args.clip_identifier_model,
            self.args.effective_analysis_dir,
            self.base_name,
        )

        if (
            analysis_path
            and os.path.exists(analysis_path)
            and os.path.getsize(analysis_path) > 0
        ):
            self.entry["analysis_path"] = analysis_path
            self.entry["status_analysis_generated"] = True
        else:
            self.entry["analysis_path"] = analysis_path if analysis_path else pd.NA
            self.entry["status_analysis_generated"] = False
        return self.entry