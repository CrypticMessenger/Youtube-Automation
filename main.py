# For local execution, you would first need to install these packages:
# pip install pytubefix google-generativeai pandas

import os # For os.environ.get in main()

# Import orchestrator functions
from orchestrator import process_youtube_url, handle_remove_url, handle_list_manifest
# Import CLI argument parser
from cli import parse_arguments
# Import manifest load/save and constants
from manifest import load_manifest, save_manifest # DEFAULT_MANIFEST_FILE is not directly used in main.py anymore


# --- Main Function ---
def main():
    args = parse_arguments()

    # The os module is imported at the top of the file.
    if (hasattr(args, "transcribe") and args.transcribe) or \
       (hasattr(args, "viral_short_identifier") and args.viral_short_identifier):
        if not os.environ.get("GOOGLE_API_KEY"):
            print(
                "[ERROR] GOOGLE_API_KEY environment variable is not set. Required for transcription/analysis."
            )
            # Consider exiting if API key is crucial and missing for requested operations
            # sys.exit(1)

    manifest_df = load_manifest(args.manifest_file)
    # print("--- Manifest Dtypes after initial load ---") # Too verbose
    # print( # Too verbose
    #     manifest_df.dtypes
    #     if not manifest_df.empty
    #     else "Manifest is empty, dtypes not applicable yet."
    # )

    if args.command_name == "process":
        # Effective directory setup is now handled within parse_arguments in cli.py
        manifest_df = process_youtube_url(args, manifest_df, args.manifest_file)
        # orchestrator.process_youtube_url handles its own manifest saving per step.
        # A final save here ensures the latest state is written if any intermediate step failed
        # but the manifest was modified.
    # save_manifest(manifest_df, args.manifest_file) # Orchestrator saves after each logical step.
    # print(f"[INFO] Final manifest state saved to {args.manifest_file} after process command.") # Redundant if orchestrator saves
    # pass # No final save needed here as orchestrator handles it.

    elif args.command_name == "manage":
        if args.manage_action == "remove":
            manifest_df = handle_remove_url(args.url, manifest_df, args.manifest_file)
        # handle_remove_url in orchestrator now saves the manifest, so no save needed here.
        # print(f"[INFO] Manifest updated and saved by remove operation via orchestrator to {args.manifest_file}.")
        elif args.manage_action == "list":
            handle_list_manifest(manifest_df)
            # list does not modify, so no save needed from here.

        # Save manifest after manage operations (if not already saved by handler like remove)
    # This is now handled by individual manage handlers if they modify the manifest.
    # if args.manage_action != "list": # List doesn't change manifest
    #      save_manifest(manifest_df, args.manifest_file)
    #      print(f"[INFO] Final manifest state saved to {args.manifest_file} after manage operation.")


if __name__ == "__main__":
    # Need to import os here if GOOGLE_API_KEY check is to work
    import os
    # import sys # if sys.exit is used
    import argparse # Though args are parsed in cli.py, main still uses hasattr on args
    main()
