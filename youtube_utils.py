import os
import yt_dlp
import pandas as pd

from processors.base import Colors

def get_sanitized_base_name(yt_title, custom_filename=None):
    if custom_filename:
        return "".join(
            c if c.isalnum() or c in " ._-" else "_" for c in custom_filename
        )
    return "".join(c if c.isalnum() or c in " ._-" else "_" for c in yt_title)

def get_video_info(url):
    """Gets video info using yt-dlp."""
    ydl_opts = {'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Could not fetch YouTube video details for {url}: {e}")
        return None

def download_video(video_info, base_name_for_paths, effective_video_dir, video_quality_arg):
    """Downloads the video stream using yt-dlp."""
    video_url = video_info['webpage_url']
    video_filename = f"{base_name_for_paths}.mp4"
    output_path = os.path.join(effective_video_dir, video_filename)
    
    format_selector = video_quality_arg

    ydl_opts = {
        'format': format_selector,
        'outtmpl': output_path,
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        print(f"{Colors.SUCCESS}[SUCCESS]{Colors.RESET} Video downloaded: {os.path.abspath(output_path)}")
        return os.path.abspath(output_path)
    except Exception as e:
        print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Video download failed for {base_name_for_paths}: {e}")
        return None

def download_audio_stream(video_info, base_name_for_paths, effective_audio_dir, audio_quality_arg):
    """Downloads a dedicated audio stream using yt-dlp."""
    video_url = video_info['webpage_url']
    temp_audio_filename = f"{base_name_for_paths}_audiotemp.m4a"
    output_path = os.path.join(effective_audio_dir, temp_audio_filename)

    ydl_opts = {
        'format': audio_quality_arg,
        'outtmpl': output_path,
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        print(f"{Colors.SUCCESS}[SUCCESS]{Colors.RESET} Raw audio stream downloaded: {os.path.abspath(output_path)}")
        return os.path.abspath(output_path)
    except Exception as e:
        print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Raw audio stream download failed for {base_name_for_paths}: {e}")
        return None

def get_yt_object_and_canonical_url(input_url):
    """Creates a YouTube object and returns it along with the canonical URL."""
    info = get_video_info(input_url)
    if info:
        return info, info.get('webpage_url')
    return None, None


def get_video_duration(video_path):
    """
    Get the duration of a video file in seconds.
    This function is not currently used in the main workflow but is available for future use.
    """
    import ffmpeg
    try:
        probe = ffmpeg.probe(video_path)
        video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        return float(video_info['duration'])
    except (ffmpeg.Error, StopIteration) as e:
        print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Error getting duration for {video_path}: {e}")
        return None