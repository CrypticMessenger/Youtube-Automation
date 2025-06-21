def get_viral_clip_identifier_prompt(
    number_of_sections=None,
    youtube_transcript_placeholder="[PASTE YOUTUBE VIDEO TRANSCRIPT HERE]",
):
    """
    Returns a prompt for identifying viral short-form video clips from a YouTube video transcript.

    :param number_of_sections: Optional; if specified, the AI will look for this many segments.
    :return: A formatted prompt string.
    """
    if number_of_sections is None:
        number_of_sections = "[Default to 3-5, or choose a number you deem appropriate based on transcript quality and length, e.g., '3 to 5']"
    else:
        number_of_sections = str(number_of_sections)

    number_of_sections_placeholder = (
        "please identify {number_of_sections} of the most promising segments.".format(
            number_of_sections=number_of_sections
        )
    )

    viral_clip_identifier_prompt = """
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

    {youtube_transcript_placeholder}

    Key considerations for you, the AI, when processing:
    Inferring from Text: Since you only have text, you'll need to infer pacing, emphasis, and potential visual accompaniments based on the language used.
    Prioritization: If there are many potential segments, prioritize those with the strongest combination of the criteria above.
    Conciseness: Even your justifications should be concise but informative.
    This prompt is designed to be very specific to guide the AI towards the desired outcome. Good luck!
    """

    return viral_clip_identifier_prompt.format(
        number_of_sections_placeholder=number_of_sections_placeholder,
        youtube_transcript_placeholder=youtube_transcript_placeholder,
    )
