import os
import subprocess
import stable_whisper

from processors.base import Colors

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
            stdout=subprocess.DEVNULL,  # Suppress ffmpeg output to keep console clean
            stderr=subprocess.DEVNULL,  # Suppress ffmpeg errors, handled by check=True
            check=True,  # Raise CalledProcessError on non-zero exit status
        )
        # Clean up temporary input file if it was a temporary audio stream download
        if (
            "_audiotemp." in os.path.basename(input_path)  # Check if it's a temp file
            and os.path.exists(input_path)
            and input_path
            != output_mp3_path  # Ensure we don't delete the output if it's same as input (e.g. re-encoding an mp3)
        ):
            try:
                print(
                    f"{Colors.WARNING}[WARNING]{Colors.RESET} Could not remove temporary audio file {input_path}: {oe}"
                )
            except OSError as oe:
                print(
                    f"{Colors.WARNING}[WARNING]{Colors.RESET} Could not remove temporary audio file {input_path}: {oe}"
                )
        print(f"{Colors.SUCCESS}[SUCCESS]{Colors.RESET} Audio converted to MP3: {output_mp3_path}")
        return output_mp3_path
    except subprocess.CalledProcessError as e:
        print(
            f"{Colors.ERROR}[ERROR]{Colors.RESET} ffmpeg conversion failed (return code {e.returncode}): {' '.join(e.cmd)}"
        )
    except Exception as e:  # Catch other potential errors during conversion
        print(
            f"{Colors.ERROR}[ERROR]{Colors.RESET} ffmpeg conversion failed: {e} for {input_path} to {output_mp3_path}"
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
                f"{Colors.WARNING}[WARNING]{Colors.RESET} Could not remove temporary file {input_path} on error: {oe}"
            )
    return None


def generate_caption_files(audio_path, output_dir, base_filename, model_name="tiny", transcript_output_dir=None):
    """Generates caption files (.srt, .ass) and optionally a transcript (.txt) using stable-whisper."""
    if not os.path.exists(audio_path):
        print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Audio file not found for caption generation: {audio_path}")
        return None

    print(
        f"{Colors.INFO}[INFO]{Colors.RESET} Generating captions and transcript for {audio_path} using stable-whisper model '{model_name}'..."
    )
    try:
        model = stable_whisper.load_model(model_name)
        os.makedirs(output_dir, exist_ok=True)
        if transcript_output_dir:
            os.makedirs(transcript_output_dir, exist_ok=True)

        result = model.transcribe(audio_path, fp16=False)

        srt_path = os.path.join(output_dir, f"{base_filename}.srt")
        ass_path = os.path.join(output_dir, f"{base_filename}.ass")
        txt_path = os.path.join(transcript_output_dir, f"{base_filename}.txt") if transcript_output_dir else None

        result.to_srt_vtt(srt_path)
        result.to_ass(ass_path)
        if txt_path:
            result.to_txt(txt_path)

        generated_files = {}
        if os.path.exists(srt_path):
            generated_files["srt"] = srt_path
        if os.path.exists(ass_path):
            generated_files["ass"] = ass_path
        if txt_path and os.path.exists(txt_path):
            generated_files["txt"] = txt_path

        if generated_files:
            print(f"{Colors.SUCCESS}[SUCCESS]{Colors.RESET} Generated files: {', '.join(generated_files.values())}")
            return generated_files
        else:
            print(
                f"{Colors.ERROR}[ERROR]{Colors.RESET} stable-whisper did not generate any expected files for {base_filename}."
            )
            return None

    except Exception as e:
        print(f"{Colors.ERROR}[ERROR]{Colors.RESET} stable-whisper caption/transcript generation failed for {audio_path}: {e}")
        import traceback

        traceback.print_exc()
        return None
