import os
import subprocess
import whisper

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

def generate_caption_files(audio_path, output_dir, base_filename, model_name="small"):
    """Generates caption files (.srt, .vtt, etc.) using OpenAI's Whisper model."""
    if not os.path.exists(audio_path):
        print(f"[ERROR] Audio file not found for caption generation: {audio_path}")
        return None

    print(f"[INFO] Generating captions for {audio_path} using Whisper model '{model_name}'...")
    try:
        model = whisper.load_model(model_name)
        # Whisper saves files directly to the output_dir
        # It creates files like base_filename.srt, base_filename.vtt, etc.
        # We need to ensure the output directory exists and then run the transcribe method.
        os.makedirs(output_dir, exist_ok=True)

        # The transcribe method returns a result object, but also saves files to output_dir
        # We need to pass the output_dir to the transcribe method.
        # The output_dir parameter in whisper.transcribe is for the directory where the files will be saved.
        # The filename for the output files will be derived from the input audio_path by default.
        # To control the output filename, we might need to move/rename after generation or use a different approach.
        # For now, let's assume whisper uses the input filename as base for output.
        # We'll need to ensure the output files are named correctly based on base_filename.

        # Whisper's CLI uses the input filename as the base for output files.
        # To match our base_filename convention, we'll temporarily link/copy the audio
        # to a name that whisper will use, then delete the temp link/copy.
        temp_audio_path = os.path.join(output_dir, f"{base_filename}.mp3")
        import shutil
        shutil.copy(audio_path, temp_audio_path)

        # Run transcription
        current_dir = os.getcwd()
        os.chdir(output_dir)
        model.transcribe(os.path.basename(temp_audio_path), fp16=False)
        os.chdir(current_dir)

        # Clean up the temporary audio file
        os.remove(temp_audio_path)

        # Construct paths to expected output files
        srt_path = os.path.join(output_dir, f"{base_filename}.srt")
        vtt_path = os.path.join(output_dir, f"{base_filename}.vtt")
        txt_path = os.path.join(output_dir, f"{base_filename}.txt") # Whisper also generates a .txt

        # Check if files were created
        if os.path.exists(srt_path) and os.path.exists(vtt_path):
            print(f"[SUCCESS] Captions generated: {srt_path}, {vtt_path}, {txt_path}")
            return {"srt": srt_path, "vtt": vtt_path, "txt": txt_path}
        else:
            print(f"[ERROR] Whisper did not generate expected caption files for {base_filename}.")
            return None

    except Exception as e:
        print(f"[ERROR] Whisper caption generation failed for {audio_path}: {e}")
        import traceback
        traceback.print_exc()
        return None
