import os
import subprocess
import stable_whisper


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
    except Exception as e:  # Catch other potential errors during conversion
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


def generate_caption_files(audio_path, output_dir, base_filename, model_name="tiny"):
    """Generates caption files (.srt, .ass) using stable-whisper."""
    if not os.path.exists(audio_path):
        print(f"[ERROR] Audio file not found for caption generation: {audio_path}")
        return None

    print(
        f"[INFO] Generating captions for {audio_path} using stable-whisper model '{model_name}'..."
    )
    try:
        model = stable_whisper.load_model(model_name)
        os.makedirs(output_dir, exist_ok=True)

        result = model.transcribe(audio_path, fp16=False)

        srt_path = os.path.join(output_dir, f"{base_filename}.srt")
        ass_path = os.path.join(output_dir, f"{base_filename}.ass")

        result.to_srt_vtt(srt_path)
        result.to_ass(ass_path)

        if os.path.exists(srt_path) and os.path.exists(ass_path):
            print(f"[SUCCESS] Captions generated: {srt_path}, {ass_path}")
            return {"srt": srt_path, "ass": ass_path}
        else:
            print(
                f"[ERROR] stable-whisper did not generate expected caption files for {base_filename}."
            )
            return None

    except Exception as e:
        print(f"[ERROR] stable-whisper caption generation failed for {audio_path}: {e}")
        import traceback

        traceback.print_exc()
        return None


def transcribe_audio_stable_ts(audio_path, output_dir, base_filename, model_name="tiny"):
    """Transcribes audio to a .txt file using stable-whisper."""
    if not os.path.exists(audio_path):
        print(f"[ERROR] Audio file not found for transcription: {audio_path}")
        return None

    print(
        f"[INFO] Transcribing {audio_path} using stable-whisper model '{model_name}'..."
    )
    try:
        model = stable_whisper.load_model(model_name)
        os.makedirs(output_dir, exist_ok=True)

        result = model.transcribe(audio_path, fp16=False)

        txt_path = os.path.join(output_dir, f"{base_filename}.txt")
        result.to_txt(txt_path)

        if os.path.exists(txt_path):
            print(f"[SUCCESS] Transcript generated: {txt_path}")
            return txt_path
        else:
            print(
                f"[ERROR] stable-whisper did not generate expected transcript file for {base_filename}."
            )
            return None

    except Exception as e:
        print(f"[ERROR] stable-whisper transcription failed for {audio_path}: {e}")
        import traceback

        traceback.print_exc()
        return None
