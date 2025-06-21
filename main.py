# For local execution, you would first need to install these packages:
# pip install pytubefix google-generativeai

import argparse
import os
import subprocess
import sys
from pytubefix import YouTube
import google.generativeai as genai


def get_viral_clip_identifier_prompt(transcript_text, number_of_sections=None):
    """
    Generates a prompt for Gemini to identify viral short clips from a YouTube transcript.
    """
    prompt = f"""
Analyze the following YouTube video transcript to identify sections with high potential to become viral short clips (e.g., for YouTube Shorts, TikTok, Instagram Reels).

For each identified section, please provide:
1. The start and end timestamps (if inferable from context, otherwise approximate segment). If timestamps are not present in the transcript, focus on logical segments.
2. The verbatim text of the section.
3. A brief justification for why this section is likely to be engaging or go viral (e.g., humor, strong emotion, surprising information, actionable advice, controversial statement, relatable moment, concise key takeaway).

Consider the following factors for virality:
- Conciseness: Shorts are typically under 60 seconds.
- Strong Hook: Does it grab attention immediately?
- Emotional Impact: Joy, surprise, curiosity, awe, etc.
- Value: Entertainment, information, inspiration.
- Shareability: Is it something people would want to share?
- Clarity: Is the message clear and easy to understand quickly?

{'Please identify the top ' + str(number_of_sections) + ' most promising sections.' if number_of_sections else 'Identify all promising sections.'}

Here is the transcript:
---
{transcript_text}
---

Provide your analysis in a clear, structured format. For example:

Potential Clip 1:
Timestamp: [Start Time] - [End Time] (if available/inferable)
Text: "..."
Justification: "..."

Potential Clip 2:
Timestamp: [Start Time] - [End Time] (if available/inferable)
Text: "..."
Justification: "..."
"""
    return prompt.strip()


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
    audio_file_path,
    transcript_output_dir,
    base_filename,
    model_name,
    save_transcript_file=True,
):
    """
    Transcribes the given audio file using Gemini API.
    Optionally saves it to a .txt file and returns the transcript text.
    """
    if not os.path.exists(audio_file_path):
        print(f"[ERROR] Audio file for transcription not found: {audio_file_path}")
        return None
    if os.path.getsize(audio_file_path) == 0:
        print(f"[ERROR] Audio file for transcription is empty: {audio_file_path}")
        return None

    print(
        f"[INFO] Starting transcription for {audio_file_path} (size: {os.path.getsize(audio_file_path)} bytes) using model {model_name}..."
    )
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("[ERROR] GOOGLE_API_KEY environment variable not set. Cannot transcribe.")
        return None

    uploaded_audio_file_details = None
    transcript_text_to_return = ""

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

        transcript_text_to_return = transcript_text

        if save_transcript_file:
            os.makedirs(transcript_output_dir, exist_ok=True)
            transcript_file_name = f"{base_filename}_transcript.txt"
            transcript_file_path = os.path.join(
                transcript_output_dir, transcript_file_name
            )

            with open(transcript_file_path, "w", encoding="utf-8") as f:
                f.write(transcript_text)

            if transcript_text.strip():
                print(f"[SUCCESS] Transcript saved to: {transcript_file_path}")
            else:
                print(
                    f"[WARNING] Empty transcript saved to: {transcript_file_path}. Check Gemini response if this is unexpected."
                )
        elif transcript_text_to_return.strip():
            print(
                f"[INFO] Transcription successful (text obtained, not saved to file)."
            )
        else:
            print(f"[WARNING] Transcription result is empty (not saved to file).")

        return transcript_text_to_return

    except Exception as e:
        print(f"[ERROR] Gemini API transcription process failed: {e}")
        import traceback

        traceback.print_exc()
        return None
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


def identify_viral_clips_gemini(
    transcript_text,
    number_of_sections,
    model_name,
    analysis_output_dir,  # Changed from output_dir
    base_filename,
):
    """Identifies viral clips from transcript using Gemini and saves the analysis."""
    if not transcript_text or not transcript_text.strip():
        print("[ERROR] Transcript text is empty. Cannot identify viral clips.")
        return

    print(f"[INFO] Identifying viral clips using model {model_name}...")
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print(
            "[ERROR] GOOGLE_API_KEY environment variable not set. Cannot identify viral clips."
        )
        return

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name=model_name)

        prompt_for_gemini = get_viral_clip_identifier_prompt(
            transcript_text=transcript_text, number_of_sections=number_of_sections
        )

        print(
            "[INFO] Sending transcript and prompt to Gemini for viral clip identification..."
        )
        response = model.generate_content(
            [prompt_for_gemini],
            request_options={"timeout": 900},
        )

        analysis_text = ""
        if hasattr(response, "text") and response.text:
            analysis_text = response.text
        elif hasattr(response, "parts") and response.parts:
            for part in response.parts:
                if hasattr(part, "text") and part.text:
                    analysis_text += part.text + "\n"
            analysis_text = analysis_text.strip()

        if not analysis_text.strip():
            print(
                "[WARNING] Viral clip analysis result is empty or could not be extracted directly."
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
                    analysis_text = response.candidates[0].content.parts[0].text
                    if analysis_text.strip():
                        print(
                            "[INFO] Successfully extracted analysis using response.candidates."
                        )
                    else:
                        print(
                            "[WARNING] Analysis from response.candidates is also empty."
                        )
                else:
                    print(
                        f"[INFO] No analysis text found in candidates or response. Full response for diagnostics: {response}"
                    )
            except Exception as e_parse:
                print(
                    f"[ERROR] Error parsing Gemini response candidates for viral clips: {e_parse}"
                )
                print(f"Full response object for diagnostics: {response}")

        os.makedirs(analysis_output_dir, exist_ok=True)  # Use analysis_output_dir
        analysis_file_name = f"{base_filename}_viral_clips_analysis.txt"
        analysis_file_path = os.path.join(
            analysis_output_dir, analysis_file_name
        )  # Use analysis_output_dir

        with open(analysis_file_path, "w", encoding="utf-8") as f:
            f.write(analysis_text)

        if analysis_text.strip():
            print(f"[SUCCESS] Viral clip analysis saved to: {analysis_file_path}")
        else:
            print(
                f"[WARNING] Empty viral clip analysis saved to: {analysis_file_path}. Check Gemini response if this is unexpected."
            )

    except Exception as e:
        print(f"[ERROR] Gemini API viral clip identification process failed: {e}")
        import traceback

        traceback.print_exc()


def download_video(
    url,
    audio_output_dir,
    video_output_dir,
    transcript_output_dir,
    analysis_output_dir,  # New parameter
    filename_base_arg,
    resolution,
    audio_only,
    transcribe_flag,
    gemini_model,
    viral_short_identifier_flag,
    number_of_sections,
    clip_identifier_model,
):
    mp3_file_for_transcription = None
    transcript_content = None

    try:
        yt = YouTube(url)
        sanitized_title = "".join(
            c if c.isalnum() or c in " ._-" else "_" for c in yt.title
        )
        base_name = filename_base_arg or sanitized_title

        needs_audio_processing = (
            audio_only or transcribe_flag or viral_short_identifier_flag
        )

        if needs_audio_processing:
            print(
                "[INFO] Downloading audio stream (required for MP3, transcription, or viral clip ID)..."
            )
            stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()
            if not stream:
                print(
                    "[ERROR] No audio stream found. Cannot proceed with audio-dependent tasks."
                )
                if audio_only:
                    sys.exit(1)
            else:
                raw_audio_temp_filename = (
                    f"{base_name}_audiotemp.{stream.subtype or 'mp4'}"
                )
                raw_file_path = stream.download(
                    output_path=audio_output_dir, filename=raw_audio_temp_filename
                )
                print(f"[SUCCESS] Raw audio downloaded: {raw_file_path}")

                final_mp3_path = os.path.join(audio_output_dir, base_name + ".mp3")
                if convert_to_mp3(raw_file_path, final_mp3_path):
                    mp3_file_for_transcription = final_mp3_path
                    if audio_only:
                        print(f"[INFO] MP3 audio ready: {final_mp3_path}")
                else:
                    print(
                        f"[ERROR] MP3 conversion failed. Cannot proceed with transcription or viral clip ID."
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
                if (
                    not needs_audio_processing
                ):  # Check if audio processing was also skipped
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

        if (
            transcribe_flag or viral_short_identifier_flag
        ) and mp3_file_for_transcription:
            print("[INFO] Proceeding with audio transcription...")
            should_save_transcript_file = transcribe_flag
            transcript_content = transcribe_audio_gemini(
                mp3_file_for_transcription,
                transcript_output_dir,  # This is for saving the .txt transcript
                base_name,
                gemini_model,
                save_transcript_file=should_save_transcript_file,
            )
            if not transcript_content:
                print(
                    "[WARNING] Transcription failed or returned empty content. Viral clip identification might not be possible or effective."
                )
        elif (
            transcribe_flag or viral_short_identifier_flag
        ) and not mp3_file_for_transcription:
            print(
                "[WARNING] Transcription or Viral Clip ID was requested, but MP3 file could not be generated/found. Skipping these steps."
            )

        if viral_short_identifier_flag and transcript_content:
            identify_viral_clips_gemini(
                transcript_text=transcript_content,
                number_of_sections=number_of_sections,
                model_name=clip_identifier_model,
                analysis_output_dir=analysis_output_dir,  # Pass the dedicated analysis dir
                base_filename=base_name,
            )
        elif viral_short_identifier_flag and not transcript_content:
            print(
                "[WARNING] Viral clip identification was requested, but transcript is not available. Skipping this step."
            )

    except Exception as e:
        print(f"[ERROR] An error occurred during download or processing: {e}")
        import traceback

        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description="🎥 YouTube Downloader CLI (video/audio/mp3) with Transcription & Viral Clip ID"
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "-o",
        "--output",
        default=".",
        help="Base output directory. Default: current directory.",
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
        default=None,
        help="Specific directory for audio files. If not set, uses '[OUTPUT_DIR]/audios'.",
    )
    parser.add_argument(
        "--video-dir",
        default=None,
        help="Specific directory for video files. If not set, uses '[OUTPUT_DIR]/videos'.",
    )
    parser.add_argument(
        "--transcript-dir",
        default=None,
        help="Specific directory for transcript files. If not set, uses '[OUTPUT_DIR]/transcripts'.",
    )
    parser.add_argument(  # New argument for analysis directory
        "--analysis-dir",
        default=None,
        help="Specific directory for viral clip analysis files. If not set, uses '[OUTPUT_DIR]/viral_analysis'.",
    )

    parser.add_argument(
        "--transcribe",
        action="store_true",
        help="Transcribe the audio using Gemini API and save to a .txt file. Generates an MP3 if one isn't already being created by -a or --viral-short-identifier.",
    )
    parser.add_argument(
        "--gemini-model",
        default="gemini-1.5-pro",
        help="Gemini model to use for transcription (e.g., gemini-1.5-flash-latest, gemini-1.5-pro-latest).",
    )

    parser.add_argument(
        "--viral-short-identifier",
        action="store_true",
        help="Identify potential viral short clips from the transcript using a specified Gemini model. Forces audio download and transcription if not already enabled.",
    )
    parser.add_argument(
        "--number-of-sections",
        type=int,
        default=None,
        help="Optimal number of viral sections to identify (used with --viral-short-identifier). Default: AI decides or identifies all promising sections.",
    )
    parser.add_argument(
        "--clip-identifier-model",
        default="gemini-1.5-pro",
        help="Gemini model to use for viral clip identification (e.g., gemini-1.5-pro-latest, models/gemini-1.5-pro-latest).",
    )

    args = parser.parse_args()

    base_output_dir = args.output

    effective_audio_dir = (
        args.audio_dir
        if args.audio_dir is not None
        else os.path.join(base_output_dir, "audios")
    )
    effective_video_dir = (
        args.video_dir
        if args.video_dir is not None
        else os.path.join(base_output_dir, "videos")
    )
    effective_transcript_dir = (
        args.transcript_dir
        if args.transcript_dir is not None
        else os.path.join(base_output_dir, "transcripts")
    )
    effective_analysis_dir = (
        args.analysis_dir
        if args.analysis_dir is not None
        else os.path.join(base_output_dir, "viral_analysis")
    )

    if args.audio or args.transcribe or args.viral_short_identifier:
        os.makedirs(effective_audio_dir, exist_ok=True)
    if not args.audio:
        os.makedirs(effective_video_dir, exist_ok=True)
    if args.transcribe:  # Only create transcript_dir if --transcribe is explicitly set
        os.makedirs(effective_transcript_dir, exist_ok=True)
    if (
        args.viral_short_identifier
    ):  # Create analysis_dir if --viral-short-identifier is set
        os.makedirs(effective_analysis_dir, exist_ok=True)
        # Also ensure transcript dir is created if viral ID is on, as transcription happens internally
        # but the user might not have set --transcribe explicitly.
        # However, transcribe_audio_gemini will create it if save_transcript_file is True.
        # Let's ensure it's created if a transcript will be saved due to --transcribe,
        # or if it's needed for viral ID (even if not saved, just to be safe with paths).
        if (
            not args.transcribe
        ):  # If only doing viral ID, transcript might not be saved, but we get content.
            # No need to create transcript dir if transcript not saved.
            pass  # The transcript_output_dir is passed to transcribe_audio_gemini,
            # which will create it if save_transcript_file is True.
            # If save_transcript_file is False (only viral ID, no --transcribe),
            # then transcript_output_dir is not strictly needed for saving a file there.

    download_video(
        url=args.url,
        audio_output_dir=effective_audio_dir,
        video_output_dir=effective_video_dir,
        transcript_output_dir=effective_transcript_dir,  # For saving .txt transcript
        analysis_output_dir=effective_analysis_dir,  # For saving analysis file
        filename_base_arg=args.filename,
        resolution=args.resolution,
        audio_only=args.audio,
        transcribe_flag=args.transcribe,
        gemini_model=args.gemini_model,
        viral_short_identifier_flag=args.viral_short_identifier,
        number_of_sections=args.number_of_sections,
        clip_identifier_model=args.clip_identifier_model,
    )


if __name__ == "__main__":
    main()
