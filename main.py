# For local execution, you would first need to install these packages:
# pip install pytubefix google-generativeai pandas

import argparse
import os
import subprocess
import sys
from pytubefix import YouTube
import google.generativeai as genai
import pandas as pd
from datetime import datetime

# --- Manifest Constants ---
MANIFEST_COLUMNS = [
    "youtube_url",
    "base_filename",
    "video_path",
    "mp3_path",
    "transcript_path",
    "analysis_path",
    "status_video_downloaded",
    "status_mp3_converted",
    "status_transcript_generated",
    "status_analysis_generated",
    "last_updated",
]
DEFAULT_MANIFEST_FILE = "processing_manifest.csv"


# --- Manifest Helper Functions ---
def load_manifest(manifest_path):
    """Loads the manifest CSV into a pandas DataFrame."""
    if os.path.exists(manifest_path):
        try:
            df = pd.read_csv(
                manifest_path,
                keep_default_na=True,  # Important for pd.NA
                na_values=[  # Comprehensive list of NA values
                    "",
                    "#N/A",
                    "#N/A N/A",
                    "#NA",
                    "-1.#IND",
                    "-1.#QNAN",
                    "-NaN",
                    "-nan",
                    "1.#IND",
                    "1.#QNAN",
                    "<NA>",  # pandas uses <NA> for its NA object sometimes
                    "N/A",
                    "NA",
                    "NULL",
                    "NaN",
                    "nan",  # lowercase nan
                    "null",  # lowercase null
                ],
                dtype_backend="numpy_nullable",  # Use pandas nullable dtypes where possible
            )

            # Ensure all manifest columns exist, add if missing
            for col in MANIFEST_COLUMNS:
                if col not in df.columns:
                    df[col] = (
                        pd.NA
                    )  # Initialize new columns with pd.NA, compatible with BooleanDtype

            bool_status_cols = [
                "status_video_downloaded",
                "status_mp3_converted",
                "status_transcript_generated",
                "status_analysis_generated",
            ]
            for col_name in bool_status_cols:
                if col_name in df.columns:
                    try:
                        df[col_name] = df[col_name].astype(pd.BooleanDtype())
                    except Exception as e_astype:
                        print(
                            f"[ERROR] load_manifest: Failed to convert column '{col_name}' to BooleanDtype. Error: {e_astype}"
                        )
                        print(
                            f"         Unique values in column '{col_name}' before error: {df[col_name].unique()[:10]}"
                        )
                else:  # If column was just added
                    df[col_name] = pd.Series([pd.NA] * len(df), dtype=pd.BooleanDtype())

            path_cols = ["video_path", "mp3_path", "transcript_path", "analysis_path"]
            for col_name in path_cols:
                if col_name in df.columns:
                    df[col_name] = df[col_name].astype(pd.StringDtype())
                else:
                    df[col_name] = pd.Series([pd.NA] * len(df), dtype=pd.StringDtype())

            if "youtube_url" in df.columns:
                df["youtube_url"] = df["youtube_url"].astype(pd.StringDtype())
            else:
                df["youtube_url"] = pd.Series([pd.NA] * len(df), dtype=pd.StringDtype())

            if "base_filename" in df.columns:
                df["base_filename"] = df["base_filename"].astype(pd.StringDtype())
            else:
                df["base_filename"] = pd.Series(
                    [pd.NA] * len(df), dtype=pd.StringDtype()
                )

            if "last_updated" in df.columns:
                df["last_updated"] = df["last_updated"].astype(pd.StringDtype())
            else:
                df["last_updated"] = pd.Series(
                    [pd.NA] * len(df), dtype=pd.StringDtype()
                )

            return df
        except pd.errors.EmptyDataError:
            print(f"[WARNING] Manifest file {manifest_path} is empty. Starting fresh.")
        except Exception as e:
            print(
                f"[ERROR] Could not load manifest {manifest_path}: {e}. Starting fresh."
            )
            import traceback

            traceback.print_exc()

    print(
        f"[INFO] Creating a new manifest structure as {manifest_path} does not exist or failed to load."
    )
    df = pd.DataFrame(columns=MANIFEST_COLUMNS)
    dtype_map = {
        "youtube_url": pd.StringDtype(),
        "base_filename": pd.StringDtype(),
        "video_path": pd.StringDtype(),
        "mp3_path": pd.StringDtype(),
        "transcript_path": pd.StringDtype(),
        "analysis_path": pd.StringDtype(),
        "status_video_downloaded": pd.BooleanDtype(),
        "status_mp3_converted": pd.BooleanDtype(),
        "status_transcript_generated": pd.BooleanDtype(),
        "status_analysis_generated": pd.BooleanDtype(),
        "last_updated": pd.StringDtype(),
    }
    for col, col_dtype in dtype_map.items():
        df[col] = pd.Series(dtype=col_dtype)
    return df


def save_manifest(df, manifest_path):
    """Saves the DataFrame to the manifest CSV."""
    try:
        df.to_csv(manifest_path, index=False)
    except Exception as e:
        print(f"[ERROR] Could not save manifest to {manifest_path}: {e}")


def get_manifest_entry(df, url_to_find):
    """Gets the manifest entry for a given URL. Returns a pandas Series or None."""
    if "youtube_url" not in df.columns or df.empty:
        return None
    entry_df = df[df["youtube_url"] == url_to_find]
    if not entry_df.empty:
        return entry_df.iloc[0].copy()
    else:
        return None


def update_manifest_entry(df, url_key, data_dict):
    """Updates or adds an entry in the manifest DataFrame, using url_key."""
    existing_entry_index = df[df["youtube_url"] == url_key].index

    current_time = datetime.now().isoformat()
    data_dict["last_updated"] = current_time

    bool_status_cols = [
        "status_video_downloaded",
        "status_mp3_converted",
        "status_transcript_generated",
        "status_analysis_generated",
    ]
    for col_name in bool_status_cols:
        if col_name in data_dict:
            val = data_dict[col_name]
            if pd.isna(val):
                data_dict[col_name] = pd.NA
            elif isinstance(val, str):
                if val.lower() == "true":
                    data_dict[col_name] = True
                elif val.lower() == "false":
                    data_dict[col_name] = False
                else:
                    data_dict[col_name] = pd.NA
            elif isinstance(val, bool):  # Already a Python bool
                data_dict[col_name] = val
            # else it might be numpy.bool_ or pd.BooleanDtype bool, leave as is

    if not existing_entry_index.empty:
        idx = existing_entry_index[0]
        for key, value in data_dict.items():
            try:
                # Ensure the column exists before trying to assign with .loc
                if key not in df.columns:
                    # This case should ideally not happen if MANIFEST_COLUMNS is complete
                    # and load_manifest ensures all columns exist.
                    # If it does, initialize the column with appropriate NA and dtype.
                    if key in bool_status_cols:
                        df[key] = pd.Series(
                            pd.NA, index=df.index, dtype=pd.BooleanDtype()
                        )
                    elif key.endswith("_path") or key in [
                        "youtube_url",
                        "base_filename",
                        "last_updated",
                    ]:
                        df[key] = pd.Series(
                            pd.NA, index=df.index, dtype=pd.StringDtype()
                        )
                    else:  # Default to object or infer, though ideally all are typed
                        df[key] = pd.NA

                df.loc[idx, key] = value
            except Exception as e:
                print(
                    f"[ERROR] update_manifest_entry (update): Failed to set {key}={value} (type: {type(value)}) for URL {url_key}. Error: {e}"
                )
                print(
                    f"       Column '{key}' dtype: {df[key].dtype if key in df else 'Not in df'}"
                )
    else:
        new_entry_data = {col: pd.NA for col in MANIFEST_COLUMNS}
        new_entry_data["youtube_url"] = url_key
        new_entry_data.update(data_dict)

        try:
            new_row_df = pd.DataFrame([new_entry_data])
            # Ensure dtypes of the new row match the main DataFrame before concat
            for col in df.columns:
                if col in new_row_df.columns:
                    try:
                        new_row_df[col] = new_row_df[col].astype(df[col].dtype)
                    except Exception as e_astype_concat:
                        print(
                            f"[WARNING] update_manifest_entry (add): Could not astype column '{col}' for new entry. Error: {e_astype_concat}. Value: {new_row_df[col].iloc[0]}, Target Dtype: {df[col].dtype}"
                        )
                        # Fallback: if astype fails, try to proceed; concat might still work or give a more specific error
                # If a column from df is not in new_row_df (shouldn't happen if new_entry_data has all MANIFEST_COLUMNS)
                # it will be pd.NA in the new row when concatenated, which is fine.

            df = pd.concat([df, new_row_df], ignore_index=True)
        except Exception as e:
            print(
                f"[ERROR] update_manifest_entry (add): Failed to concat new entry for URL {url_key}. Error: {e}"
            )
            print(f"       New entry data: {new_entry_data}")
            print(f"       Main df dtypes: \n{df.dtypes}")
            import traceback

            traceback.print_exc()
    return df


def get_sanitized_base_name(yt_title, custom_filename=None):
    if custom_filename:
        return "".join(
            c if c.isalnum() or c in " ._-" else "_" for c in custom_filename
        )
    return "".join(c if c.isalnum() or c in " ._-" else "_" for c in yt_title)


# --- Core Functions (Modified for Manifest Interaction) ---
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
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        if (
            "_audiotemp." in os.path.basename(input_path)
            and os.path.exists(input_path)
            and input_path != output_mp3_path
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
    except Exception as e:
        print(
            f"[ERROR] ffmpeg conversion failed: {e} for {input_path} to {output_mp3_path}"
        )
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


def transcribe_audio_gemini(
    audio_file_path,
    transcript_output_dir,
    base_filename,
    model_name,
    save_transcript_file=True,
):
    if not os.path.exists(audio_file_path):
        print(f"[ERROR] Audio file for transcription not found: {audio_file_path}")
        return {"text": None, "path": None}
    if os.path.getsize(audio_file_path) == 0:
        print(f"[ERROR] Audio file for transcription is empty: {audio_file_path}")
        return {"text": None, "path": None}

    print(f"[INFO] Transcribing {audio_file_path} using model {model_name}...")
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("[ERROR] GOOGLE_API_KEY not set.")
        return {"text": None, "path": None}

    uploaded_audio_file_details = None
    transcript_text_to_return = None
    transcript_file_path = None

    try:
        genai.configure(api_key=api_key)
        audio_file_obj = genai.upload_file(path=audio_file_path)
        uploaded_audio_file_details = audio_file_obj
        print(f"[SUCCESS] File uploaded to Gemini: {audio_file_obj.name}")

        model = genai.GenerativeModel(model_name=model_name)
        response = model.generate_content(
            ["Please transcribe this audio.", audio_file_obj],
            request_options={"timeout": 16000},
        )

        transcript_text = ""
        if hasattr(response, "text") and response.text:
            transcript_text = response.text
        elif hasattr(response, "parts") and response.parts:
            for part in response.parts:
                if hasattr(part, "text") and part.text:
                    transcript_text += part.text + "\n"
            transcript_text = transcript_text.strip()
        if (
            not transcript_text.strip()
            and hasattr(response, "candidates")
            and response.candidates
        ):
            try:
                if (
                    response.candidates[0].content
                    and len(response.candidates[0].content.parts) > 0
                    and hasattr(response.candidates[0].content.parts[0], "text")
                    and response.candidates[0].content.parts[0].text
                ):
                    transcript_text = response.candidates[0].content.parts[0].text
                    if transcript_text.strip():
                        print("[INFO] Extracted text via response.candidates.")
            except Exception as e_parse:
                print(f"[ERROR] Parsing Gemini response candidates: {e_parse}")

        transcript_text_to_return = transcript_text.strip() if transcript_text else ""

        if save_transcript_file:
            os.makedirs(transcript_output_dir, exist_ok=True)
            transcript_file_name = f"{base_filename}_transcript.txt"
            transcript_file_path = os.path.join(
                transcript_output_dir, transcript_file_name
            )
            with open(transcript_file_path, "w", encoding="utf-8") as f:
                f.write(transcript_text_to_return)
            if transcript_text_to_return:
                print(f"[SUCCESS] Transcript saved to: {transcript_file_path}")
            else:
                print(f"[WARNING] Empty transcript saved to: {transcript_file_path}")
        elif transcript_text_to_return:
            print("[INFO] Transcription successful (text obtained, not saved to file).")
        else:
            print("[WARNING] Transcription result is empty (not saved).")

        return {"text": transcript_text_to_return, "path": transcript_file_path}

    except Exception as e:
        print(f"[ERROR] Gemini transcription failed: {e}")
        import traceback

        traceback.print_exc()
        return {"text": None, "path": None}
    finally:
        if uploaded_audio_file_details:
            try:
                genai.delete_file(uploaded_audio_file_details.name)
                print(
                    f"[INFO] Deleted uploaded file {uploaded_audio_file_details.name} from Gemini."
                )
            except Exception as e_del:
                print(
                    f"[WARNING] Could not delete {uploaded_audio_file_details.name}: {e_del}"
                )


def get_viral_clip_identifier_prompt(transcript_text, number_of_sections):
    prompt = f"Given the following transcript, please identify {number_of_sections if number_of_sections else 'several'} sections that have high potential to be engaging or viral short clips. For each identified section, please provide:\n1. A short, compelling title for the clip.\n2. The start and end timestamps (if available in the transcript, otherwise describe the start/end points textually).\n3. A brief explanation of why this section is likely to be engaging or go viral.\n\nTranscript:\n\"\"\"\n{transcript_text}\n\"\"\"\n\nPlease format your response clearly for each identified clip."
    if not number_of_sections:
        prompt = prompt.replace(
            f" {number_of_sections if number_of_sections else 'several'} sections",
            " several sections (e.g., 3-5)",
        )
    return prompt


def identify_viral_clips_gemini(
    transcript_text, number_of_sections, model_name, analysis_output_dir, base_filename
):
    if not transcript_text or not transcript_text.strip():
        print("[ERROR] Transcript text is empty for viral clip ID.")
        return None

    print(f"[INFO] Identifying viral clips with {model_name}...")
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("[ERROR] GOOGLE_API_KEY not set.")
        return None

    analysis_file_path = None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name=model_name)
        prompt = get_viral_clip_identifier_prompt(transcript_text, number_of_sections)
        response = model.generate_content([prompt], request_options={"timeout": 900})

        analysis_text = ""
        if hasattr(response, "text") and response.text:
            analysis_text = response.text
        elif hasattr(response, "parts") and response.parts:
            for part in response.parts:
                if hasattr(part, "text") and part.text:
                    analysis_text += part.text + "\n"
            analysis_text = analysis_text.strip()
        if (
            not analysis_text.strip()
            and hasattr(response, "candidates")
            and response.candidates
        ):
            try:
                if (
                    response.candidates[0].content
                    and len(response.candidates[0].content.parts) > 0
                    and hasattr(response.candidates[0].content.parts[0], "text")
                    and response.candidates[0].content.parts[0].text
                ):
                    analysis_text = response.candidates[0].content.parts[0].text
                    if analysis_text.strip():
                        print("[INFO] Extracted analysis via response.candidates.")
            except Exception as e_parse:
                print(
                    f"[ERROR] Parsing Gemini response candidates for analysis: {e_parse}"
                )

        analysis_text_to_save = analysis_text.strip() if analysis_text else ""

        os.makedirs(analysis_output_dir, exist_ok=True)
        analysis_file_name = f"{base_filename}_viral_clips_analysis.txt"
        analysis_file_path = os.path.join(analysis_output_dir, analysis_file_name)
        with open(analysis_file_path, "w", encoding="utf-8") as f:
            f.write(analysis_text_to_save)

        if analysis_text_to_save:
            print(f"[SUCCESS] Viral clip analysis saved to: {analysis_file_path}")
            return analysis_file_path
        else:
            print(f"[WARNING] Empty viral clip analysis saved: {analysis_file_path}")
            return analysis_file_path  # Return path even if empty, status will reflect content

    except Exception as e:
        print(f"[ERROR] Gemini viral clip ID failed: {e}")
        import traceback

        traceback.print_exc()
        return None


def process_youtube_url(args, manifest_df, manifest_path):
    input_url_arg = args.url
    force_processing = args.force

    try:
        yt = YouTube(input_url_arg)
        canonical_url = yt.watch_url
        current_base_name = get_sanitized_base_name(yt.title, args.filename)
        print(f"[INFO] Processing URL: {input_url_arg} (Canonical: {canonical_url})")
    except Exception as e:
        print(f"[ERROR] Could not fetch YouTube video details for {input_url_arg}: {e}")
        return manifest_df

    entry = get_manifest_entry(manifest_df, canonical_url)

    if entry is None:
        print(
            f"[DEBUG] No existing manifest entry for canonical URL: {canonical_url}. Creating new one."
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
        print(f"[DEBUG] New entry created and retrieved for {canonical_url}.")
    else:
        print(
            f"[DEBUG] Found existing manifest entry for canonical URL: {canonical_url}."
        )

    manifest_base_name = entry.get("base_filename")
    if pd.isna(manifest_base_name) or not str(manifest_base_name).strip():
        print(
            f"[DEBUG] base_filename missing or empty in manifest for {canonical_url}. Using current: {current_base_name}"
        )
        manifest_df = update_manifest_entry(
            manifest_df, canonical_url, {"base_filename": current_base_name}
        )
        # Re-fetch entry to get the updated base_filename if it was just set
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

    print(f"[DEBUG] Using base_name_for_paths: '{base_name_for_paths}'")

    # --- 1. Video Download ---
    video_download_path_from_manifest = entry.get("video_path")
    video_status_from_manifest = entry.get("status_video_downloaded")
    video_download_path_to_use = None  # Initialize

    # Debug block for Video Download
    print("\n--- Video Download Cache Check ---")
    print(f"URL: {canonical_url}")
    print(f"Force processing: {force_processing}")
    print(
        f"Status from manifest: {video_status_from_manifest} (type: {type(video_status_from_manifest)})"
    )
    print(
        f"Is status True? (video_status_from_manifest == True): {video_status_from_manifest == True}"  # Changed is to ==
    )
    print(f"Path from manifest: {video_download_path_from_manifest}")
    print(
        f"Is path notna? (pd.notna(video_download_path_from_manifest)): {pd.notna(video_download_path_from_manifest)}"
    )
    if (
        pd.notna(video_download_path_from_manifest)
        and str(video_download_path_from_manifest).strip()
    ):
        print(
            f"Does path exist? (os.path.exists(str(video_download_path_from_manifest))): {os.path.exists(str(video_download_path_from_manifest))}"
        )
    else:
        print(f"Path is NA, None, or empty; os.path.exists not checked.")
    print("--- End Video Download Cache Check ---\n")

    if not args.audio:
        if (
            not force_processing
            and video_status_from_manifest == True  # Changed is to ==
            and pd.notna(video_download_path_from_manifest)
            and str(video_download_path_from_manifest).strip()
            and os.path.exists(str(video_download_path_from_manifest))
        ):
            print(f"[CACHE] Using existing video: {video_download_path_from_manifest}")
            video_download_path_to_use = str(video_download_path_from_manifest)
        else:
            if video_status_from_manifest == True and (  # Changed is to ==
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

            target_stream = None
            if args.resolution == "highest":
                target_stream = yt.streams.get_highest_resolution()
            else:
                target_stream = yt.streams.filter(
                    res=args.resolution,
                    progressive=True,
                    file_extension="mp4",
                ).first()
            if not target_stream:
                print(
                    f"[INFO] No stream for res '{args.resolution}' (progressive, mp4). Trying any progressive mp4."
                )
                target_stream = (
                    yt.streams.filter(progressive=True, file_extension="mp4")
                    .order_by("resolution")
                    .desc()
                    .first()
                )
            if not target_stream:
                print(
                    f"[INFO] No progressive mp4 stream. Trying highest resolution adaptive mp4 video stream."
                )
                target_stream = (
                    yt.streams.filter(
                        adaptive=True, file_extension="mp4", only_video=True
                    )
                    .order_by("resolution")
                    .desc()
                    .first()
                )

            if target_stream:
                file_extension = target_stream.subtype
                if not file_extension:
                    if target_stream.mime_type and "/" in target_stream.mime_type:
                        file_extension = target_stream.mime_type.split("/")[-1]
                    else:
                        file_extension = "mp4"
                video_filename = f"{base_name_for_paths}.{file_extension}"
                os.makedirs(args.effective_video_dir, exist_ok=True)
                downloaded_path = target_stream.download(
                    output_path=args.effective_video_dir, filename=video_filename
                )
                print(f"[SUCCESS] Video downloaded: {downloaded_path}")
                video_download_path_to_use = os.path.abspath(downloaded_path)
                manifest_df = update_manifest_entry(
                    manifest_df,
                    canonical_url,
                    {
                        "video_path": video_download_path_to_use,
                        "status_video_downloaded": True,
                    },
                )
                entry = get_manifest_entry(manifest_df, canonical_url)  # Refresh entry
            else:
                print(
                    f"[ERROR] No suitable video stream found for {base_name_for_paths}. Skipping video download."
                )
                video_download_path_to_use = None
                manifest_df = update_manifest_entry(
                    manifest_df,
                    canonical_url,
                    {"video_path": pd.NA, "status_video_downloaded": False},
                )
                entry = get_manifest_entry(manifest_df, canonical_url)  # Refresh entry
            save_manifest(manifest_df, manifest_path)
    else:  # audio-only mode
        video_download_path_to_use = None
        if video_status_from_manifest != False or pd.notna(
            video_download_path_from_manifest
        ):  # Use != False to catch True or NA
            manifest_df = update_manifest_entry(
                manifest_df,
                canonical_url,
                {"video_path": pd.NA, "status_video_downloaded": False},
            )
            entry = get_manifest_entry(manifest_df, canonical_url)  # Refresh entry
            save_manifest(manifest_df, manifest_path)

    # --- 2. MP3 Conversion ---
    mp3_path_from_manifest = entry.get("mp3_path")
    mp3_status_from_manifest = entry.get("status_mp3_converted")
    needs_mp3 = args.audio or args.transcribe or args.viral_short_identifier
    mp3_file_for_processing = None

    if needs_mp3:
        print("\n--- MP3 Conversion Cache Check ---")
        print(f"URL: {canonical_url}")
        print(f"Force processing: {force_processing}")
        print(
            f"Status from manifest: {mp3_status_from_manifest} (type: {type(mp3_status_from_manifest)})"
        )
        print(
            f"Is status True? (mp3_status_from_manifest == True): {mp3_status_from_manifest == True}"  # Changed is to ==
        )
        print(f"MP3 path from manifest: {mp3_path_from_manifest}")
        print(
            f"Is path notna? (pd.notna(mp3_path_from_manifest)): {pd.notna(mp3_path_from_manifest)}"
        )
        if pd.notna(mp3_path_from_manifest) and str(mp3_path_from_manifest).strip():
            print(
                f"Does path exist? (os.path.exists(str(mp3_path_from_manifest))): {os.path.exists(str(mp3_path_from_manifest))}"
            )
        else:
            print(f"Path is NA, None, or empty; os.path.exists not checked.")
        print("--- End MP3 Conversion Cache Check ---\n")

        if (
            not force_processing
            and mp3_status_from_manifest == True  # Changed is to ==
            and pd.notna(mp3_path_from_manifest)
            and str(mp3_path_from_manifest).strip()
            and os.path.exists(str(mp3_path_from_manifest))
        ):
            print(f"[CACHE] Using existing MP3: {mp3_path_from_manifest}")
            mp3_file_for_processing = str(mp3_path_from_manifest)
        else:
            if mp3_status_from_manifest == True and (  # Changed is to ==
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
                not args.audio  # If not audio-only, video might exist
                and video_download_path_to_use  # video_download_path_to_use is from previous step (cached or downloaded)
                and os.path.exists(video_download_path_to_use)
            ):
                print(
                    f"[INFO] Using downloaded video as source for MP3: {video_download_path_to_use}"
                )
                source_for_ffmpeg = video_download_path_to_use
            else:
                print("[INFO] Downloading dedicated audio stream for MP3 conversion...")
                audio_stream = yt.streams.get_audio_only()
                if not audio_stream:
                    audio_stream = (
                        yt.streams.filter(only_audio=True)
                        .order_by("abr")
                        .desc()
                        .first()
                    )
                if audio_stream:
                    temp_audio_filename = f"{base_name_for_paths}_audiotemp.{audio_stream.subtype or 'mp4'}"
                    os.makedirs(args.effective_audio_dir, exist_ok=True)
                    raw_audio_input_path = audio_stream.download(
                        output_path=args.effective_audio_dir,
                        filename=temp_audio_filename,
                    )
                    print(f"[SUCCESS] Raw audio downloaded: {raw_audio_input_path}")
                    source_for_ffmpeg = raw_audio_input_path
                else:
                    print("[ERROR] No audio stream found for MP3 conversion.")
                    manifest_df = update_manifest_entry(
                        manifest_df,
                        canonical_url,
                        {"mp3_path": pd.NA, "status_mp3_converted": False},
                    )
                    entry = get_manifest_entry(
                        manifest_df, canonical_url
                    )  # Refresh entry

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
                entry = get_manifest_entry(manifest_df, canonical_url)  # Refresh entry
            save_manifest(manifest_df, manifest_path)
    elif mp3_status_from_manifest != False or pd.notna(mp3_path_from_manifest):
        manifest_df = update_manifest_entry(
            manifest_df,
            canonical_url,
            {"mp3_path": pd.NA, "status_mp3_converted": False},
        )
        entry = get_manifest_entry(manifest_df, canonical_url)  # Refresh entry
        save_manifest(manifest_df, manifest_path)

    # --- 3. Transcription ---
    transcript_content = None
    transcript_path_from_manifest = entry.get("transcript_path")
    transcript_status_from_manifest = entry.get("status_transcript_generated")
    needs_transcription = args.transcribe or args.viral_short_identifier

    if needs_transcription:
        print("\n--- Transcription Cache Check ---")
        print(f"URL: {canonical_url}")
        print(f"Force processing: {force_processing}")
        print(
            f"Status from manifest: {transcript_status_from_manifest} (type: {type(transcript_status_from_manifest)})"
        )
        print(
            f"Is status True? (transcript_status_from_manifest == True): {transcript_status_from_manifest == True}"  # Changed is to ==
        )
        print(f"Path from manifest: {transcript_path_from_manifest}")
        print(
            f"Is path notna? (pd.notna(transcript_path_from_manifest)): {pd.notna(transcript_path_from_manifest)}"
        )
        if (
            pd.notna(transcript_path_from_manifest)
            and str(transcript_path_from_manifest).strip()
        ):
            print(
                f"Does path exist? (os.path.exists(str(transcript_path_from_manifest))): {os.path.exists(str(transcript_path_from_manifest))}"
            )
        else:
            print(f"Path is NA, None, or empty; os.path.exists not checked.")
        print(
            f"MP3 available for processing: {mp3_file_for_processing if mp3_file_for_processing else 'No'}"
        )
        print("--- End Transcription Cache Check ---\n")

        if mp3_file_for_processing and os.path.exists(mp3_file_for_processing):
            if (
                not force_processing
                and transcript_status_from_manifest == True  # Changed is to ==
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
                    # Verify content, as empty transcript file might exist
                    if not transcript_content.strip():
                        print(
                            f"[WARNING] Cached transcript file {transcript_path_from_manifest} is empty. Will re-transcribe."
                        )
                        transcript_content = None  # Force re-transcription
                        # Optionally, mark status as False here if you want to be strict
                        manifest_df = update_manifest_entry(
                            manifest_df,
                            canonical_url,
                            {"status_transcript_generated": False},
                        )
                        entry = get_manifest_entry(
                            manifest_df, canonical_url
                        )  # Refresh entry

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
                    entry = get_manifest_entry(
                        manifest_df, canonical_url
                    )  # Refresh entry

            if (
                transcript_content is None
            ):  # Process if not loaded from cache or cache was invalid
                if transcript_status_from_manifest == True and (  # Changed is to ==
                    not pd.notna(transcript_path_from_manifest)
                    or not str(transcript_path_from_manifest).strip()
                    or not os.path.exists(str(transcript_path_from_manifest))
                    # or (transcript_content is not None and not transcript_content.strip()) # Covered by transcript_content is None now
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

                if transcript_content is not None:  # Gemini returned something
                    new_transcript_path = (
                        os.path.abspath(transcription_result["path"])
                        if transcription_result["path"]
                        and os.path.exists(transcription_result["path"])
                        else pd.NA
                    )
                    manifest_df = update_manifest_entry(
                        manifest_df,
                        canonical_url,
                        {
                            "transcript_path": new_transcript_path,
                            "status_transcript_generated": (
                                True
                                if pd.notna(new_transcript_path)
                                and transcript_content.strip()  # Status True only if path valid AND content exists
                                else False
                            ),
                        },
                    )
                else:  # Gemini failed
                    manifest_df = update_manifest_entry(
                        manifest_df,
                        canonical_url,
                        {
                            "transcript_path": pd.NA,
                            "status_transcript_generated": False,
                        },
                    )
                entry = get_manifest_entry(manifest_df, canonical_url)  # Refresh entry
                save_manifest(manifest_df, manifest_path)
        else:
            print(
                "[WARNING] MP3 not available or path invalid, skipping transcription."
            )
            if transcript_status_from_manifest != False or pd.notna(
                transcript_path_from_manifest
            ):
                manifest_df = update_manifest_entry(
                    manifest_df,
                    canonical_url,
                    {"transcript_path": pd.NA, "status_transcript_generated": False},
                )
                entry = get_manifest_entry(manifest_df, canonical_url)  # Refresh entry
                save_manifest(manifest_df, manifest_path)
    elif transcript_status_from_manifest != False or pd.notna(
        transcript_path_from_manifest
    ):
        manifest_df = update_manifest_entry(
            manifest_df,
            canonical_url,
            {"transcript_path": pd.NA, "status_transcript_generated": False},
        )
        entry = get_manifest_entry(manifest_df, canonical_url)  # Refresh entry
        save_manifest(manifest_df, manifest_path)

    # --- 4. Viral Clip Analysis ---
    analysis_path_from_manifest = entry.get("analysis_path")
    analysis_status_from_manifest = entry.get("status_analysis_generated")

    if args.viral_short_identifier:
        print("\n--- Viral Clip Analysis Cache Check ---")
        print(f"URL: {canonical_url}")
        print(f"Force processing: {force_processing}")
        print(
            f"Status from manifest: {analysis_status_from_manifest} (type: {type(analysis_status_from_manifest)})"
        )
        print(
            f"Is status True? (analysis_status_from_manifest == True): {analysis_status_from_manifest == True}"  # Changed is to ==
        )
        print(f"Path from manifest: {analysis_path_from_manifest}")
        print(
            f"Is path notna? (pd.notna(analysis_path_from_manifest)): {pd.notna(analysis_path_from_manifest)}"
        )
        if (
            pd.notna(analysis_path_from_manifest)
            and str(analysis_path_from_manifest).strip()
        ):
            print(
                f"Does path exist? (os.path.exists(str(analysis_path_from_manifest))): {os.path.exists(str(analysis_path_from_manifest))}"
            )
        else:
            print(f"Path is NA, None, or empty; os.path.exists not checked.")
        print(
            f"Transcript content available: {'Yes' if transcript_content and transcript_content.strip() else 'No'}"
        )
        print("--- End Viral Clip Analysis Cache Check ---\n")

        cached_analysis_valid_and_present = False
        if (
            not force_processing
            and analysis_status_from_manifest == True  # Changed is to ==
            and pd.notna(analysis_path_from_manifest)
            and str(analysis_path_from_manifest).strip()
            and os.path.exists(str(analysis_path_from_manifest))
        ):
            # Additionally check if analysis file is non-empty
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
                    # Optionally mark status as False here
                    manifest_df = update_manifest_entry(
                        manifest_df, canonical_url, {"status_analysis_generated": False}
                    )
                    entry = get_manifest_entry(
                        manifest_df, canonical_url
                    )  # Refresh entry
            except OSError:
                print(
                    f"[WARNING] Could not check size of cached analysis file {analysis_path_from_manifest}. Assuming invalid."
                )

        if transcript_content and transcript_content.strip():
            if not cached_analysis_valid_and_present:
                if analysis_status_from_manifest == True and (  # Changed is to ==
                    not pd.notna(analysis_path_from_manifest)
                    or not str(analysis_path_from_manifest).strip()
                    or not os.path.exists(str(analysis_path_from_manifest))
                    # or (cached_analysis_valid_and_present was False due to empty file)
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
                    transcript_content,
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
                        pass  # Keep analysis_content_exists as False

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
                entry = get_manifest_entry(manifest_df, canonical_url)  # Refresh entry
                save_manifest(manifest_df, manifest_path)
        else:  # Transcript not available
            print(
                "[WARNING] Transcript not available or empty, skipping viral clip analysis."
            )
            if analysis_status_from_manifest != False or pd.notna(
                analysis_path_from_manifest
            ):
                manifest_df = update_manifest_entry(
                    manifest_df,
                    canonical_url,
                    {"analysis_path": pd.NA, "status_analysis_generated": False},
                )
                entry = get_manifest_entry(manifest_df, canonical_url)  # Refresh entry
                save_manifest(manifest_df, manifest_path)
    elif analysis_status_from_manifest != False or pd.notna(
        analysis_path_from_manifest
    ):
        manifest_df = update_manifest_entry(
            manifest_df,
            canonical_url,
            {"analysis_path": pd.NA, "status_analysis_generated": False},
        )
        entry = get_manifest_entry(manifest_df, canonical_url)  # Refresh entry
        save_manifest(manifest_df, manifest_path)

    print(f"[INFO] Processing for {canonical_url} complete.")
    return manifest_df


# --- Manage Command Handlers ---
def handle_remove_url(url_to_remove_input, manifest_df, manifest_path):
    try:
        yt_remove = YouTube(url_to_remove_input)
        url_to_remove_canonical = yt_remove.watch_url
        print(
            f"[INFO] Attempting to remove canonical URL: {url_to_remove_canonical} (from input {url_to_remove_input})"
        )
    except Exception:
        print(
            f"[WARNING] Could not get canonical URL for '{url_to_remove_input}'. Trying to remove as is."
        )
        url_to_remove_canonical = url_to_remove_input

    entry = get_manifest_entry(manifest_df, url_to_remove_canonical)
    if entry is None:
        if url_to_remove_canonical != url_to_remove_input:
            print(
                f"[INFO] Canonical URL '{url_to_remove_canonical}' not found. Trying original input '{url_to_remove_input}'."
            )
            entry = get_manifest_entry(manifest_df, url_to_remove_input)
            if entry is None:
                print(
                    f"[INFO] URL not found in manifest (tried canonical and original): {url_to_remove_input}"
                )
                return manifest_df
            else:
                url_to_remove_canonical = url_to_remove_input
        else:
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
        elif pd.notna(file_path_obj):
            print(
                f"[INFO] Path in manifest was present but empty or invalid: '{file_path_obj}'"
            )

    manifest_df = manifest_df[
        manifest_df["youtube_url"] != url_to_remove_canonical
    ].reset_index(drop=True)
    print(f"[SUCCESS] Removed entry for {url_to_remove_canonical} from manifest.")
    return manifest_df


def handle_list_manifest(manifest_df):
    if manifest_df.empty:
        print("[INFO] Manifest is empty.")
        return
    print("\n--- Processing Manifest (Top 20 rows) ---")
    # To prevent truncation in display for long paths
    with pd.option_context(
        "display.max_colwidth", None, "display.width", 1000, "display.max_rows", 25
    ):
        print(manifest_df.head(20).to_string())
    print(f"--- Total entries: {len(manifest_df)} ---")
    print("\n--- Manifest Dtypes ---")
    print(manifest_df.dtypes)
    print("--- End of Manifest ---\n")


# --- Main Function ---
def main():
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
    list_parser = manage_subparsers.add_parser(
        "list", help="List all entries in the manifest"
    )

    args = parser.parse_args()

    if (hasattr(args, "transcribe") and args.transcribe) or (
        hasattr(args, "viral_short_identifier") and args.viral_short_identifier
    ):
        if not os.environ.get("GOOGLE_API_KEY"):
            print(
                "[ERROR] GOOGLE_API_KEY environment variable is not set. Required for transcription/analysis."
            )

    manifest_df = load_manifest(args.manifest_file)
    print("--- Manifest Dtypes after initial load ---")
    print(
        manifest_df.dtypes
        if not manifest_df.empty
        else "Manifest is empty, dtypes not applicable yet."
    )

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

        manifest_df = process_youtube_url(args, manifest_df, args.manifest_file)
        # Final save is now inside process_youtube_url after each major step,
        # but an overall final save can still be useful.
        save_manifest(manifest_df, args.manifest_file)
        print(f"[INFO] Final manifest saved to {args.manifest_file}")

    elif args.command_name == "manage":
        if args.manage_action == "remove":
            manifest_df = handle_remove_url(args.url, manifest_df, args.manifest_file)
        elif args.manage_action == "list":
            handle_list_manifest(manifest_df)
        save_manifest(manifest_df, args.manifest_file)
        print(
            f"[INFO] Final manifest saved to {args.manifest_file} after manage operation."
        )


if __name__ == "__main__":
    main()
