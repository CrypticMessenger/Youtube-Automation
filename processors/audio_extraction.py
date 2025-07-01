import os
import pandas as pd

from .base import ProcessingStep, Colors
from youtube_utils import get_video_info, download_audio_stream
from audio_processing import convert_to_mp3


class AudioExtractionStep(ProcessingStep):
    @property
    def is_complete(self):
        return (
            self.entry.get("status_mp3_converted") is True
            and pd.notna(self.entry.get("mp3_path"))
            and os.path.exists(self.entry.get("mp3_path"))
        )

    def process(self):
        source_for_ffmpeg = None
        video_path = self.entry.get("video_path")

        if pd.notna(video_path) and os.path.exists(video_path):
            print(f"{Colors.INFO}[INFO]{Colors.RESET} Using downloaded video as source for MP3: {video_path}")
            source_for_ffmpeg = video_path
        else:
            print(f"{Colors.INFO}[INFO]{Colors.RESET} Video not found, downloading dedicated audio stream...")
            video_info = get_video_info(self.url)
            if not video_info:
                self.entry["status_mp3_converted"] = False
                return self.entry
            source_for_ffmpeg = download_audio_stream(
                video_info,
                self.base_name,
                self.args.effective_audio_dir,
                self.args.audio_quality,
            )

        if not source_for_ffmpeg:
            print(f"{Colors.ERROR}[ERROR]{Colors.RESET} No valid source for audio extraction.")
            self.entry["mp3_path"] = pd.NA
            self.entry["status_mp3_converted"] = False
            return self.entry

        os.makedirs(self.args.effective_audio_dir, exist_ok=True)
        final_mp3_path = os.path.join(
            self.args.effective_audio_dir, self.base_name + ".mp3"
        )
        converted_path = convert_to_mp3(source_for_ffmpeg, final_mp3_path)

        if converted_path:
            self.entry["mp3_path"] = converted_path
            self.entry["status_mp3_converted"] = True
        else:
            self.entry["mp3_path"] = pd.NA
            self.entry["status_mp3_converted"] = False
        return self.entry