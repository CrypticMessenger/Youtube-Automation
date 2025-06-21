## 1. Youtube video clipper - to create reels from a youtube video

theme like: Youtube video clipper to create reels from a youtube video

- [] Figure out possible way to automate the process via telegram bot
- [x] Figure out way to download youtube videos
- [x] Figure out way to download youtube videos audio
- [x] Figure out way to download youtube videos transcripts
- [] Figure out a prompt to find the most plasible parts of the video that are likely to be userful as a reel (max 30-50 seconds)
  - [] does sending audio/video will help in finding the most plausible parts of the video? or transcript is enough?
  - [] Transcription currently consists only transcription, without timestamps, so we need to figure out a way to get the timestamps for the transcription
- [] Figure out a way to automatically clip the video based on the prompt and save the clips

## 2. Entirely new Youtube reel creator

theme like : Docker under 60 seconds etc.

- [] Given an input, Figure out a way to generate script for the youtube reel ( max 60 seconds)
- [] Investigate if there is a way to generate a human voice over for the script
- [] Figure out a way to generate a video for the script (if possible - might require manual effort for now)

## Common launch readiness tasks

- [] Figure out a way to display capations on the video clip as overlay subtitles. (might require manual effort for now - high stimulation videos have more retention)
- [] Figure out a way to upload the clips to youtube as reels - might have to use n8n for this or not.
- [] Figure out a way to generate a thumbnail for the video clip
- [] Figure out a way to generate a title for the video clip
- [] Figure out a way to generate a description for the video clip
- [] Figure out a way to generate hashtags for the video clip

## Good to have

- [] Add Human-in-the-loop for the script selection/upload step via telegram bot

---

## TODO

## Idea generator from reddit

## Twitter Account Automator

## Medium Article Automator

## LinkedIn Post Automator

---

```
python3 main.py process "https://youtu.be/jwr1EOvAxQI\?si\=_ZBOy2GzaUdV7jUz" \
    --output "/Users/ambrose_/Desktop/exploration/ProjectGoliathYoutubeAutomation" \
    --transcribe \
    --viral-short-identifier
```
