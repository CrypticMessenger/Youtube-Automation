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
            stdout=subprocess.DEVNULL, # Suppress ffmpeg output to keep console clean
            stderr=subprocess.DEVNULL, # Suppress ffmpeg errors, handled by check=True
            check=True, # Raise CalledProcessError on non-zero exit status
        )
        # Clean up temporary input file if it was a temporary audio stream download
        if (
            "_audiotemp." in os.path.basename(input_path) # Check if it's a temp file
            and os.path.exists(input_path)
            and input_path != output_mp3_path # Ensure we don't delete the output if it's same as input (e.g. re-encoding an mp3)
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
    except Exception as e: # Catch other potential errors during conversion
        print(
            f"[ERROR] ffmpeg conversion failed: {e} for {input_path} to {output_mp3_path}"
        )

    # Attempt to remove temporary input file even on conversion error, if it exists and is a temp file
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
