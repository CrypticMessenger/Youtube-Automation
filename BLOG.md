# I built Goliath–YT Automation engine and now it's worth nothing…

**Goliath — My Brainchild was dead… Just like that…**

🪦 **Github**: [https://github.com/CrypticMessenger/Youtube-Automation](https://github.com/CrypticMessenger/Youtube-Automation)  
💀 **Abandoned Frontend** (that never met its backend): [https://azimuth-ashen.vercel.app/](https://azimuth-ashen.vercel.app/)

---

## The Birth of an Idea

It started, as many projects do, with a simple, ambitious idea. I wanted to build a fully automated system that could take long-form content, like podcasts, and intelligently carve out the most engaging, viral-worthy clips for YouTube Shorts.

The dream was to create a content machine — a digital titan that could feed the insatiable appetite of the short-form video world.

> **$4.20/month for a `yt-dlp` wrapper lmao** — people were willing to pay, BTW.

---

## Market Research on the Idea

### Functional Requirements

The plan was to create a system that could:

1. Download a YouTube video  
2. Transcribe the entire audio track with precise timestamps  
3. Use an AI model to analyze the transcript and identify sections with the highest potential for virality — the jokes, the profound statements, the "aha!" moments  
4. Automatically clip those sections  
5. Burn the captions directly onto the video for maximum engagement **[Added Value]**  
6. Upload these polished, perfectly-packaged shorts directly to YouTube via a Scheduler **[Added Value]**

### Non-Functional Requirements

- Processing of 1-hour videos should not take more than 3 minutes

---

**_July 4th, 2025, 2:50 AM:_**  
*In the quiet hum of my computer, Goliath was born.*

---

## Internal Machinery

Goliath was designed as an orchestration engine. I built a Directed Acyclic Graph (DAG) to manage the workflow, ensuring each step ran in perfect order, caching results to be as efficient as possible.

### DAG Workflow – Key Design Choices

#### 1. Aggressive File-Based Caching

Every operation — from downloading a video to generating a transcript — was treated as a distinct step in the pipeline. The state of each step was meticulously tracked in a central manifest file.

This meant that if you ran the process on a video, and then later asked for different clips, the system was smart enough to avoid re-downloading or re-transcribing the source. It simply picked up from the last completed step.

> This made the system **resilient** and **incredibly fast** on subsequent runs.

---

#### 2. The Power of `stable-ts` for Accurate Timestamps

A core challenge was getting reliable, **word-level timestamps**. Most transcription services only offer sentence- or phrase-level timing.

That’s where `stable-ts` came in.

- Transcription was done 100% **locally**  
- It took **only ~8–9 seconds** for a **30-minute video**  
- Output: word-level timestamps, perfectly precise

> *(DO YOU KNOW PEOPLE PAY FOR THESE SERVICES!?)*

This allowed me to surgically identify the *exact* start and end points of viral moments. Final clips were perfectly timed and captions synced to audio.

---

#### 3. Optimized Clipping and Burning

Video manipulation was the most expensive part.

- My naive approach: burn captions on the **entire** video, then clip — **painfully slow**
- Optimized approach: **clip first**, then overlay .srt captions using `ffmpeg`  
- Result: **processing time dropped from minutes to seconds**

> A simple change — but the key to making the entire system scalable.

---

## The Sobering Reality

A recent announcement from the YouTube CEO claimed:

> **As of 2025, YouTube Shorts is bagging over 200 Billion views every day.**

### Let’s break that down:

- **200 billion views/day**  
- **~25 seconds per view**

200,000,000,000 views/day × 25 seconds = 5,000,000,000,000 seconds/day
→ 5T seconds ÷ 3600 = ~1.39 billion hours/day on Shorts


### Now compare that to humanity's waking hours:

- **Global population ≈ 8B**  
- **16 waking hours/day → 8B × 16 = 128B waking hours/day**

### So…

> **1.39B / 128B = ~1.08%**

**Humanity spends ~1% of all waking hours watching Shorts. One percent.**

---

I was, in essence, building a more efficient factory for digital junk food.

**Goliath — a tool that could push that number even higher.**

Was I contributing? Or just adding to the noise?

Goliath was becoming a net-negative contribution to society — but mind you — it **WAS** a money-making machine!

---

## The Killing Blow

Turns out, I didn’t need to wrestle with that moral dilemma for long. The decision was made for me.

> **As of July 15, 2025 — YouTube updated its guidelines** to better identify mass-produced, repetitious, inauthentic content.

➡️ [Link to policy change]

Just like that — **Goliath was slain.**

All that work. All that code. All that ambition… **rendered worthless in an instant.**

> In the biblical narrative, Goliath was killed by David — a shepherd with a sling and a stone.  
> **I built Goliath. YouTube became David.**

---

## The Aftermath

Maybe YouTube did me — and all of us — a favor.

Perhaps the universe has a funny way of course-correcting.

My project, Goliath, is dead.

The code now sits silently on my hard drive — a **monument to a failed idea.**

> Remember: I have to go on till X–1 more times before definite success.

**The automation engine is worth nothing now.**  
But maybe the **lesson** is worth everything.
