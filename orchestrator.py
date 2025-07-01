import os
import pandas as pd

from manifest import (
    load_manifest,
    save_manifest,
    get_manifest_entry,
    update_manifest_entry,
    DEFAULT_MANIFEST_FILE,
)
from youtube_utils import (
    get_sanitized_base_name,
    get_yt_object_and_canonical_url,
    get_video_info,
)
from processors import (
    VideoDownloadStep,
    AudioExtractionStep,
    TranscriptionStep,
    CaptionGenerationStep,
    ViralAnalysisStep,
    ViralTimestampsStep,
    BurnVideoStep,
    ClipVideoStep,
)

# --- Dependency Graph Definition ---

STEP_DEPENDENCIES = {
    ClipVideoStep: [BurnVideoStep, ViralTimestampsStep],
    BurnVideoStep: [VideoDownloadStep, CaptionGenerationStep],
    ViralTimestampsStep: [CaptionGenerationStep, ViralAnalysisStep],
    ViralAnalysisStep: [TranscriptionStep],
    CaptionGenerationStep: [AudioExtractionStep],
    TranscriptionStep: [AudioExtractionStep],
    AudioExtractionStep: [VideoDownloadStep],
    VideoDownloadStep: [],
}

# The full pipeline in a reasonable execution order for a full run.
FULL_PIPELINE = [
    VideoDownloadStep,
    AudioExtractionStep,
    TranscriptionStep,
    CaptionGenerationStep,
    ViralAnalysisStep,
    ViralTimestampsStep,
    BurnVideoStep,
    ClipVideoStep,
]


class Orchestrator:
    def __init__(self, args):
        self.args = args
        self.manifest_path = os.path.join(args.output, DEFAULT_MANIFEST_FILE)
        self.manifest_df = load_manifest(self.manifest_path)
        self.completed_steps = set()

    def _execute_step(self, step_class, entry_dict):
        """
        Executes a single step, ensuring its dependencies are met first.
        Uses a set `self.completed_steps` to avoid re-running steps in the same session.
        """
        if step_class in self.completed_steps:
            return entry_dict

        # --- 1. Resolve Dependencies First ---
        dependencies = STEP_DEPENDENCIES.get(step_class, [])
        for dep_class in dependencies:
            entry_dict = self._execute_step(dep_class, entry_dict)

        # --- 2. Execute the Current Step ---
        step = step_class(entry_dict, self.args)
        entry_dict = step.run()

        # --- 3. Mark as Complete ---
        self.completed_steps.add(step_class)
        return entry_dict

    def _get_target_steps(self):
        """Determines which final steps the user wants to run based on CLI flags."""
        targets = []
        if getattr(self.args, 'clip_video', False):
            targets.append(ClipVideoStep)
        if getattr(self.args, 'burn_video', False):
            targets.append(BurnVideoStep)
        if getattr(self.args, 'get_viral_timestamps', False):
            targets.append(ViralTimestampsStep)
        if getattr(self.args, 'viral_short_identifier', False):
            targets.append(ViralAnalysisStep)
        if getattr(self.args, 'generate_captions', False):
            targets.append(CaptionGenerationStep)
        if getattr(self.args, 'transcribe', False):
            targets.append(TranscriptionStep)
        if getattr(self.args, 'extract_audio', False):
            targets.append(AudioExtractionStep)
        if getattr(self.args, 'download_video', False):
            targets.append(VideoDownloadStep)

        # If no specific flags are given, run the entire pipeline.
        if not targets:
            return FULL_PIPELINE
        return targets

    def process_url(self, url):
        """
        Processes a YouTube URL by executing the requested steps and their dependencies.
        """
        _, canonical_url = get_yt_object_and_canonical_url(url)
        if not canonical_url:
            return

        video_info = get_video_info(canonical_url)
        if not video_info:
            return

        # --- 1. Get or Create Manifest Entry ---
        entry = get_manifest_entry(self.manifest_df, canonical_url)
        base_name = get_sanitized_base_name(
            video_info.get("title", "default_title"), self.args.filename
        )

        if entry is None:
            print(f"[INFO] Creating new manifest entry for {canonical_url}")
            entry_data = {"youtube_url": canonical_url, "base_filename": base_name}
            self.manifest_df = update_manifest_entry(
                self.manifest_df, canonical_url, entry_data
            )
            entry = get_manifest_entry(self.manifest_df, canonical_url)
        else:
            entry["base_filename"] = base_name

        entry_dict = entry.to_dict()

        # --- 2. Determine and Execute Target Steps ---
        target_steps = self._get_target_steps()
        if not target_steps:
            print("[INFO] No processing steps were selected. Exiting.")
            return

        print(f"[INFO] Target steps: {[s.__name__ for s in target_steps]}")

        for step_class in target_steps:
            entry_dict = self._execute_step(step_class, entry_dict)

        # --- 3. Save Final Manifest ---
        self.manifest_df = update_manifest_entry(
            self.manifest_df, canonical_url, entry_dict
        )
        save_manifest(self.manifest_df, self.manifest_path)
        print(f"\n[SUCCESS] Orchestration complete for {canonical_url}.")

    def list_manifest(self):
        if self.manifest_df.empty:
            print("[INFO] Manifest is empty.")
            return
        print("\n--- Manifest Contents ---")
        with pd.option_context(
            "display.max_colwidth", 50, "display.width", 1000, "display.max_rows", 25
        ):
            display_cols = [col for col in self.manifest_df.columns]
            print(self.manifest_df[display_cols].head(20).to_string())
        print(f"--- Total entries: {len(self.manifest_df)} ---")

    def remove_url(self, url_to_remove):
        _, canonical_url = get_yt_object_and_canonical_url(url_to_remove)
        if not canonical_url:
            canonical_url = url_to_remove

        entry = get_manifest_entry(self.manifest_df, canonical_url)
        if entry is None:
            print(f"[INFO] URL not found in manifest: {canonical_url}")
            return

        print(f"[INFO] Removing URL '{canonical_url}' and associated files.")
        base_name = entry.get('base_filename')
        potential_paths = [
            entry.get("video_path"),
            entry.get("mp3_path"),
            entry.get("transcript_path"),
            entry.get("analysis_path"),
            entry.get("caption_srt_path"),
            os.path.join(self.args.output, "captioned_videos", f"{base_name}_captioned.mp4"),
            os.path.join(self.args.output, "viral_clip_timestamps", f"{base_name}_timestamps.json"),
        ]
        # Also remove generated clips
        clips_dir = os.path.join(self.args.output, "viral_clips")
        if os.path.exists(clips_dir):
            for f in os.listdir(clips_dir):
                if f.startswith(base_name):
                    potential_paths.append(os.path.join(clips_dir, f))

        for path in potential_paths:
            if pd.notna(path) and os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"[SUCCESS] Deleted file: {path}")
                except OSError as e:
                    print(f"[ERROR] Could not delete file {path}: {e}")

        self.manifest_df = self.manifest_df[
            self.manifest_df["youtube_url"] != canonical_url
        ].reset_index(drop=True)
        save_manifest(self.manifest_df, self.manifest_path)
        print(f"[SUCCESS] Removed entry for {canonical_url} from manifest.")


# --- CLI Entry Points ---
def process_youtube_url(args):
    orchestrator = Orchestrator(args)
    orchestrator.process_url(args.url)

def handle_list_manifest(args):
    orchestrator = Orchestrator(args)
    orchestrator.list_manifest()

def handle_remove_url(args):
    orchestrator = Orchestrator(args)
    orchestrator.remove_url(args.url)