
import os
import pandas as pd

from .base import ProcessingStep
from youtube_utils import get_video_info, download_video


class VideoDownloadStep(ProcessingStep):
    @property
    def is_complete(self):
        return (
            self.entry.get("status_video_downloaded") is True
            and pd.notna(self.entry.get("video_path"))
            and os.path.exists(self.entry.get("video_path"))
        )

    def process(self):
        video_info = get_video_info(self.url)
        if not video_info:
            self.entry["status_video_downloaded"] = False
            return self.entry

        downloaded_path = download_video(
            video_info,
            self.base_name,
            self.args.effective_video_dir,
            self.args.video_quality,
        )

        if downloaded_path:
            self.entry["video_path"] = downloaded_path
            self.entry["status_video_downloaded"] = True
        else:
            self.entry["video_path"] = pd.NA
            self.entry["status_video_downloaded"] = False
        return self.entry
