import os
import pandas as pd
from datetime import datetime

from processors.base import Colors

# --- Manifest Constants ---
MANIFEST_COLUMNS = [
    "youtube_url",
    "base_filename",
    "video_path",
    "mp3_path",
    "transcript_path",
    "analysis_path",
    "caption_srt_path",
    "caption_vtt_path",
    "caption_txt_path",
    "status_video_downloaded",
    "status_mp3_converted",
    "status_transcript_generated",
    "status_analysis_generated",
    "status_captions_generated",
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
                "status_captions_generated",
            ]
            for col_name in bool_status_cols:
                if col_name in df.columns:
                    try:
                        df[col_name] = df[col_name].astype(pd.BooleanDtype())
                    except Exception as e_astype:
                        print(
                            f"{Colors.ERROR}[ERROR]{Colors.RESET} load_manifest: Failed to convert column '{col_name}' to BooleanDtype. Error: {e_astype}"
                        )
                        print(
                            f"         Unique values in column '{col_name}' before error: {df[col_name].unique()[:10]}"
                        )
                else:  # If column was just added
                    df[col_name] = pd.Series([pd.NA] * len(df), dtype=pd.BooleanDtype())

            path_cols = ["video_path", "mp3_path", "transcript_path", "analysis_path", "caption_srt_path", "caption_vtt_path", "caption_txt_path"]
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
            print(f"{Colors.WARNING}[WARNING]{Colors.RESET} Manifest file {manifest_path} is empty. Starting fresh.")
        except Exception as e:
            print(
                f"{Colors.ERROR}[ERROR]{Colors.RESET} Could not load manifest {manifest_path}: {e}. Starting fresh."
            )
            import traceback

            traceback.print_exc()

    print(
        f"{Colors.INFO}[INFO]{Colors.RESET} Creating a new manifest structure as {manifest_path} does not exist or failed to load."
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
        print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Could not save manifest to {manifest_path}: {e}")


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
                    f"{Colors.ERROR}[ERROR]{Colors.RESET} update_manifest_entry (update): Failed to set {key}={value} (type: {type(value)}) for URL {url_key}. Error: {e}"
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
                            f"{Colors.WARNING}[WARNING]{Colors.RESET} update_manifest_entry (add): Could not astype column '{col}' for new entry. Error: {e_astype_concat}. Value: {new_row_df[col].iloc[0]}, Target Dtype: {df[col].dtype}"
                        )
                        # Fallback: if astype fails, try to proceed; concat might still work or give a more specific error
                # If a column from df is not in new_row_df (shouldn't happen if new_entry_data has all MANIFEST_COLUMNS)
                # it will be pd.NA in the new row when concatenated, which is fine.

            df = pd.concat([df, new_row_df], ignore_index=True)
        except Exception as e:
            print(
                f"{Colors.ERROR}[ERROR]{Colors.RESET} update_manifest_entry (add): Failed to concat new entry for URL {url_key}. Error: {e}"
            )
            print(f"       New entry data: {new_entry_data}")
            print(f"       Main df dtypes: \n{df.dtypes}")
            import traceback

            traceback.print_exc()
    return df