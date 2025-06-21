import os
from pytubefix import YouTube
import pandas as pd # Required for pd.NA

def get_sanitized_base_name(yt_title, custom_filename=None):
    if custom_filename:
        return "".join(
            c if c.isalnum() or c in " ._-" else "_" for c in custom_filename
        )
    return "".join(c if c.isalnum() or c in " ._-" else "_" for c in yt_title)

def download_video(yt, base_name_for_paths, effective_video_dir, resolution_arg):
    """Downloads the video stream."""
    target_stream = None
    if resolution_arg == "highest":
        target_stream = yt.streams.get_highest_resolution()
    else:
        target_stream = yt.streams.filter(
            res=resolution_arg,
            progressive=True,
            file_extension="mp4",
        ).first()
    if not target_stream:
        print(
            f"[INFO] No stream for res '{resolution_arg}' (progressive, mp4). Trying any progressive mp4."
        )
        target_stream = (
            yt.streams.filter(progressive=True, file_extension="mp4")
            .order_by("resolution")
            .desc()
            .first()
        )
    if not target_stream:
        print(
            f"[INFO] No progressive mp4 stream. Trying highest resolution adaptive mp4 video stream."
        )
        target_stream = (
            yt.streams.filter(
                adaptive=True, file_extension="mp4", only_video=True
            )
            .order_by("resolution")
            .desc()
            .first()
        )

    if target_stream:
        file_extension = target_stream.subtype
        if not file_extension:
            if target_stream.mime_type and "/" in target_stream.mime_type:
                file_extension = target_stream.mime_type.split("/")[-1]
            else:
                file_extension = "mp4" # Default fallback
        video_filename = f"{base_name_for_paths}.{file_extension}"
        os.makedirs(effective_video_dir, exist_ok=True)
        try:
            downloaded_path = target_stream.download(
                output_path=effective_video_dir, filename=video_filename
            )
            print(f"[SUCCESS] Video downloaded: {downloaded_path}")
            return os.path.abspath(downloaded_path)
        except Exception as e:
            print(f"[ERROR] Video download failed for {base_name_for_paths}: {e}")
            return None
    else:
        print(
            f"[ERROR] No suitable video stream found for {base_name_for_paths}. Skipping video download."
        )
        return None

def download_audio_stream(yt, base_name_for_paths, effective_audio_dir):
    """Downloads a dedicated audio stream, typically for later conversion."""
    audio_stream = yt.streams.get_audio_only()
    if not audio_stream:
        audio_stream = (
            yt.streams.filter(only_audio=True)
            .order_by("abr") # Average Bit Rate
            .desc()
            .first()
        )
    if audio_stream:
        temp_audio_filename = f"{base_name_for_paths}_audiotemp.{audio_stream.subtype or 'mp4'}"
        os.makedirs(effective_audio_dir, exist_ok=True)
        try:
            raw_audio_input_path = audio_stream.download(
                output_path=effective_audio_dir,
                filename=temp_audio_filename,
            )
            print(f"[SUCCESS] Raw audio stream downloaded: {raw_audio_input_path}")
            return os.path.abspath(raw_audio_input_path)
        except Exception as e:
            print(f"[ERROR] Raw audio stream download failed for {base_name_for_paths}: {e}")
            return None
    else:
        print("[ERROR] No dedicated audio stream found.")
        return None

def get_yt_object_and_canonical_url(input_url):
    """Creates a YouTube object and returns it along with the canonical URL."""
    try:
        yt = YouTube(input_url)
        canonical_url = yt.watch_url
        return yt, canonical_url
    except Exception as e:
        print(f"[ERROR] Could not fetch YouTube video details for {input_url}: {e}")
        return None, None
