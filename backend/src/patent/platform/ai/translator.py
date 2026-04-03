"""
Translate JPO Office Actions from Japanese to English.

Primary engine: Google Translate (fast, set GOOGLE_TRANSLATE_API_KEY).
Fallback:       Claude Opus (set ANTHROPIC_API_KEY).
"""

import anthropic
import os

from .google_translate import translate_ja_to_en, is_configured as google_configured
from .translation_dict import preprocess

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are an expert Japanese patent attorney and translator specializing in JPO Office Actions (拒絶理由通知).

Translate the provided Japanese Office Action into English using a word-for-word, clause-by-clause approach. Prioritise fidelity to the source over natural English flow — patent attorneys need to verify the exact meaning of each phrase against the original Japanese.

Rules:
- Translate each sentence in the order it appears; do not reorder or restructure
- Preserve every clause, modifier, and conditional exactly as written
- Keep all claim numbers, reference numerals, and figure references unchanged
- Render article numbers literally (e.g., 特許法第29条第2項 → Patent Act Article 29, Paragraph 2)
- Keep Japanese legal set-phrases as close to literal as possible (e.g., 容易に想到 → "could easily conceive", not "obvious")
- Do not paraphrase, summarise, or omit any part
- Preserve paragraph and line structure

After the translation, add a section titled "## Key Issues Summary" listing the rejection grounds as short bullets."""

DRAFT_SYSTEM_PROMPT = """You are an expert Japanese patent attorney. Based on the provided JPO Office Action (in Japanese) and its English translation, draft a response strategy and report for the patent attorney.

Structure your response as:
## 1. 拒絶理由の要約 (Summary of Rejection)
## 2. 対応方針 (Response Strategy)
## 3. 補正案 (Amendment Proposals)
## 4. 意見書の要点 (Key Arguments for Remarks)
## 5. 注意事項 (Notes & Risks)

Write in Japanese."""


def translate_oa(japanese_text: str, user_rules: list[dict] = []) -> str:
    """
    Translate a Japanese OA to English.
    Uses Google Translate if configured, otherwise Claude Opus.

    user_rules: per-user substitution rules loaded from the DB
                (dicts with keys: pattern, replacement, rule_type, enabled).
                Applied via preprocess() before translation.
    """
    processed_text = preprocess(japanese_text, user_rules)

    if google_configured():
        result = translate_ja_to_en(processed_text)
        if result:
            return result
        # fall through to Claude if Google fails

    # Claude fallback
    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": processed_text}],
    ) as stream:
        return "".join(chunk for chunk in stream.text_stream)


def draft_response(japanese_text: str, translation: str) -> str:
    """Draft a response strategy report in Japanese."""
    user_content = f"""## 拒絶理由通知（原文）
{japanese_text}

## 英訳
{translation}"""

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=DRAFT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    ) as stream:
        return "".join(chunk for chunk in stream.text_stream)
