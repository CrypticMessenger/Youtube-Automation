# YouTube Video Processing Toolkit

This project provides a command-line toolkit to download, process, and analyze YouTube videos. It can download videos or audio, transcribe audio content using Google Gemini, and identify potential viral clips from the transcripts.

## Features

*   **YouTube Video/Audio Downloading**:
    *   Download videos at specified resolutions or the highest available.
    *   Download audio-only in MP3 format.
    *   Specify custom output directories and filenames.
*   **Audio Transcription**:
    *   Transcribe audio content from downloaded videos/audio using Google Gemini models.
    *   Save transcripts as `.txt` files.
*   **Viral Clip Identification**:
    *   Analyze transcripts to identify sections with high potential to be engaging or viral short clips.
    *   Uses Google Gemini models for analysis.
*   **Processing Manifest**:
    *   Keeps track of processed URLs and their associated files (video, audio, transcript, analysis) in a CSV manifest (`processing_manifest.csv`).
    *   Supports caching: avoids re-processing already completed steps unless forced.
    *   Manage the manifest by listing entries or removing specific URLs and their associated files.
*   **Flexible Output Configuration**:
    *   Specify base output directory.
    *   Set custom directories for videos, audios, transcripts, and analysis files.

## Installation

1.  **Prerequisites**:
    *   Python 3.x
    *   FFmpeg: Ensure FFmpeg is installed and accessible in your system's PATH. It's required for audio extraction and MP3 conversion. You can download it from [ffmpeg.org](https://ffmpeg.org/download.html).

2.  **Clone the Repository (if applicable)**:
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

3.  **Set up a Virtual Environment (Recommended)**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

4.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

5.  **Set Environment Variables**:
    *   For transcription and viral clip identification features, you need a Google API Key.
    *   Set the `GOOGLE_API_KEY` environment variable:
        ```bash
        export GOOGLE_API_KEY="YOUR_API_KEY"
        ```
        (On Windows, use `set GOOGLE_API_KEY="YOUR_API_KEY"` for the current session, or set it permanently via system properties.)

## Usage

The script `main.py` is the entry point for all operations. It has two main subcommands: `process`, `manage` and `generate`.

### `process` Command

Use the `process` command to download and analyze a YouTube video.

**Syntax**:

```bash
python3 main.py process <youtube_url> [options]
```

**Arguments & Options**:

*   `url`: (Required) The YouTube video URL to process.
*   `-o, --output <directory>`: Base output directory for all generated files (default: current directory).
*   `-f, --filename <name>`: Custom base filename (no extension) for downloaded files. Defaults to a sanitized version of the video title.
*   `-r, --resolution <res>`: Video resolution (e.g., `720p`, `1080p`, `highest`). Defaults to `highest`.
*   `-a, --audio`: Download audio-only (MP3 format). If specified, no video file will be downloaded.
*   `--audio-dir <directory>`: Specific directory for audio files (default: `<output_dir>/audios`).
*   `--video-dir <directory>`: Specific directory for video files (default: `<output_dir>/videos`).
*   `--transcript-dir <directory>`: Specific directory for transcript files (default: `<output_dir>/transcripts`).
*   `--analysis-dir <directory>`: Specific directory for analysis files (default: `<output_dir>/viral_analysis`).
*   `--transcribe`: Transcribe the audio and save it as a `.txt` file. (Requires `GOOGLE_API_KEY`).
*   `--gemini-model <model_name>`: Gemini model to use for transcription (default: `gemini-1.5-flash-latest`).
*   `--viral-short-identifier`: Identify potential viral short clips from the transcript. (Requires `GOOGLE_API_KEY`).
*   `--number-of-sections <count>`: Number of viral sections for the AI to find (e.g., `3`, `5`).
*   `--clip-identifier-model <model_name>`: Gemini model for clip identification (default: `gemini-2.5-flash`).
*   `--generate-captions`: Generate caption files (.srt, .ass) using `stable-whisper`.
*   `--whisper-model <model_name>`: Whisper model to use for caption generation (e.g., `small`, `base`, `medium`, `large`). Defaults to `small`.
*   `--caption-dir <directory>`: Specific directory for caption files (default: `<output_dir>/captions`).
*   `--force`: Force re-processing of all steps, ignoring any cached files or statuses in the manifest.
*   `--manifest-file <path>`: Path to the processing manifest CSV file (default: `processing_manifest.csv`).

**Examples**:

1.  **Download video, transcribe, and identify viral clips**:
    ```bash
    python3 main.py process "https://www.youtube.com/watch?v=your_video_id" \
        --output "./my_youtube_projects" \
        --transcribe \
        --viral-short-identifier \
        --number-of-sections 3
    ```

2.  **Download audio-only and save to a specific directory**:
    ```bash
    python3 main.py process "https://www.youtube.com/watch?v=your_video_id" \
        --audio \
        --audio-dir "./downloaded_mp3s"
    ```

3.  **Download video at 720p resolution with a custom filename**:
    ```bash
    python3 main.py process "https://www.youtube.com/watch?v=your_video_id" \
        --resolution "720p" \
        --filename "custom_video_name" \
        --output "./videos"
    ```

### `manage` Command

Use the `manage` command to interact with the processing manifest.

**Syntax**:

```bash
python3 main.py manage <action> [options]
```

**Actions**:

*   **`list`**: Lists all entries currently in the manifest.
    ```bash
    python3 main.py manage list
    ```
*   **`remove <youtube_url>`**: Removes a specific YouTube URL and its associated downloaded files (video, audio, transcript, analysis) from the manifest and the filesystem.
    ```bash
    python3 main.py manage remove "https://www.youtube.com/watch?v=some_old_video_id"
    ```

### `generate` Command

Use the `generate` command to create a video with hardcoded captions, using the data stored in the manifest. The output video will be saved in the `captioned_videos` directory with a `_captioned.mp4` suffix.

**Syntax**:

```bash
python3 main.py generate <youtube_url>
```

**Arguments & Options**:

*   `url`: (Required) The YouTube video URL. This must match an entry in the manifest that has already been processed with the `--generate-captions` flag.

**Example**:

1.  **Generate a video with captions**:
    First, ensure the video has been processed (e.g., with `--generate-captions`). Then, run:
    ```bash
    python3 main.py generate "https://www.youtube.com/watch?v=your_video_id"
    ```
    This will create a file in the `captioned_videos` directory with a name like `your_video_title_captioned.mp4`.

**Options for `manage` command**:
*   `--manifest-file <path>`: Path to the processing manifest CSV file (default: `processing_manifest.csv`).

### Processing a New YouTube Video

To process a brand new YouTube video from start to finish, including downloading, transcribing, identifying viral clips, generating captions, and creating a captioned video, follow these steps:

1.  **Process the video with transcription, viral clip identification, and caption generation**:
    This command will download the video, transcribe its audio, identify potential viral sections, and generate caption files. Replace `"https://www.youtube.com/watch?v=your_video_id"` with the actual YouTube URL and adjust the `--output` directory as needed.

    ```bash
    python3 main.py process "https://www.youtube.com/watch?v=your_video_id" \
        --output "./processed_videos" \
        --transcribe \
        --viral-short-identifier \
        --number-of-sections 3 \
        --generate-captions
    ```

    **Expected Results**:
    *   **Video File**: The downloaded video will be saved in `./processed_videos/videos/` (e.g., `your_video_title.mp4`).
    *   **Audio File**: The extracted audio will be in `./processed_videos/audios/` (e.g., `your_video_title.mp3`).
    *   **Transcript File**: The transcript will be in `./processed_videos/transcripts/` (e.g., `your_video_title.txt`).
    *   **Viral Analysis**: The viral clip analysis will be in `./processed_videos/viral_analysis/` (e.g., `your_video_title_viral_analysis.json`).
    *   **Caption Files**: The generated `.srt` and `.ass` caption files will be in `./processed_videos/captions/` (e.g., `your_video_title.srt`, `your_video_title.ass`).
    *   **Manifest Entry**: An entry for this video will be added to `processing_manifest.csv`.

2.  **Generate the captioned video**:
    Once the processing in step 1 is complete, you can generate a new video with hardcoded captions using the `generate` command.

    ```bash
    python3 main.py generate "https://www.youtube.com/watch?v=your_video_id"
    ```

    **Expected Results**:
    *   **Captioned Video File**: The final video with hardcoded captions will be saved in the `captioned_videos/` directory at the project root (e.g., `captioned_videos/your_video_title_captioned.mp4`).

    You can find all generated files in their respective directories as specified above, relative to your chosen `--output` directory (or the current directory if not specified). The `processing_manifest.csv` file will keep a record of all processed URLs and their associated file paths.



## Implementation Plan / TODOs

This section outlines planned enhancements and future project ideas.

### Youtube Video Clipper Enhancements (Current Project)

*   [ ] Figure out possible way to automate the process via telegram bot
*   [x] Figure out way to download youtube videos
*   [x] Figure out way to download youtube videos audio
*   [x] Figure out way to download youtube videos transcripts
*   [x] Figure out a prompt to find the most plausible parts of the video that are likely to be useful as a reel (max 30-50 seconds)
    *   [ ] Does sending audio/video will help in finding the most plausible parts of the video? or transcript is enough?
    *   [ ] Transcription currently consists only transcription, without timestamps, so we need to figure out a way to get the timestamps for the transcription (e.g., investigate Gemini's capabilities for timestamped transcription or integrate a library like `stable-ts` or `whisperX`).
        *   **Note:** An alternative for generating timestamped captions is to use OpenAI's Whisper CLI. After generating an MP3, you can run `whisper <audio_path>/<audio>.mp3 --model small` to get `.srt`, `.vtt`, and other caption files with word-level timestamps.
*   [ ] Figure out a way to automatically clip the video based on the prompt and save the clips (e.g., using FFmpeg with timestamps).

### New Youtube Reel Creator (Future Project Idea)

Theme like: Docker under 60 seconds etc.

*   [ ] Given an input, Figure out a way to generate script for the youtube reel (max 60 seconds)
*   [ ] Investigate if there is a way to generate a human voice over for the script
*   [ ] Figure out a way to generate a video for the script (if possible - might require manual effort for now)

### Common Features & Launch Readiness

*   [ ] Figure out a way to display captions on the video clip as overlay subtitles. (might require manual effort for now - high stimulation videos have more retention, investigate FFmpeg's subtitle capabilities or libraries like `moviepy`).
*   [ ] Figure out a way to upload the clips to youtube as reels - might have to use n8n for this or not.
*   [ ] Figure out a way to generate a thumbnail for the video clip
*   [ ] Figure out a way to generate a title for the video clip
*   [ ] Figure out a way to generate a description for the video clip
*   [ ] Figure out a way to generate hashtags for the video clip

### Good to Have

*   [ ] Add Human-in-the-loop for the script selection/upload step via telegram bot

---

### Other Ideas (Unrelated to current YouTube tools)

*   [ ] Idea generator from reddit
*   [ ] Twitter Account Automator
*   [ ] Medium Article Automator
*   [ ] LinkedIn Post Automator
---
