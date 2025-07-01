import subprocess
import os

from processors.base import Colors

def burn_subtitles(video_path, audio_path, ass_path, output_path):
    """Burns subtitles into a video using ffmpeg."""
    try:
        command = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex", f"[0:v]ass='{os.path.basename(ass_path)}'[v];[1:a]anull[a]",
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264",
            "-crf", "22",
            "-preset", "medium",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path
        ]
        # Change to the directory of the ass file to ensure ffmpeg can find it.
        subprocess.run(command, check=True, cwd=os.path.dirname(ass_path))
        print(f"{Colors.SUCCESS}[SUCCESS]{Colors.RESET} Subtitles burned into video: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"{Colors.ERROR}[ERROR]{Colors.RESET} ffmpeg subtitle burn failed: {e}")
        return None

def generate_video_with_captions(video_path, audio_path, ass_path, output_path):
    """Generates a video with hardcoded captions using ffmpeg."""
    try:
        command = [
            "ffmpeg",
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex", f"[0:v]ass={os.path.basename(ass_path)}[v];[1:a]anull[a]",
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264", "-crf", "22", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k",
            output_path
        ]
        subprocess.run(command, check=True, cwd=os.path.dirname(ass_path))
        print(f"{Colors.SUCCESS}[SUCCESS]{Colors.RESET} Generated video with captions: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"{Colors.ERROR}[ERROR]{Colors.RESET} ffmpeg video generation failed: {e}")
        return None