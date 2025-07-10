import os
import google.generativeai as genai
import json
import re

from processors.base import Colors

# --- Gemini Interaction Functions ---

def get_viral_clip_identifier_prompt_text(transcript_text, number_of_sections, niche_prompt=None): # Renamed to avoid conflict if we later import the original prompts.py for some reason
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
    Clear Start & End Points: Identify precise start & end phrases/sentences for seamless trimming.
    Number of Sections: {number_of_sections_placeholder}

    {niche_prompt_section_placeholder}

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
    {transcript_text}
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


    niche_section_text = ""
    if niche_prompt and niche_prompt.strip():
        niche_section_text = f"Additionally, consider the following niche focus for identifying clips: {niche_prompt}\n"

    return prompt_template.format(
        number_of_sections_placeholder=number_of_sections_placeholder_text,
        transcript_text=transcript_text,
        niche_prompt_section_placeholder=niche_section_text,
    )




def identify_viral_clips_gemini(
    transcript_text, number_of_sections, model_name, analysis_output_dir, base_filename, niche_prompt=None
):
    if not transcript_text or not transcript_text.strip():
        print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Transcript text is empty for viral clip ID.")
        return None

    print(f"{Colors.INFO}[INFO]{Colors.RESET} Identifying viral clips with {model_name}...")
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print(f"{Colors.ERROR}[ERROR]{Colors.RESET} GOOGLE_API_KEY not set.")
        return None

    analysis_file_path = None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name=model_name)
        prompt = get_viral_clip_identifier_prompt_text(transcript_text, number_of_sections, niche_prompt)
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
                    f"{Colors.ERROR}[ERROR]{Colors.RESET} Parsing Gemini response candidates for analysis: {e_parse}"
                )

        analysis_text_to_save = analysis_text.strip() if analysis_text else ""

        os.makedirs(analysis_output_dir, exist_ok=True)
        analysis_file_name = f"{base_filename}_viral_clips_analysis.txt"
        analysis_file_path = os.path.join(analysis_output_dir, analysis_file_name)
        with open(analysis_file_path, "w", encoding="utf-8") as f:
            f.write(analysis_text_to_save)

        if analysis_text_to_save:
            print(f"{Colors.SUCCESS}[SUCCESS]{Colors.RESET} Viral clip analysis saved to: {analysis_file_path}")
            return analysis_file_path
        else:
            print(f"{Colors.WARNING}[WARNING]{Colors.RESET} Empty viral clip analysis saved: {analysis_file_path}")
            return analysis_file_path  # Return path even if content is empty, manifest status will reflect this

    except Exception as e:
        print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Gemini viral clip ID failed: {e}")
        import traceback
        traceback.print_exc() # Keep traceback for debugging errors with Gemini API
        return None

def get_viral_timestamps_prompt_text(srt_content, analysis_content):
    """
    Generates the prompt for extracting viral timestamps from SRT and analysis text.
    """
    prompt_template = """
    You are a precise Video Editor AI. Your task is to analyze the provided SRT file content and a viral clip analysis text.
    Based on the analysis, identify the exact start and end timestamps for each viral segment identified in the analysis.

    The output MUST be a JSON object containing a list of segments. Each segment object must have "start_time" and "end_time" keys.

    Example Output:
    ```json
    {{
      "segments": [
        {{
          "start_time": "00:01:23,456",
          "end_time": "00:01:58,789"
        }},
        {{
          "start_time": "00:03:10,123",
          "end_time": "00:03:45,456"
        }}
      ]
    }}
    ```

    Here is the SRT file content:
    \"\"\"
    {srt_content}
    \"\"\"

    Here is the viral clip analysis:
    \"\"\"
    {analysis_content}
    \"\"\"

    Now, provide the JSON output with the exact timestamps.
    """
    return prompt_template.format(
        srt_content=srt_content,
        analysis_content=analysis_content,
    )

def get_viral_timestamps_gemini(srt_content, analysis_content, model_name):
    """
    Calls the Gemini model to get viral timestamps.
    """
    if not srt_content or not srt_content.strip():
        print(f"{Colors.ERROR}[ERROR]{Colors.RESET} SRT content is empty.")
        return None
    if not analysis_content or not analysis_content.strip():
        print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Analysis content is empty.")
        return None

    print(f"{Colors.INFO}[INFO]{Colors.RESET} Getting viral timestamps with {model_name}...")
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print(f"{Colors.ERROR}[ERROR]{Colors.RESET} GOOGLE_API_KEY not set.")
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name=model_name)
        prompt = get_viral_timestamps_prompt_text(srt_content, analysis_content)
        response = model.generate_content([prompt], request_options={"timeout": 900})
        print("[DEBUG] Gemini response received for viral timestamps extraction.")
        response_text = ""
        if hasattr(response, "text") and response.text:
            response_text = response.text
        elif hasattr(response, "parts") and response.parts:
            for part in response.parts:
                if hasattr(part, "text") and part.text:
                    response_text += part.text + "\n"
            response_text = response.text.strip()

        # Clean the response to extract only the JSON part
        json_match = re.search(r'```json\n(.*)\n```', response_text, re.DOTALL)
        if json_match:
            json_string = json_match.group(1)
            return json.loads(json_string)
        else:
            # Fallback for cases where the model doesn't use markdown
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Failed to decode JSON from Gemini response.")
                print("Raw response:", response_text)
                return None

    except Exception as e:
        print(f"{Colors.ERROR}[ERROR]{Colors.RESET} Gemini viral timestamps extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None
