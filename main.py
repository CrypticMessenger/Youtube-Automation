# For local execution, you would first need to install these packages:
# pip install yt-dlp google-generativeai pandas

import os # For os.environ.get in main()

# Standard library imports
import os

# Local application imports
from orchestrator import (
    process_youtube_url,
    handle_remove_url,
    handle_list_manifest,
    handle_generate_video,
)
from cli import parse_arguments
from manifest import load_manifest # save_manifest is now handled by orchestrator/handlers


def main():
    args = parse_arguments()

    # Check for GOOGLE_API_KEY if transcription or analysis is requested.
    # The os module is imported at the top of the file.
    if (hasattr(args, "viral_short_identifier") and args.viral_short_identifier) or (hasattr(args, "get_viral_timestamps") and args.get_viral_timestamps):
        if not os.environ.get("GOOGLE_API_KEY"):
            print(
                "[ERROR] GOOGLE_API_KEY environment variable is not set. Required for viral clip analysis."
            )
            # Exiting here could be an option if the key is absolutely critical.
            # import sys
            # sys.exit(1)

    manifest_df = load_manifest(args.manifest_file)
    # Initial manifest dtype printing was removed as it was too verbose.

    if args.command_name == "process":
        # Directory setup (effective_audio_dir etc.) is handled within parse_arguments in cli.py
        manifest_df = process_youtube_url(args, manifest_df, args.manifest_file)
        # Manifest saving is handled within process_youtube_url for each logical step.
        # No final save is needed here.

    elif args.command_name == "manage":
        if args.manage_action == "remove":
            manifest_df = handle_remove_url(args.url, manifest_df, args.manifest_file)
            # handle_remove_url in orchestrator saves the manifest.
        elif args.manage_action == "list":
            handle_list_manifest(manifest_df)
            # list command does not modify the manifest, so no save operation.

    elif args.command_name == "generate":
        handle_generate_video(args, manifest_df)

        # Other manage actions might require saving, but should be handled by their respective functions.


if __name__ == "__main__":
    # argparse is used by cli.py, but main.py also uses hasattr on args,
    # and the GOOGLE_API_KEY check uses os.environ.
    # No specific imports like 'sys' are needed here unless sys.exit is activated above.
    main()
