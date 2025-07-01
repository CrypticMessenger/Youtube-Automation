# For local execution, you would first need to install these packages:
# pip install yt-dlp google-generativeai pandas

import os # For os.environ.get in main()

# Local application imports
from orchestrator import (
    process_youtube_url,
    handle_remove_url,
    handle_list_manifest,
)
from cli import parse_arguments
from processors.base import Colors


def main():
    args = parse_arguments()

    # Check for GOOGLE_API_KEY if viral analysis or timestamps are requested.
    if (hasattr(args, "viral_short_identifier") and args.viral_short_identifier) or \
       (hasattr(args, "get_viral_timestamps") and args.get_viral_timestamps):
        if not os.environ.get("GOOGLE_API_KEY"):
            print(
                f"{Colors.ERROR}[ERROR]{Colors.RESET} GOOGLE_API_KEY environment variable is not set. Required for viral clip analysis."
            )
            # You might want to exit here if the key is absolutely critical
            # import sys
            # sys.exit(1)

    if args.command_name == "process":
        process_youtube_url(args)
    elif args.command_name == "manage":
        if args.manage_action == "remove":
            handle_remove_url(args)
        elif args.manage_action == "list":
            handle_list_manifest(args)


if __name__ == "__main__":
    main()
