import os
import google.generativeai as genai

# --- Gemini Interaction Functions ---

def get_viral_clip_identifier_prompt_text(transcript_text, number_of_sections): # Renamed to avoid conflict if we later import the original prompts.py for some reason
    """
    Generates the prompt text for identifying viral clips using a detailed template.
    The number of sections and transcript are injected into the template.
    """
    prompt_template = """
    You are an Expert Short-Form Video Editor and Viral Content Strategist. Your mission is to analyze the provided YouTube video transcript and identify segments that can be directly trimmed into highly engaging, viral-potential short-form videos (like Instagram Reels, TikToks, or YouTube Shorts), each between 30 and 50 seconds in length.
    Your selections must be optimized for maximum public appeal and content retention, meaning they should be compelling enough to make viewers watch the entire clip and eager to share. Leverage your vast knowledge base on what makes short-form content captivating and shareable.
    Here are the critical criteria for identifying each segment:
    Viral Potential & Public Appeal:
    Emotional Resonance: Does the segment evoke strong emotions? (e.g., humor, awe, surprise, curiosity, inspiration, relatability, empathy, satisfaction, mild outrage/controversy that sparks discussion).
    "Aha!" or "Wow!" Moments: Does it contain a surprising reveal, a brilliant insight, a mind-blowing fact, or an exceptionally clever point?
    Relatability: Does it touch upon a common experience, struggle, or thought that a wide audience can connect with?
    Value Proposition (Quick Win): Does it offer a quick, valuable tip, hack, piece of advice, or a solution to a common problem that can be understood and appreciated within the time limit?
    Storytelling Nugget: Is there a mini-story with a clear hook, rising action, and a punchline/resolution/cliffhanger within the segment?
    Uniqueness/Novelty: Is the content, idea, or presentation fresh, unexpected, or a unique take on a common topic?
    Visually Suggestive (Even from Text): Does the dialogue describe or imply something visually interesting, a transformation, a dynamic action, or a strong facial expression that would translate well to video?
    Content Retention & Compelling Narrative (within 30-50 seconds):
    Strong Hook (First 1-3 seconds): The segment must start with something immediately gripping – a provocative question, a bold statement, an intriguing premise, or a visual/auditory cue (inferred from text).
    Clear, Concise Message: The core idea of the segment must be easily digestible. Avoid overly complex or jargon-filled sections unless the jargon itself is part of the hook or explanation.
    Build & Payoff: Even in a short clip, there should be a sense of progression. It should build anticipation or develop an idea and then deliver a payoff (e.g., the answer, the result, the punchline, the key takeaway).
    Satisfying Loop (Optional but good): Does the end make you want to rewatch it immediately, or does it resolve satisfyingly?
    No Dead Air/Fluff: The segment should be packed with value or entertainment. Every second counts. Identify if any small phrases within the potential segment could be trimmed for even tighter pacing.
    Technical & Structural Requirements:
    Segment Length: Strictly 30-50 seconds. Use word count or sentence structure to estimate. (Assume average speaking pace of 2-3 words per second).
    Standalone Cohesion: The segment must make sense on its own, without requiring extensive context from the rest of the video.
    Clear Start & End Points: Identify precise start and end phrases/sentences for seamless trimming.
    Number of Sections: {number_of_sections_placeholder}

    Output Format for Each Identified Segment:
    Please provide your findings in the following format for EACH identified segment:
    Generated code
    **Segment [Number]**
    *   **Estimated Duration:** [e.g., ~40 seconds]
    *   **Start Cue (Phrase/Sentence):** "[Exact starting phrase/sentence of the segment]"
    *   **End Cue (Phrase/Sentence):** "[Exact ending phrase/sentence of the segment]"
    *   **Transcript of Segment:**
        "[Paste the full text of the identified segment here]"
    *   **Justification for Virality & Retention (linking to criteria):**
        *   **Hook:** [Explain what makes the first few seconds grab attention]
        *   **Core Appeal:** [Explain the primary reason this segment is compelling - e.g., emotional impact, value, humor, surprise, relatability]
        *   **Payoff/Conclusion:** [Explain how the segment resolves or delivers value effectively within the timeframe]
        *   **Why it will keep people watching:** [Specific elements that contribute to retention for this clip]
    *   **Potential Viral Angle/Headline Idea (Optional but helpful):** [e.g., "You WON'T BELIEVE what happens next!" or "The #1 Mistake People Make When..."]
    Your ultimate objective is to provide me with ready-to-trim goldmines from my transcript that have the highest probability of becoming highly watchable, shareable, and viral short-form content.
    Now, please analyze the following YouTube video transcript:

    \"\"\"
    {youtube_transcript_placeholder}
    \"\"\"

    Key considerations for you, the AI, when processing:
    Inferring from Text: Since you only have text, you'll need to infer pacing, emphasis, and potential visual accompaniments based on the language used.
    Prioritization: If there are many potential segments, prioritize those with the strongest combination of the criteria above.
    Conciseness: Even your justifications should be concise but informative.
    This prompt is designed to be very specific to guide the AI towards the desired outcome. Good luck!
    """

    num_sections_str = (
        f"{number_of_sections}"
        if number_of_sections
        else "[Default to 3-5, or choose a number you deem appropriate based on transcript quality and length, e.g., '3 to 5']"
    )

    number_of_sections_placeholder_text = (
        f"please identify {num_sections_str} of the most promising segments."
    )

    return prompt_template.format(
        number_of_sections_placeholder=number_of_sections_placeholder_text,
        youtube_transcript_placeholder=transcript_text,
    )


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
                    # This was a granular log, already commented out.
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
        traceback.print_exc() # Keep traceback for debugging errors with Gemini API
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
        prompt = get_viral_clip_identifier_prompt_text(transcript_text, number_of_sections)
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
                    # This was a granular log, already commented out.
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
            return analysis_file_path  # Return path even if content is empty, manifest status will reflect this

    except Exception as e:
        print(f"[ERROR] Gemini viral clip ID failed: {e}")
        import traceback
        traceback.print_exc() # Keep traceback for debugging errors with Gemini API
        return None
