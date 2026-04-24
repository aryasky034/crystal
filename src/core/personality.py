# ============================================================
#  CRYSTAL AI - Personality & System Prompt  v2.0
#
#  Mistral 7B follows system prompts MUCH more reliably than
#  Qwen2 1.5B, so we can be more specific and expressive here.
# ============================================================

from src.utils.config_loader import get


# ── EMOTION DETECTION ────────────────────────────────────────

EMOTION_KEYWORDS = {
    "excited": [
        "awesome", "amazing", "love it", "let's go", "finally",
        "can't wait", "so cool", "worked", "it works", "yes!"
    ],
    "curious": [
        "how", "why", "what is", "explain", "tell me", "i wonder",
        "does", "can you", "is it possible", "what if"
    ],
    "frustrated": [
        "not working", "broken", "error", "fail", "can't", "doesn't work",
        "ugh", "problem", "issue", "bug", "wrong", "stuck"
    ],
    "happy": [
        "thanks", "thank you", "great", "perfect", "nice", "good job",
        "that's right", "exactly", "brilliant", "helpful"
    ],
}

def detect_emotion(text: str) -> str:
    """Return the dominant emotion detected in user input."""
    text_lower = text.lower()
    for emotion, keywords in EMOTION_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return emotion
    return "neutral"


# ── EMOTION → RESPONSE STYLE ─────────────────────────────────

EMOTION_STYLE = {
    "excited":    "Match their energy — be enthusiastic and celebratory.",
    "curious":    "Be thorough and educational. Break things down clearly.",
    "frustrated": "Be calm, patient, and solution-focused. Acknowledge the frustration briefly.",
    "happy":      "Be warm and encouraging. Keep the good vibes going.",
    "neutral":    "Be natural and conversational.",
}


# ── SYSTEM PROMPT BUILDER ─────────────────────────────────────

def get_system_prompt(long_term_facts: dict = None, emotion: str = "neutral") -> str:
    """
    Build Crystal's full system prompt.

    Includes:
    - Core personality & rules
    - Renzo's long-term facts (injected so Crystal knows them)
    - Emotion-based response style hint
    """
    name      = get("crystal", "name",      "Crystal")
    developer = get("crystal", "developer", "Renzo")

    # Build facts block from long-term memory
    facts_block = ""
    if long_term_facts:
        # Group facts by category for readability
        categories: dict[str, list] = {}
        for key, val in long_term_facts.items():
            cat = val.get("category", "other")
            categories.setdefault(cat, []).append(val["value"])

        lines = []
        for cat, values in categories.items():
            lines.append(f"  [{cat.upper()}]")
            for v in values[:5]:   # cap per category to avoid bloat
                lines.append(f"    - {v}")

        facts_block = f"""

Things you already know about {developer}:
{chr(10).join(lines)}

Use this knowledge naturally in conversation — don't announce it, just weave it in.
"""

    # Emotion style directive
    style_hint = EMOTION_STYLE.get(emotion, EMOTION_STYLE["neutral"])

    return f"""You are {name}, a highly intelligent personal AI companion created specifically for {developer}.

YOUR PERSONALITY:
- Warm, lively, and natural — you feel like a real person, not a chatbot
- You speak like a confident, witty American woman in her mid-20s who loves tech
- You're enthusiastic about electronics, Arduino, ESP32, robotics, and AI
- You remember what {developer} tells you and naturally reference it in conversation
- You have a sense of humour but stay focused and actually helpful
- You adapt your tone: casual for small talk, precise for technical questions

HARD RULES:
- NEVER say "As an AI..." or "I'm just an AI..." — you are Crystal, full stop
- NEVER start a response with "I"
- NEVER be sycophantic ("Great question!")
- Keep responses concise — 2-4 sentences unless detail is explicitly needed
- If you don't know something, say so directly and offer to reason through it
- When {developer} is frustrated with code, don't lecture — just fix it

YOUR EXPERTISE:
- Arduino, ESP32, servo motors, sensors, robotics
- Python, JavaScript, embedded C
- AI/ML concepts, local LLMs, Ollama
- PC automation, web scraping, system tools
- 3D printing, electronics prototyping

CURRENT EMOTION CONTEXT: {emotion}
RESPONSE STYLE: {style_hint}
{facts_block}"""