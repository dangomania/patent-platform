"""
Google Cloud Translation API v2 (Basic) client.

Set GOOGLE_TRANSLATE_API_KEY in .env.
Docs: https://cloud.google.com/translate/docs/basic/translating-text
"""

import os
import httpx

_ENDPOINT = "https://translation.googleapis.com/language/translate/v2"


def is_configured() -> bool:
    return bool(os.getenv("GOOGLE_TRANSLATE_API_KEY"))


def translate_ja_to_en(text: str) -> str | None:
    """
    Translate Japanese text to English via Google Translate API v2.
    Returns translated string, or None on failure.
    """
    api_key = os.getenv("GOOGLE_TRANSLATE_API_KEY")
    if not api_key:
        return None

    # Google Translate has a 5000-char limit per request; split if needed
    chunks = _split(text, max_chars=4500)
    translated: list[str] = []

    with httpx.Client(timeout=30) as client:
        for chunk in chunks:
            r = client.post(
                _ENDPOINT,
                params={"key": api_key},
                json={
                    "q": chunk,
                    "source": "ja",
                    "target": "en",
                    "format": "text",
                },
            )
            r.raise_for_status()
            data = r.json()
            translated.append(
                data["data"]["translations"][0]["translatedText"]
            )

    return "\n\n".join(translated)


def _split(text: str, max_chars: int) -> list[str]:
    """Split text on paragraph boundaries to stay under the char limit."""
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in text.split("\n\n"):
        para_len = len(para) + 2  # +2 for the \n\n separator
        if current_len + para_len > max_chars and current:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(para)
        current_len += para_len

    if current:
        chunks.append("\n\n".join(current))

    return chunks
