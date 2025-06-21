import argparse
import os
from manifest import DEFAULT_MANIFEST_FILE # For default manifest file path

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="🎥 YouTube Downloader & Analyzer with Caching",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--manifest-file",
        default=DEFAULT_MANIFEST_FILE,
        help=f"Path to the processing manifest CSV file (default: {DEFAULT_MANIFEST_FILE})",
    )

    subparsers = parser.add_subparsers(
        title="commands", dest="command_name", help="Action to perform", required=True
    )

    # --- Process Command ---
    process_parser = subparsers.add_parser(
        "process", help="Download and process a YouTube video"
    )
    process_parser.add_argument("url", help="YouTube video URL")
    process_parser.add_argument(
        "-o",
        "--output",
        default=".",
        help="Base output directory (default: current directory)",
    )
    process_parser.add_argument(
        "-f",
        "--filename",
        help="Custom base filename (no extension). Defaults to video title.",
    )
    process_parser.add_argument(
        "-r",
        "--resolution",
        default="highest",
        help="Video resolution (e.g., 720p, highest)",
    )
    process_parser.add_argument(
        "-a",
        "--audio",
        action="store_true",
        help="Download audio-only (MP3). No video download.",
    )
    process_parser.add_argument(
        "--audio-dir",
        default=None,
        help="Directory for audio files (default: [OUTPUT]/audios)",
    )
    process_parser.add_argument(
        "--video-dir",
        default=None,
        help="Directory for video files (default: [OUTPUT]/videos)",
    )
    process_parser.add_argument(
        "--transcript-dir",
        default=None,
        help="Directory for transcript files (default: [OUTPUT]/transcripts)",
    )
    process_parser.add_argument(
        "--analysis-dir",
        default=None,
        help="Directory for analysis files (default: [OUTPUT]/viral_analysis)",
    )
    process_parser.add_argument(
        "--transcribe",
        action="store_true",
        help="Transcribe audio and save .txt transcript.",
    )
    process_parser.add_argument(
        "--gemini-model",
        default="gemini-1.5-flash-latest",
        help="Gemini model for transcription.",
    )
    process_parser.add_argument(
        "--viral-short-identifier",
        action="store_true",
        help="Identify viral short clips from transcript.",
    )
    process_parser.add_argument(
        "--number-of-sections",
        type=int,
        default=None,
        help="Number of viral sections for AI to find.",
    )
    process_parser.add_argument(
        "--clip-identifier-model",
        default="gemini-1.5-pro-latest",
        help="Gemini model for clip identification.",
    )
    process_parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-processing, ignoring cached files/statuses.",
    )

    # --- Manage Command ---
    manage_parser = subparsers.add_parser(
        "manage", help="Manage the processing manifest"
    )
    manage_subparsers = manage_parser.add_subparsers(
        title="manage_actions",
        dest="manage_action",
        help="Manifest management action",
        required=True,
    )
    remove_parser = manage_subparsers.add_parser(
        "remove", help="Remove a URL and its files from manifest"
    )
    remove_parser.add_argument("url", help="YouTube URL to remove")
    list_parser = manage_subparsers.add_parser( # noqa: F841 -- assigned but not used directly, but needed for argparser
        "list", help="List all entries in the manifest"
    )
    # list_parser takes no arguments other than the global --manifest-file

    args = parser.parse_args()

    # Set up effective directory paths for process command
    if args.command_name == "process":
        base_out = os.path.abspath(args.output)
        args.effective_audio_dir = (
            os.path.abspath(args.audio_dir)
            if args.audio_dir
            else os.path.join(base_out, "audios")
        )
        args.effective_video_dir = (
            os.path.abspath(args.video_dir)
            if args.video_dir
            else os.path.join(base_out, "videos")
        )
        args.effective_transcript_dir = (
            os.path.abspath(args.transcript_dir)
            if args.transcript_dir
            else os.path.join(base_out, "transcripts")
        )
        args.effective_analysis_dir = (
            os.path.abspath(args.analysis_dir)
            if args.analysis_dir
            else os.path.join(base_out, "viral_analysis")
        )

    return args
