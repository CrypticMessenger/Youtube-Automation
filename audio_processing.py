import os
import subprocess

def convert_to_mp3(input_path, output_mp3_path):
    """Converts input to MP3. Returns output_mp3_path on success, None on failure."""
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                input_path,
                "-vn",
                "-ar",
                "44100",
                "-ac",
                "2",
                "-b:a",
                "192k",
                output_mp3_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        if (
            "_audiotemp." in os.path.basename(input_path)
            and os.path.exists(input_path)
            and input_path != output_mp3_path # Don't remove if input was already the target mp3
        ):
            try:
                os.remove(input_path)
            except OSError as oe:
                print(
                    f"[WARNING] Could not remove temporary audio file {input_path}: {oe}"
                )
        print(f"[SUCCESS] Audio converted to MP3: {output_mp3_path}")
        return output_mp3_path
    except subprocess.CalledProcessError as e:
        print(
            f"[ERROR] ffmpeg conversion failed (return code {e.returncode}): {' '.join(e.cmd)}"
        )
    except Exception as e:
        print(
            f"[ERROR] ffmpeg conversion failed: {e} for {input_path} to {output_mp3_path}"
        )
    # Attempt to remove temp file even on error, if it exists and is a temp file
    if (
        "_audiotemp." in os.path.basename(input_path)
        and os.path.exists(input_path)
        and input_path != output_mp3_path
    ):
        try:
            os.remove(input_path)
        except OSError as oe:
            print(
                f"[WARNING] Could not remove temporary file {input_path} on error: {oe}"
            )
    return None
