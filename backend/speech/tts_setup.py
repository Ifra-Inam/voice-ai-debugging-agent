import os
import re
from urllib.parse import urlparse
from xml.sax.saxutils import escape

import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


import re

# Remove fenced code block markers but preserve the code inside.
def remove_code_fences(text: str) -> str:
    def replace_fence(match: re.Match) -> str:
        code = match.group(1)
        return f" Code example: {code} "

    return re.sub(
        r"```[^\S\r\n]*[a-zA-Z0-9_+-]*[^\S\r\n]*\n?(.*?)```",
        replace_fence,
        text,
        flags=re.DOTALL,
    )

def _strip_markdown_for_speech(text: str) -> str:
    cleaned = remove_code_fences(text)

    # Remove inline code ticks, preserving the enclosed text.
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)

    # Convert Markdown links to their readable labels.
    cleaned = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)

    # Remove bold, italic, and strikethrough markers.
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"__(.*?)__", r"\1", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"~~(.*?)~~", r"\1", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", cleaned)
    cleaned = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"\1", cleaned)

    # Remove headings and list markers.
    cleaned = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", cleaned)
    cleaned = re.sub(r"(?m)^\s*[-*+]\s+", "", cleaned)
    cleaned = re.sub(r"(?m)^\s*\d+[.)]\s+", "", cleaned)

    # Convert operators BEFORE replacing individual equals signs.
    replacements = [
        ("=>", " arrow "),
        ("->", " arrow "),
        ("!=", " not equal to "),
        ("==", " equals "),
        (">=", " greater than or equal to "),
        ("<=", " less than or equal to "),
        ("=", " equals "),
        ("+", " plus "),
        ("/", " slash "),
        ("_", " underscore "),
        ("[", " open bracket "),
        ("]", " close bracket "),
        ("{", " open brace "),
        ("}", " close brace "),
        ("(", " open parenthesis "),
        (")", " close parenthesis "),
    ]

    for symbol, spoken in replacements:
        cleaned = cleaned.replace(symbol, spoken)

    # Remove leftover Markdown characters and normalize whitespace.
    cleaned = re.sub(r"[*#`~|]", " ", cleaned)
    cleaned = re.sub(r"\s+([,.!?;:])", r"\1", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned or "Here is the update."

def speak_text(text: str):
    # Set up the speech config using resource endpoint
    endpoint_url = os.getenv("AZURE_SPEECH_ENDPOINT")

    parsed = urlparse(endpoint_url)
    base_endpoint = f"{parsed.scheme}://{parsed.netloc}"

    speech_key = os.getenv("API_KEY")
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, endpoint=base_endpoint)
    speech_config.speech_synthesis_voice_name = "en-US-Ava:DragonHDLatestNeural"

    spoken_text = _strip_markdown_for_speech(text)
    ssml = (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        'xml:lang="en-US">'
        '<voice name="en-US-Ava:DragonHDLatestNeural">'
        '<prosody rate="+20%">'
        f"{escape(spoken_text)}"
        '</prosody>'
        '</voice>'
        '</speak>'
    )

    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return result
    if result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        raise RuntimeError(f"Speech synthesis canceled: {cancellation_details.reason}, {cancellation_details.error_details}")

    raise RuntimeError("Speech synthesis did not complete.")