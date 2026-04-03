"""
Pre- and post-translation substitution dictionary.

Applied BEFORE sending to Google Translate so that the output already uses
the preferred English terms (e.g. 引用文献１ → D1).

Built-in rules are applied first, then per-user rules loaded from the DB
(passed in as a list of dicts with keys: pattern, replacement, rule_type, enabled).
"""

import re

# ── Full-width → ASCII digit mapping ─────────────────────────────────────────

_FW = str.maketrans("０１２３４５６７８９", "0123456789")


def _fw(s: str) -> str:
    """Convert full-width digits in s to ASCII."""
    return s.translate(_FW)


# ── Built-in regex rules ──────────────────────────────────────────────────────
#
# Each entry: (compiled regex, replacement_callable_or_string)
# Applied in order; results of earlier rules feed into later ones.

def _cited_doc_repl(m: re.Match) -> str:
    """引用文献N  →  DN  (handles full-width or ASCII digits)"""
    return "D" + _fw(m.group(1))


_BUILTIN_REGEX_RULES: list[tuple[re.Pattern, object]] = [
    # 引用文献１ / 引用文献1  →  D1  (full-width or ASCII, 1-2 digits)
    (
        re.compile(r"引用文献([０-９0-9]{1,2})"),
        _cited_doc_repl,
    ),
]

# ── Static exact-string replacements (built-in) ───────────────────────────────
#
# Applied AFTER regex rules.
# Keys are Japanese strings; values are the English replacements.

STATIC_DICT: dict[str, str] = {
    # Add entries here, e.g.:
    # "特定の技術的特徴": "specific technical features",
}

# Keep REGEX_RULES as a public alias for backward compatibility
REGEX_RULES = _BUILTIN_REGEX_RULES


# ── Public API ────────────────────────────────────────────────────────────────

def preprocess(text: str, user_rules: list[dict] = []) -> str:
    """
    Apply dictionary substitutions to Japanese text before translation.

    Built-in rules run first (regex, then static dict), followed by
    per-user rules from the DB in sort_order.

    Each element of user_rules must be a dict with keys:
        pattern     (str)
        replacement (str)
        rule_type   ('exact' or 'regex')
        enabled     (bool)
    """
    # 1. Built-in regex rules
    for pattern, repl in _BUILTIN_REGEX_RULES:
        text = pattern.sub(repl, text)

    # 2. Built-in static dict
    for ja, en in STATIC_DICT.items():
        text = text.replace(ja, en)

    # 3. Per-user rules (already sorted by sort_order from the caller)
    for rule in user_rules:
        if not rule.get("enabled", True):
            continue
        pat = rule["pattern"]
        rep = rule["replacement"]
        if rule.get("rule_type") == "regex":
            try:
                text = re.sub(pat, rep, text)
            except re.error:
                # Skip malformed regex rather than crashing
                pass
        else:
            text = text.replace(pat, rep)

    return text
