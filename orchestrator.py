import os
import pandas as pd # For pd.NA and type hints
from pytubefix import YouTube # For type hints, and used by handle_remove_url (indirectly via get_yt_object_and_canonical_url)

# Import from our new modules
from manifest import (
    get_manifest_entry,
    update_manifest_entry,
    save_manifest,
    # MANIFEST_COLUMNS, # Not directly used here but good to be aware of
)
from youtube_utils import (
    get_sanitized_base_name,
    download_video,
    download_audio_stream,
    get_yt_object_and_canonical_url,
)
from audio_processing import convert_to_mp3, generate_caption_files
from gemini_interaction import transcribe_audio_gemini, identify_viral_clips_gemini


def process_youtube_url(args, manifest_df, manifest_path):
    input_url_arg = args.url
    force_processing = args.force

    yt, canonical_url = get_yt_object_and_canonical_url(input_url_arg)
    if not yt:
        return manifest_df # Error already printed

    current_base_name = get_sanitized_base_name(yt.title, args.filename)
    print(f"[INFO] Processing URL: {input_url_arg} (Canonical: {canonical_url})")

    entry = get_manifest_entry(manifest_df, canonical_url)

    if entry is None:
        print(
            f"[INFO] No existing manifest entry for {canonical_url}. Creating new one."
        )
        manifest_df = update_manifest_entry(
            manifest_df,
            canonical_url,
            {"base_filename": current_base_name, "youtube_url": canonical_url},
        )
        entry = get_manifest_entry(manifest_df, canonical_url)
        if entry is None:
            print(
                f"[CRITICAL_ERROR] Failed to create or retrieve new manifest entry for {canonical_url}. Aborting processing for this URL."
            )
            return manifest_df
    # No specific logging if entry is found, it's the normal path.

    manifest_base_name = entry.get("base_filename")
    if pd.isna(manifest_base_name) or not str(manifest_base_name).strip():
        print(
            f"[INFO] base_filename missing or empty in manifest for {canonical_url}. Using current: {current_base_name}"
        )
        manifest_df = update_manifest_entry(
            manifest_df, canonical_url, {"base_filename": current_base_name}
        )
        entry = get_manifest_entry(manifest_df, canonical_url)
        base_name_for_paths = current_base_name
    else:
        if args.filename and args.filename != manifest_base_name:
            print(
                f"[WARNING] Custom filename '{args.filename}' provided, but manifest has '{manifest_base_name}' for {canonical_url}."
            )
            print(
                f"         Using manifest base_filename '{manifest_base_name}' to locate existing files."
            )
        base_name_for_paths = manifest_base_name

    # Base name for paths is now determined.

    # --- 1. Video Download ---
    video_download_path_from_manifest = entry.get("video_path")
    video_status_from_manifest = entry.get("status_video_downloaded")
    video_download_path_to_use = None

    # Cache check logic for video download.
    if not args.audio: # Not in audio-only mode
        if (
            not force_processing
            and video_status_from_manifest == True
            and pd.notna(video_download_path_from_manifest)
            and str(video_download_path_from_manifest).strip()
            and os.path.exists(str(video_download_path_from_manifest))
        ):
            print(f"[CACHE] Using existing video: {video_download_path_from_manifest}")
            video_download_path_to_use = str(video_download_path_from_manifest)
        else:
            if video_status_from_manifest == True and (
                not pd.notna(video_download_path_from_manifest)
                or not str(video_download_path_from_manifest).strip()
                or not os.path.exists(str(video_download_path_from_manifest))
            ):
                print(
                    f"[INFO] Video status was True, but file missing/path invalid. Re-downloading for {base_name_for_paths}."
                )
            elif force_processing:
                print(f"[INFO] Force processing video for {base_name_for_paths}.")
            else:
                print(f"[INFO] Attempting to download video: {base_name_for_paths}")

            downloaded_path = download_video(yt, base_name_for_paths, args.effective_video_dir, args.resolution)

            if downloaded_path:
                video_download_path_to_use = downloaded_path
                manifest_df = update_manifest_entry(
                    manifest_df,
                    canonical_url,
                    {
                        "video_path": video_download_path_to_use,
                        "status_video_downloaded": True,
                    },
                )
                entry = get_manifest_entry(manifest_df, canonical_url)
            else:
                video_download_path_to_use = None
                manifest_df = update_manifest_entry(
                    manifest_df,
                    canonical_url,
                    {"video_path": pd.NA, "status_video_downloaded": False},
                )
                entry = get_manifest_entry(manifest_df, canonical_url)
            save_manifest(manifest_df, manifest_path)
    else:  # audio-only mode
        video_download_path_to_use = None # Ensure it's None
        if video_status_from_manifest != False or pd.notna(video_download_path_from_manifest):
            manifest_df = update_manifest_entry(
                manifest_df,
                canonical_url,
                {"video_path": pd.NA, "status_video_downloaded": False},
            )
            entry = get_manifest_entry(manifest_df, canonical_url)
            save_manifest(manifest_df, manifest_path)

    # --- 2. MP3 Conversion ---
    mp3_path_from_manifest = entry.get("mp3_path")
    mp3_status_from_manifest = entry.get("status_mp3_converted")
    needs_mp3 = args.audio or args.transcribe or args.viral_short_identifier or args.generate_captions
    mp3_file_for_processing = None

    # Cache check logic for MP3 conversion.
    if needs_mp3:
        # --- Improved Cache Logic ---
        # Default to manifest path if valid
        if (
            not force_processing
            and mp3_status_from_manifest == True
            and pd.notna(mp3_path_from_manifest)
            and str(mp3_path_from_manifest).strip()
            and os.path.exists(str(mp3_path_from_manifest))
        ):
            print(f"[CACHE] Using existing MP3 from manifest: {mp3_path_from_manifest}")
            mp3_file_for_processing = str(mp3_path_from_manifest)
        else:
            # Fallback to check expected path
            expected_mp3_path = os.path.join(args.effective_audio_dir, base_name_for_paths + ".mp3")
            if not force_processing and os.path.exists(expected_mp3_path):
                print(f"[CACHE] Found existing MP3 at expected path, updating manifest: {expected_mp3_path}")
                mp3_file_for_processing = os.path.abspath(expected_mp3_path)
                manifest_df = update_manifest_entry(
                    manifest_df,
                    canonical_url,
                    {
                        "mp3_path": mp3_file_for_processing,
                        "status_mp3_converted": True,
                    },
                )
                entry = get_manifest_entry(manifest_df, canonical_url)
                save_manifest(manifest_df, manifest_path)

        # If after all checks, we still don't have a file, generate it.
        if not mp3_file_for_processing:
            if mp3_status_from_manifest == True and (
                not pd.notna(mp3_path_from_manifest)
                or not str(mp3_path_from_manifest).strip()
                or not os.path.exists(str(mp3_path_from_manifest))
            ):
                print(
                    f"[INFO] MP3 status was True, but file missing/path invalid. Re-processing MP3 for {base_name_for_paths}."
                )
            elif force_processing:
                print(f"[INFO] Force processing MP3 for {base_name_for_paths}.")

            source_for_ffmpeg = None
            if (
                not args.audio # Not audio-only, so video *might* exist
                and video_download_path_to_use # Check if video was successfully obtained
                and os.path.exists(video_download_path_to_use)
            ):
                print(
                    f"[INFO] Using downloaded video as source for MP3: {video_download_path_to_use}"
                )
                source_for_ffmpeg = video_download_path_to_use
            else: # Audio-only mode, or video download failed/skipped
                print("[INFO] Attempting to download dedicated audio stream for MP3 conversion...")
                raw_audio_input_path = download_audio_stream(yt, base_name_for_paths, args.effective_audio_dir)
                if raw_audio_input_path:
                    source_for_ffmpeg = raw_audio_input_path
                else:
                    manifest_df = update_manifest_entry(
                        manifest_df,
                        canonical_url,
                        {"mp3_path": pd.NA, "status_mp3_converted": False},
                    )
                    entry = get_manifest_entry(manifest_df, canonical_url)
                    save_manifest(manifest_df, manifest_path) # Save state and potentially skip next steps

            if source_for_ffmpeg:
                os.makedirs(args.effective_audio_dir, exist_ok=True)
                final_mp3_path_target = os.path.join(
                    args.effective_audio_dir, base_name_for_paths + ".mp3"
                )
                converted_mp3_path = convert_to_mp3(
                    source_for_ffmpeg, final_mp3_path_target
                )
                if converted_mp3_path:
                    mp3_file_for_processing = os.path.abspath(converted_mp3_path)
                    manifest_df = update_manifest_entry(
                        manifest_df,
                        canonical_url,
                        {
                            "mp3_path": mp3_file_for_processing,
                            "status_mp3_converted": True,
                        },
                    )
                else:
                    print(f"[ERROR] MP3 conversion failed for {canonical_url}.")
                    mp3_file_for_processing = None
                    manifest_df = update_manifest_entry(
                        manifest_df,
                        canonical_url,
                        {"mp3_path": pd.NA, "status_mp3_converted": False},
                    )
                entry = get_manifest_entry(manifest_df, canonical_url)
            save_manifest(manifest_df, manifest_path)

    elif mp3_status_from_manifest != False or pd.notna(mp3_path_from_manifest): # If not needed, but manifest had info
        manifest_df = update_manifest_entry(
            manifest_df,
            canonical_url,
            {"mp3_path": pd.NA, "status_mp3_converted": False},
        )
        entry = get_manifest_entry(manifest_df, canonical_url)
        save_manifest(manifest_df, manifest_path)

    # --- 3. Transcription ---
    transcript_content = None # Store content if loaded or generated
    transcript_path_from_manifest = entry.get("transcript_path")
    transcript_status_from_manifest = entry.get("status_transcript_generated")
    needs_transcription = args.transcribe or args.viral_short_identifier

    # Cache check logic for transcription.
    if needs_transcription:
        if mp3_file_for_processing and os.path.exists(mp3_file_for_processing):
            if (
                not force_processing
                and transcript_status_from_manifest == True
                and pd.notna(transcript_path_from_manifest)
                and str(transcript_path_from_manifest).strip()
                and os.path.exists(str(transcript_path_from_manifest))
            ):
                print(
                    f"[CACHE] Loading transcript from: {transcript_path_from_manifest}"
                )
                try:
                    with open(
                        str(transcript_path_from_manifest), "r", encoding="utf-8"
                    ) as f:
                        transcript_content = f.read()
                    if not transcript_content.strip():
                        print(
                            f"[WARNING] Cached transcript file {transcript_path_from_manifest} is empty. Will re-transcribe."
                        )
                        transcript_content = None
                        manifest_df = update_manifest_entry(
                            manifest_df,
                            canonical_url,
                            {"status_transcript_generated": False}, # Keep path, but mark status false
                        )
                        entry = get_manifest_entry(manifest_df, canonical_url)
                except Exception as e:
                    print(
                        f"[ERROR] Failed to read cached transcript {transcript_path_from_manifest}: {e}"
                    )
                    transcript_content = None
                    manifest_df = update_manifest_entry(
                        manifest_df,
                        canonical_url,
                        {
                            "status_transcript_generated": False,
                            "transcript_path": pd.NA,
                        },
                    )
                    entry = get_manifest_entry(manifest_df, canonical_url)

            if transcript_content is None: # Process if not loaded from cache or cache was invalid/empty
                if transcript_status_from_manifest == True and (
                    not pd.notna(transcript_path_from_manifest)
                    or not str(transcript_path_from_manifest).strip()
                    or not os.path.exists(str(transcript_path_from_manifest))
                ):
                    print(
                        f"[INFO] Transcript status was True, but file/path invalid or content empty. Re-transcribing for {base_name_for_paths}."
                    )
                elif force_processing:
                    print(
                        f"[INFO] Force processing transcription for {base_name_for_paths}."
                    )

                print("[INFO] Performing audio transcription...")
                os.makedirs(args.effective_transcript_dir, exist_ok=True)
                transcription_result = transcribe_audio_gemini(
                    mp3_file_for_processing,
                    args.effective_transcript_dir,
                    base_name_for_paths,
                    args.gemini_model,
                    save_transcript_file=True,
                )
                transcript_content = transcription_result["text"]
                new_transcript_path = pd.NA

                if transcript_content is not None: # Gemini returned something (even if empty string)
                    new_transcript_path = (
                        os.path.abspath(transcription_result["path"])
                        if transcription_result["path"] and os.path.exists(transcription_result["path"])
                        else pd.NA
                    )
                    manifest_df = update_manifest_entry(
                        manifest_df,
                        canonical_url,
                        {
                            "transcript_path": new_transcript_path,
                            "status_transcript_generated": (
                                True
                                if pd.notna(new_transcript_path) and transcript_content.strip() # Status True only if path valid AND content exists
                                else False
                            ),
                        },
                    )
                else: # Gemini failed (returned None for text)
                    manifest_df = update_manifest_entry(
                        manifest_df,
                        canonical_url,
                        {
                            "transcript_path": pd.NA,
                            "status_transcript_generated": False,
                        },
                    )
                entry = get_manifest_entry(manifest_df, canonical_url)
                save_manifest(manifest_df, manifest_path)
        else:
            print(
                "[WARNING] MP3 not available or path invalid, skipping transcription."
            )
            if transcript_status_from_manifest != False or pd.notna(transcript_path_from_manifest):
                manifest_df = update_manifest_entry(
                    manifest_df,
                    canonical_url,
                    {"transcript_path": pd.NA, "status_transcript_generated": False},
                )
                entry = get_manifest_entry(manifest_df, canonical_url)
                save_manifest(manifest_df, manifest_path)
    elif transcript_status_from_manifest != False or pd.notna(transcript_path_from_manifest):
        manifest_df = update_manifest_entry(
            manifest_df,
            canonical_url,
            {"transcript_path": pd.NA, "status_transcript_generated": False},
        )
        entry = get_manifest_entry(manifest_df, canonical_url)
        save_manifest(manifest_df, manifest_path)


    # --- 4. Viral Clip Analysis ---
    analysis_path_from_manifest = entry.get("analysis_path")
    analysis_status_from_manifest = entry.get("status_analysis_generated")

    # Cache check logic for viral clip analysis.
    if args.viral_short_identifier:
        cached_analysis_valid_and_present = False
        if (
            not force_processing
            and analysis_status_from_manifest == True
            and pd.notna(analysis_path_from_manifest)
            and str(analysis_path_from_manifest).strip()
            and os.path.exists(str(analysis_path_from_manifest))
        ):
            try:
                if os.path.getsize(str(analysis_path_from_manifest)) > 0:
                    print(
                        f"[CACHE] Using existing analysis: {analysis_path_from_manifest}"
                    )
                    cached_analysis_valid_and_present = True
                else:
                    print(
                        f"[WARNING] Cached analysis file {analysis_path_from_manifest} is empty. Will re-analyze."
                    )
                    manifest_df = update_manifest_entry(
                        manifest_df, canonical_url, {"status_analysis_generated": False} # Keep path, mark status false
                    )
                    entry = get_manifest_entry(manifest_df, canonical_url)
            except OSError:
                print(
                    f"[WARNING] Could not check size of cached analysis file {analysis_path_from_manifest}. Assuming invalid."
                )
                cached_analysis_valid_and_present = False # Ensure it's false

        if transcript_content and transcript_content.strip(): # Check if we have transcript content
            if not cached_analysis_valid_and_present:
                if analysis_status_from_manifest == True and (
                     not pd.notna(analysis_path_from_manifest)
                    or not str(analysis_path_from_manifest).strip()
                    or not os.path.exists(str(analysis_path_from_manifest))
                    # or cached_analysis_valid_and_present was False due to empty file (implicitly handled by not cached_analysis_valid_and_present)
                ):
                    print(
                        f"[INFO] Analysis status was True, but file/path invalid or content empty. Re-analyzing for {base_name_for_paths}."
                    )
                elif force_processing:
                    print(
                        f"[INFO] Force processing analysis for {base_name_for_paths}."
                    )

                print("[INFO] Performing viral clip analysis...")
                os.makedirs(args.effective_analysis_dir, exist_ok=True)
                generated_analysis_path = identify_viral_clips_gemini(
                    transcript_content, # Use the obtained transcript content
                    args.number_of_sections,
                    args.clip_identifier_model,
                    args.effective_analysis_dir,
                    base_name_for_paths,
                )
                abs_analysis_path = pd.NA
                analysis_content_exists = False
                if generated_analysis_path and os.path.exists(generated_analysis_path):
                    abs_analysis_path = os.path.abspath(generated_analysis_path)
                    try:
                        if os.path.getsize(abs_analysis_path) > 0:
                            analysis_content_exists = True
                    except OSError:
                        pass

                manifest_df = update_manifest_entry(
                    manifest_df,
                    canonical_url,
                    {
                        "analysis_path": abs_analysis_path,
                        "status_analysis_generated": (
                            True
                            if pd.notna(abs_analysis_path) and analysis_content_exists
                            else False
                        ),
                    },
                )
                entry = get_manifest_entry(manifest_df, canonical_url)
                save_manifest(manifest_df, manifest_path)
        else:
            print(
                "[WARNING] Transcript not available or empty, skipping viral clip analysis."
            )
            if analysis_status_from_manifest != False or pd.notna(analysis_path_from_manifest):
                manifest_df = update_manifest_entry(
                    manifest_df,
                    canonical_url,
                    {"analysis_path": pd.NA, "status_analysis_generated": False},
                )
                entry = get_manifest_entry(manifest_df, canonical_url)
                save_manifest(manifest_df, manifest_path)
    elif analysis_status_from_manifest != False or pd.notna(analysis_path_from_manifest):
        manifest_df = update_manifest_entry(
            manifest_df,
            canonical_url,
            {"analysis_path": pd.NA, "status_analysis_generated": False},
        )
        entry = get_manifest_entry(manifest_df, canonical_url)
        save_manifest(manifest_df, manifest_path)

    # --- 5. Caption Generation ---
    caption_srt_path_from_manifest = entry.get("caption_srt_path")
    caption_ass_path_from_manifest = entry.get("caption_ass_path")
    caption_status_from_manifest = entry.get("status_captions_generated")

    if args.generate_captions:
        cached_captions_valid_and_present = False
        # --- Improved Cache Logic ---
        # Default to manifest path if valid
        if (
            not force_processing
            and caption_status_from_manifest == True
            and pd.notna(caption_srt_path_from_manifest)
            and os.path.exists(str(caption_srt_path_from_manifest))
            and pd.notna(caption_ass_path_from_manifest)
            and os.path.exists(str(caption_ass_path_from_manifest))
        ):
            print(f"[CACHE] Using existing captions from manifest: {caption_srt_path_from_manifest}, etc.")
            cached_captions_valid_and_present = True
        else:
            # Fallback to check expected paths
            expected_srt_path = os.path.join(args.effective_caption_dir, base_name_for_paths + ".srt")
            expected_ass_path = os.path.join(args.effective_caption_dir, base_name_for_paths + ".ass")
            if (
                not force_processing and
                os.path.exists(expected_srt_path) and
                os.path.exists(expected_ass_path)
            ):
                print(f"[CACHE] Found existing caption files at expected paths, updating manifest: {args.effective_caption_dir}")
                manifest_df = update_manifest_entry(
                    manifest_df,
                    canonical_url,
                    {
                        "caption_srt_path": os.path.abspath(expected_srt_path),
                        "caption_ass_path": os.path.abspath(expected_ass_path),
                        "status_captions_generated": True,
                    },
                )
                entry = get_manifest_entry(manifest_df, canonical_url)
                save_manifest(manifest_df, manifest_path)
                cached_captions_valid_and_present = True

        if not cached_captions_valid_and_present:
            if caption_status_from_manifest == True and (
                not pd.notna(caption_srt_path_from_manifest)
                or not os.path.exists(str(caption_srt_path_from_manifest))
                or not pd.notna(caption_ass_path_from_manifest)
                or not os.path.exists(str(caption_ass_path_from_manifest))
            ):
                print(
                    f"[INFO] Caption status was True, but files missing/path invalid. Re-generating captions for {base_name_for_paths}."
                )
            elif force_processing:
                print(f"[INFO] Force processing captions for {base_name_for_paths}.")

        if mp3_file_for_processing and os.path.exists(mp3_file_for_processing):
            if not cached_captions_valid_and_present:
                print("[INFO] Generating caption files...")
                os.makedirs(args.effective_caption_dir, exist_ok=True)
                caption_paths = generate_caption_files(
                    mp3_file_for_processing,
                    args.effective_caption_dir,
                    base_name_for_paths,
                    args.whisper_model,
                )
                if caption_paths:
                    manifest_df = update_manifest_entry(
                        manifest_df,
                        canonical_url,
                        {
                            "caption_srt_path": os.path.abspath(caption_paths["srt"]),
                            "caption_ass_path": os.path.abspath(caption_paths["ass"]),
                            "status_captions_generated": True,
                        },
                    )
                else:
                    print(f"[ERROR] Caption generation failed for {canonical_url}.")
                    manifest_df = update_manifest_entry(
                        manifest_df,
                        canonical_url,
                        {
                            "caption_srt_path": pd.NA,
                            "caption_ass_path": pd.NA,
                            "status_captions_generated": False,
                        },
                    )
                entry = get_manifest_entry(manifest_df, canonical_url)
                save_manifest(manifest_df, manifest_path)
        else:
            print("[WARNING] MP3 not available or path invalid, skipping caption generation.")
            if caption_status_from_manifest != False or pd.notna(caption_srt_path_from_manifest):
                manifest_df = update_manifest_entry(
                    manifest_df,
                    canonical_url,
                    {
                        "caption_srt_path": pd.NA,
                        "caption_ass_path": pd.NA,
                        "status_captions_generated": False,
                    },
                )
                entry = get_manifest_entry(manifest_df, canonical_url)
                save_manifest(manifest_df, manifest_path)
    elif caption_status_from_manifest != False or pd.notna(caption_srt_path_from_manifest):
        manifest_df = update_manifest_entry(
            manifest_df,
            canonical_url,
            {
                "caption_srt_path": pd.NA,
                "caption_ass_path": pd.NA,
                "status_captions_generated": False,
            },
        )
        entry = get_manifest_entry(manifest_df, canonical_url)
        save_manifest(manifest_df, manifest_path)

    print(f"[INFO] Processing for {canonical_url} complete.")
    return manifest_df


# --- Manage Command Handlers ---
def handle_remove_url(url_to_remove_input, manifest_df, manifest_path):
    yt_remove, url_to_remove_canonical = get_yt_object_and_canonical_url(url_to_remove_input)

    if not yt_remove:
        print(
            f"[WARNING] Could not get canonical URL for '{url_to_remove_input}'. Trying to remove using the provided input."
        )
        url_to_remove_canonical = url_to_remove_input
    # If yt_remove is successful, canonical_url is used silently.

    entry = get_manifest_entry(manifest_df, url_to_remove_canonical)
    if entry is None:
        if url_to_remove_canonical != url_to_remove_input: # If canonical was different and not found
            # Attempt to find using the original input if canonical lookup failed
            entry = get_manifest_entry(manifest_df, url_to_remove_input)
            if entry is None:
                print(
                    f"[INFO] URL not found in manifest (tried canonical and original input): {url_to_remove_input}"
                )
                return manifest_df
            else: # Original input was found
                url_to_remove_canonical = url_to_remove_input
                print(f"[INFO] Found URL using original input: {url_to_remove_canonical}")
        else: # Original input was used (same as canonical or canonical failed early), and not found
            print(f"[INFO] URL not found in manifest: {url_to_remove_canonical}")
            return manifest_df

    print(
        f"[INFO] Removing URL '{url_to_remove_canonical}' and associated files from manifest."
    )
    files_to_delete = [
        entry.get("video_path"),
        entry.get("mp3_path"),
        entry.get("transcript_path"),
        entry.get("analysis_path"),
        entry.get("caption_srt_path"),
        entry.get("caption_ass_path"),
    ]
    for file_path_obj in files_to_delete:
        if pd.notna(file_path_obj) and str(file_path_obj).strip():
            file_path = str(file_path_obj)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"[SUCCESS] Deleted file: {file_path}")
                except OSError as e:
                    print(f"[ERROR] Could not delete file {file_path}: {e}")
            else:
                print(
                    f"[INFO] File not found (already deleted or path incorrect?): {file_path}"
                )
        elif pd.notna(file_path_obj): # Path was in manifest but resolved to empty string or just spaces
             print(f"[INFO] Path in manifest was present but empty or invalid: '{file_path_obj}'")


    manifest_df = manifest_df[
        manifest_df["youtube_url"] != url_to_remove_canonical
    ].reset_index(drop=True)
    print(f"[SUCCESS] Removed entry for {url_to_remove_canonical} from manifest.")
    save_manifest(manifest_df, manifest_path) # Save after removal
    return manifest_df


def handle_list_manifest(manifest_df):
    if manifest_df.empty:
        print("[INFO] Manifest is empty.")
        return
    print("\n--- Manifest Contents ---")
    with pd.option_context(
        "display.max_colwidth", 50, "display.width", 1000, "display.max_rows", 25
    ):
        cols_to_display = ["youtube_url", "base_filename", "status_video_downloaded", "status_mp3_converted", "status_transcript_generated", "status_analysis_generated", "status_captions_generated"]
        # Filter out columns that might not exist to prevent errors
        cols_to_display = [col for col in cols_to_display if col in manifest_df.columns]
        if not cols_to_display:
            print(manifest_df.head(20).to_string()) # Fallback to all if preferred are missing
        else:
            print(manifest_df[cols_to_display].head(20).to_string())

    print(f"--- Total entries: {len(manifest_df)} ---")
    print("--- End of Manifest List ---\n")
