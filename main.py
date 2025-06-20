# For local execution, you would first need to install these packages:
# pip install pytubefix google-generativeai

import argparse
import os
import subprocess
import sys
from pytubefix import YouTube
import google.generativeai as genai


def convert_to_mp3(input_path, output_mp3_path):
    """Converts the input audio file to MP3 using ffmpeg and returns success status."""
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
        if os.path.exists(input_path) and input_path != output_mp3_path:
            os.remove(input_path)
        print(f"[SUCCESS] Audio converted to MP3: {output_mp3_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(
            f"[ERROR] ffmpeg conversion failed. Return code: {e.returncode} for command: {' '.join(e.cmd)}"
        )
        if os.path.exists(input_path) and input_path != output_mp3_path:
            try:
                os.remove(input_path)
            except OSError as oe:
                print(f"[WARNING] Could not remove temporary file {input_path}: {oe}")
        return False
    except Exception as e:
        print(
            f"[ERROR] ffmpeg conversion failed: {e} for {input_path} to {output_mp3_path}"
        )
        if os.path.exists(input_path) and input_path != output_mp3_path:
            try:
                os.remove(input_path)
            except OSError as oe:
                print(f"[WARNING] Could not remove temporary file {input_path}: {oe}")
        return False


def transcribe_audio_gemini(
    audio_file_path, transcript_output_dir, base_filename, model_name
):
    """Transcribes the given audio file using Gemini API and saves it to a .txt file."""
    if not os.path.exists(audio_file_path):
        print(f"[ERROR] Audio file for transcription not found: {audio_file_path}")
        return
    if os.path.getsize(audio_file_path) == 0:
        print(f"[ERROR] Audio file for transcription is empty: {audio_file_path}")
        return

    print(
        f"[INFO] Starting transcription for {audio_file_path} (size: {os.path.getsize(audio_file_path)} bytes) using model {model_name}..."
    )
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("[ERROR] GOOGLE_API_KEY environment variable not set. Cannot transcribe.")
        return

    uploaded_audio_file_details = None
    try:
        genai.configure(api_key=api_key)

        print(f"[INFO] Uploading {audio_file_path} to Gemini API...")
        audio_file_obj = genai.upload_file(path=audio_file_path)
        uploaded_audio_file_details = audio_file_obj
        print(
            f"[SUCCESS] File uploaded: {audio_file_obj.name} (URI: {audio_file_obj.uri})"
        )

        model = genai.GenerativeModel(model_name=model_name)

        print("[INFO] Sending audio to Gemini for transcription...")
        response = model.generate_content(
            ["Please transcribe this audio.", audio_file_obj],
            request_options={"timeout": 600},
        )

        transcript_text = ""
        if hasattr(response, "text") and response.text:
            transcript_text = response.text
        elif hasattr(response, "parts") and response.parts:
            for part in response.parts:
                if hasattr(part, "text") and part.text:
                    transcript_text += part.text + "\n"
            transcript_text = transcript_text.strip()

        if not transcript_text.strip():
            print(
                "[WARNING] Transcription result is empty or could not be extracted directly."
            )
            try:
                if (
                    response.candidates
                    and len(response.candidates) > 0
                    and response.candidates[0].content
                    and len(response.candidates[0].content.parts) > 0
                    and hasattr(response.candidates[0].content.parts[0], "text")
                    and response.candidates[0].content.parts[0].text
                ):
                    transcript_text = response.candidates[0].content.parts[0].text
                    if transcript_text.strip():
                        print(
                            "[INFO] Successfully extracted text using response.candidates."
                        )
                    else:
                        print("[WARNING] Text from response.candidates is also empty.")
                else:
                    print(
                        f"[INFO] No transcript text found in candidates or response. Full response for diagnostics: {response}"
                    )
            except Exception as e_parse:
                print(f"[ERROR] Error parsing Gemini response candidates: {e_parse}")
                print(f"Full response object for diagnostics: {response}")

        os.makedirs(transcript_output_dir, exist_ok=True)
        transcript_file_name = f"{base_filename}_transcript.txt"
        transcript_file_path = os.path.join(transcript_output_dir, transcript_file_name)

        with open(transcript_file_path, "w", encoding="utf-8") as f:
            f.write(transcript_text)

        if transcript_text.strip():
            print(f"[SUCCESS] Transcript saved to: {transcript_file_path}")
        else:
            print(
                f"[WARNING] Empty transcript saved to: {transcript_file_path}. Check Gemini response if this is unexpected."
            )

    except Exception as e:
        print(f"[ERROR] Gemini API transcription process failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if uploaded_audio_file_details and hasattr(uploaded_audio_file_details, "name"):
            try:
                print(
                    f"[INFO] Deleting uploaded file {uploaded_audio_file_details.name} from Gemini API..."
                )
                genai.delete_file(uploaded_audio_file_details.name)
                print(
                    f"[SUCCESS] File {uploaded_audio_file_details.name} deleted from Gemini API."
                )
            except Exception as e_del:
                print(
                    f"[WARNING] Could not delete uploaded file {uploaded_audio_file_details.name} from Gemini API: {e_del}"
                )


def download_video(
    url,
    audio_output_dir,
    video_output_dir,
    transcript_output_dir,
    filename_base_arg,
    resolution,
    audio_only,
    transcribe,
    gemini_model,
):
    mp3_file_for_transcription = None
    try:
        yt = YouTube(url)
        sanitized_title = "".join(
            c if c.isalnum() or c in " ._-" else "_" for c in yt.title
        )
        base_name = filename_base_arg or sanitized_title

        if audio_only or transcribe:
            print("[INFO] Downloading audio stream...")
            stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()
            if not stream:
                print("[ERROR] No audio stream found.")
                if audio_only:
                    sys.exit(1)
                return

            raw_audio_temp_filename = f"{base_name}_audiotemp.{stream.subtype or 'mp4'}"
            raw_file_path = stream.download(
                output_path=audio_output_dir, filename=raw_audio_temp_filename
            )  # Download to audio_dir
            print(f"[SUCCESS] Raw audio downloaded: {raw_file_path}")

            final_mp3_path = os.path.join(audio_output_dir, base_name + ".mp3")
            if convert_to_mp3(raw_file_path, final_mp3_path):
                mp3_file_for_transcription = final_mp3_path
                if audio_only:
                    print(f"[INFO] MP3 audio ready: {final_mp3_path}")
            else:
                print(
                    f"[ERROR] MP3 conversion failed. Cannot proceed with transcription if it was requested."
                )
                if audio_only:
                    sys.exit(1)
                mp3_file_for_transcription = None

        if not audio_only:
            print(f"[INFO] Attempting to download video: {base_name}")
            target_stream = None
            if resolution == "highest":
                target_stream = yt.streams.get_highest_resolution()
            else:
                target_stream = yt.streams.filter(
                    res=resolution, progressive=True
                ).first()

            if not target_stream:
                print(
                    f"[WARNING] Video resolution {resolution} (progressive) not found. Trying any progressive MP4 stream..."
                )
                target_stream = (
                    yt.streams.filter(progressive=True, file_extension="mp4")
                    .order_by("resolution")
                    .desc()
                    .first()
                )

            if not target_stream:
                print(
                    f"[ERROR] No suitable video stream found for {base_name}. Skipping video download."
                )
                if not transcribe and not audio_only:
                    sys.exit(1)
            else:
                video_output_filename = base_name + ".mp4"
                video_full_path = os.path.join(video_output_dir, video_output_filename)
                print(
                    f"[INFO] Downloading video stream to {video_full_path}: Resolution: {target_stream.resolution}, FPS: {target_stream.fps}fps, Progressive: {target_stream.is_progressive}"
                )
                target_stream.download(
                    output_path=video_output_dir, filename=video_output_filename
                )
                print(f"[SUCCESS] Video downloaded: {video_full_path}")

        if transcribe and mp3_file_for_transcription:
            transcribe_audio_gemini(
                mp3_file_for_transcription,
                transcript_output_dir,
                base_name,
                gemini_model,
            )
        elif transcribe and not mp3_file_for_transcription:
            print(
                "[WARNING] Transcription was requested, but MP3 file could not be generated/found. Skipping transcription."
            )

    except Exception as e:
        print(f"[ERROR] An error occurred during download or processing: {e}")
        import traceback

        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description="🎥 YouTube Downloader CLI (video/audio/mp3) with Transcription"
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "-o",
        "--output",
        default=".",
        help="Base output directory. Specific content types will go into subfolders (audio, video, transcripts) unless overridden by specific --*_dir arguments (default: current directory)",
    )
    parser.add_argument(
        "-f",
        "--filename",
        help="Custom base filename (without extension). If not provided, video title is used.",
    )
    parser.add_argument(
        "-r",
        "--resolution",
        default="highest",
        help="Video resolution (e.g., 720p, 480p, highest)",
    )
    parser.add_argument(
        "-a",
        "--audio",
        action="store_true",
        help="Download audio-only and convert to mp3. Video will not be downloaded if this is set.",
    )

    parser.add_argument(
        "--audio-dir",
        default="./audios",
        help="Specific directory for audio files. Overrides default audio subfolder within --output.",
    )
    parser.add_argument(
        "--video-dir",
        default="./videos",
        help="Specific directory for video files. Overrides default video subfolder within --output.",
    )
    parser.add_argument(
        "--transcript-dir",
        default="./transcripts",
        help="Specific directory for transcript files. Overrides default transcripts subfolder within --output.",
    )

    parser.add_argument(
        "--transcribe",
        action="store_true",
        help="Transcribe the audio using Gemini API. Generates an MP3 if one isn't already being created by -a.",
    )
    parser.add_argument(
        "--gemini-model",
        default="gemini-2.5-flash",
        help="Gemini model to use for transcription (e.g., gemini-2.5-flash, gemini-2.5-pro)",
    )

    args = parser.parse_args()

    # Determine effective output directories
    effective_audio_dir = (
        args.audio_dir if args.audio_dir else os.path.join(args.output, "audio")
    )
    effective_video_dir = (
        args.video_dir if args.video_dir else os.path.join(args.output, "video")
    )
    effective_transcript_dir = (
        args.transcript_dir
        if args.transcript_dir
        else os.path.join(args.output, "transcripts")
    )

    # Create directories if they don't exist
    if args.audio or args.transcribe:
        os.makedirs(effective_audio_dir, exist_ok=True)
    if not args.audio:  # Video is downloaded if not audio_only
        os.makedirs(effective_video_dir, exist_ok=True)
    if args.transcribe:
        os.makedirs(effective_transcript_dir, exist_ok=True)

    download_video(
        url=args.url,
        audio_output_dir=effective_audio_dir,
        video_output_dir=effective_video_dir,
        transcript_output_dir=effective_transcript_dir,
        filename_base_arg=args.filename,
        resolution=args.resolution,
        audio_only=args.audio,
        transcribe=args.transcribe,
        gemini_model=args.gemini_model,
    )


if __name__ == "__main__":
    main()
