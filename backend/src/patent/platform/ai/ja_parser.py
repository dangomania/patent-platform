"""
Japanese morphological analysis for patent claim processing.

Uses SudachiPy (SplitMode.C = longest compound segmentation) to:
  1. Parse Japanese patent claims into individual tokens
  2. Find every 前記XX / 該XX reference
  3. Extract the noun phrase XX correctly (compound nouns, 第Nの~)
  4. Check antecedent basis against preceding claims
"""

import re
from sudachipy import Dictionary, SplitMode

_tokenizer = Dictionary().create(mode=SplitMode.C)


# ── Tokenisation helpers ──────────────────────────────────────────────────────

def _tokenize(text: str):
    return _tokenizer.tokenize(text)


def _is_noun_like(tok) -> bool:
    """True for tokens that may form part of a noun phrase."""
    ps = tok.part_of_speech()
    pos0, pos1 = ps[0], ps[1]
    return pos0 in ("名詞", "接頭辞") or (pos0 == "名詞" and pos1 == "数詞")


def _is_no_bridge(tok, tokens, idx, phrase: list[str]) -> bool:
    """
    True when の should be included in the noun phrase.

    Only bridge の when the immediately preceding token in the phrase is a
    接頭辞 (prefix, e.g. 第) or a 数詞 (numeral).  This correctly handles
    「第1のステップ」 while stopping before possessive modifiers like
    「発光素子の色」(where の marks an attribute, not part of the term name).
    """
    if tok.surface() != "の":
        return False
    if tok.part_of_speech()[0] != "助詞":
        return False
    if not phrase:
        return False
    # The last real token added to the phrase must be a prefix or numeral
    prev_idx = idx - 1
    while prev_idx >= 0:
        prev_tok = tokens[prev_idx]
        prev_ps = prev_tok.part_of_speech()
        if prev_ps[0] in ("接頭辞",) or (prev_ps[0] == "名詞" and prev_ps[1] == "数詞"):
            break
        if prev_tok.surface() in ("の",):
            prev_idx -= 1
            continue
        return False   # previous content token is a regular noun → don't bridge
    nxt = idx + 1
    return nxt < len(tokens) and _is_noun_like(tokens[nxt])


# Verb-modifier surfaces that can appear between nouns in a noun phrase,
# e.g. 「不活性化された + 遺伝子」, 「改変した + DNA」, 「発現している + タンパク質」
_VERB_BRIDGE_RE = re.compile(
    r"^(さ?れ?た|した|している|してある|されている|されてある|される|する)$"
)


def _try_verb_bridge(tokens, i: int) -> int | None:
    """
    If tokens[i:] start with a verb-modifier sequence (〜された / 〜した / etc.)
    AND the token immediately after it is noun-like, return the index of that
    following noun token.  Otherwise return None.
    """
    j = i
    buf = ""
    while j < len(tokens):
        ps = tokens[j].part_of_speech()
        pos0 = ps[0]
        surf = tokens[j].surface()
        # Accept: 動詞, 助動詞, and て (接続助詞 bridging して+いる)
        if pos0 in ("動詞", "助動詞") or (pos0 == "助詞" and surf == "て"):
            buf += surf
            j += 1
        else:
            break
    if _VERB_BRIDGE_RE.match(buf) and j < len(tokens) and _is_noun_like(tokens[j]):
        return j   # caller should resume collecting from j (the following noun)
    return None


def _extract_np_at(tokens, start: int) -> str:
    """
    Starting at tokens[start], greedily collect a noun phrase.
    Includes:
      • 名詞 (all subtypes) and 接頭辞
      • の when bridging ordinal/numeral to noun  (「第1のステップ」)
      • verb-modifier sequences (〜された/〜した/〜している) between nouns
    """
    phrase = []
    i = start
    while i < len(tokens):
        tok = tokens[i]
        if _is_noun_like(tok):
            phrase.append(tok.surface())
            i += 1
        elif phrase and _is_no_bridge(tok, tokens, i, phrase):
            phrase.append(tok.surface())   # append の
            i += 1
        elif phrase:
            # Try verb-modifier bridge (〜された + NOUN, etc.)
            resume = _try_verb_bridge(tokens, i)
            if resume is not None:
                # Include all tokens from i up to (not including) the next noun
                for k in range(i, resume):
                    phrase.append(tokens[k].surface())
                i = resume   # next iteration picks up the noun
            else:
                break
        else:
            break
    return "".join(phrase)


# ── Claim parser ──────────────────────────────────────────────────────────────

_FW_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


def _to_int(s: str) -> int:
    return int(s.translate(_FW_DIGITS))


def parse_claims(raw: str) -> list[dict]:
    """
    Parse a block of Japanese patent claims into [{num, text}, …].

    Supported formats:
      • 【請求項N】  (ASCII or full-width digits)
      • 請求項N / N. at line start
    """
    text = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    claims: list[dict] = []

    # Format 1: 【請求項N】
    re1 = re.compile(r"【請求項([０-９\d]+)】([\s\S]*?)(?=【請求項[０-９\d]+】|$)")
    for m in re1.finditer(text):
        claims.append({"num": _to_int(m.group(1)), "text": m.group(2).strip()})
    if claims:
        return claims

    # Format 2: line-start "請求項N" or "N."
    lines = text.split("\n")
    cur: dict | None = None
    for line in lines:
        m2 = re.match(r"^(?:請求項|クレーム)\s*([０-９\d]+)[．.。\s](.*)", line) \
          or re.match(r"^([０-９\d]+)[．.)）]\s*(.*)", line)
        if m2:
            if cur:
                claims.append(cur)
            cur = {"num": _to_int(m2.group(1)), "text": m2.group(2)}
        elif cur:
            cur["text"] += "\n" + line
    if cur:
        claims.append(cur)
    return claims


# ── Dependency parser ────────────────────────────────────────────────────────

# Matches 請求項N (and full-width N) inside claim text
_DEP_NUM_RE = re.compile(r"請求項([０-９\d]+)")
# Matches ranges: 請求項N〜M, 請求項N～M, 請求項N-M (full/half-width dashes)
_DEP_RANGE_RE = re.compile(r"請求項([０-９\d]+)[〜～\-－–—]([０-９\d]+)")


def _direct_parents(claim_text: str, own_num: int) -> list[int]:
    """Return claim numbers that this claim explicitly depends on."""
    nums: set[int] = set()
    # Expand ranges first (e.g. 請求項１０〜１２ → 10, 11, 12)
    for m in _DEP_RANGE_RE.finditer(claim_text):
        start, end = _to_int(m.group(1)), _to_int(m.group(2))
        for n in range(start, end + 1):
            if n != own_num:
                nums.add(n)
    # Individual references (also catches the start of any range, deduped by set)
    for m in _DEP_NUM_RE.finditer(claim_text):
        n = _to_int(m.group(1))
        if n != own_num:
            nums.add(n)
    return sorted(nums)


def _build_chain(num: int, parent_map: dict[int, list[int]], visited: set[int]) -> list[int]:
    """Recursively follow the first (primary) parent to root; returns [num, parent, …, root]."""
    if num in visited:
        return [num]
    visited.add(num)
    parents = parent_map.get(num, [])
    if not parents:
        return [num]
    return [num] + _build_chain(parents[0], parent_map, visited)


def _nearest_found_in_branch(entry: int, found_set: set[int],
                              parent_map: dict[int, list[int]]) -> list[int] | None:
    """
    BFS from entry through parent_map; return shortest path to the nearest claim
    in found_set.  Stops at the first hit — does not continue past a found claim.
    """
    from collections import deque
    if entry in found_set:
        return [entry]
    queue: deque[list[int]] = deque([[entry]])
    visited: set[int] = {entry}
    while queue:
        path = queue.popleft()
        for parent in parent_map.get(path[-1], []):
            if parent in found_set:
                return path + [parent]
            if parent not in visited:
                visited.add(parent)
                queue.append(path + [parent])
    return None


def _all_ancestors(num: int, parent_map: dict[int, list[int]], visited: set[int] | None = None) -> set[int]:
    """Return ALL claim numbers reachable upward through the dependency graph (excluding num)."""
    if visited is None:
        visited = set()
    result: set[int] = set()
    for parent in parent_map.get(num, []):
        if parent not in visited:
            visited.add(parent)
            result.add(parent)
            result |= _all_ancestors(parent, parent_map, visited)
    return result


# ── Reference finder ──────────────────────────────────────────────────────────

_MARKERS = {"前記", "該"}


def find_refs(claim_text: str) -> list[dict]:
    """
    Find all 前記XX / 該XX references in a claim.
    Returns [{term, prefix, char_index}, …] with deduplicated terms.
    """
    tokens = _tokenize(claim_text)
    refs: list[dict] = []
    seen: set[str] = set()

    # Reconstruct char offsets from token surfaces
    pos = 0
    tok_offsets = []
    for tok in tokens:
        tok_offsets.append(pos)
        pos += len(tok.surface())

    for i, tok in enumerate(tokens):
        if tok.surface() in _MARKERS:
            term = _extract_np_at(tokens, i + 1)
            if term and term not in seen:
                seen.add(term)
                refs.append({
                    "term": term,
                    "prefix": tok.surface(),
                    "char_index": tok_offsets[i],
                })
    return refs


# ── Antecedent checker ────────────────────────────────────────────────────────

def _find_bare_occurrences(term: str, text: str, window: int = 50) -> list[dict]:
    """
    Find all occurrences of `term` in `text` that are NOT preceded by 前記/該.
    Returns a list of context snippets with the term's relative position.
    """
    results = []
    idx = 0
    while True:
        pos = text.find(term, idx)
        if pos == -1:
            break
        before = text[max(0, pos - 2): pos]
        if not (before.endswith("前記") or before.endswith("該")):
            start = max(0, pos - window)
            end = min(len(text), pos + len(term) + window)
            results.append({
                "snippet": text[start:end],
                "term_start": pos - start,
                "term_len": len(term),
            })
        idx = pos + len(term)
    return results


# ── Main analysis entry point ─────────────────────────────────────────────────

def analyze(raw: str) -> dict:
    """
    Analyse a full claims block.

    Returns:
    {
      "claims": [
        {
          "num": int,
          "text": str,
          "refs": [
            {
              "term": str,
              "prefix": "前記" | "該",
              "has_basis": bool,
              "self_found": bool,            # introduced in same claim (before this ref)
              "preceding_nums": [int, …],
              "contexts": [
                { "claim_num": int, "snippet": str,
                  "term_start": int, "term_len": int }
              ]
            }
          ]
        }
      ]
    }
    """
    claims = parse_claims(raw)

    # Build dependency map for all claims
    parent_map: dict[int, list[int]] = {
        c["num"]: _direct_parents(c["text"], c["num"]) for c in claims
    }

    result_claims = []
    for claim in claims:
        refs = find_refs(claim["text"])
        analyzed_refs = []

        for ref in refs:
            term = ref["term"]

            # Same-claim antecedent (text before the marker)
            text_before = claim["text"][: ref["char_index"]]
            self_ctxs = _find_bare_occurrences(term, text_before)
            self_found = len(self_ctxs) > 0

            # Preceding claims
            preceding_nums: list[int] = []
            contexts: list[dict] = []

            if self_found:
                for c in self_ctxs:
                    contexts.append({
                        "claim_num": claim["num"],
                        "label": f"請求項{claim['num']}（同一）",
                        **c,
                    })

            ancestor_nums = _all_ancestors(claim["num"], parent_map)
            claim_by_num = {c["num"]: c for c in claims}

            # Collect which ancestors actually contain the term (bare)
            found_set: set[int] = set()
            for anc_num in ancestor_nums:
                prev = claim_by_num.get(anc_num)
                if prev and _find_bare_occurrences(term, prev["text"]):
                    found_set.add(anc_num)
                    preceding_nums.append(anc_num)

            preceding_nums.sort()

            # Build one chain per direct parent: path to nearest found claim in that branch
            dep_chains: list[list[int]] = []
            seen_chain_keys: set[str] = set()
            for dp in parent_map.get(claim["num"], []):
                path = _nearest_found_in_branch(dp, found_set, parent_map)
                if path:
                    full = [claim["num"]] + path
                    key = "-".join(map(str, full))
                    if key not in seen_chain_keys:
                        seen_chain_keys.add(key)
                        dep_chains.append(full)

            # Contexts: one snippet per unique found claim referenced in dep_chains
            seen_ctx: set[int] = set()
            for chain in dep_chains:
                found_num = chain[-1]
                if found_num in seen_ctx:
                    continue
                seen_ctx.add(found_num)
                prev = claim_by_num[found_num]
                for c in _find_bare_occurrences(term, prev["text"])[:2]:
                    contexts.append({
                        "claim_num": found_num,
                        "label": f"請求項{found_num}",
                        **c,
                    })

            analyzed_refs.append({
                "term": term,
                "prefix": ref["prefix"],
                "has_basis": self_found or len(preceding_nums) > 0,
                "self_found": self_found,
                "preceding_nums": preceding_nums,
                "dep_chains": dep_chains,   # [[13,10], [13,11], [13,12,10]]
                "contexts": contexts,
            })

        dep_chain = _build_chain(claim["num"], parent_map, set())

        result_claims.append({
            "num": claim["num"],
            "text": claim["text"],
            "depends_on": parent_map.get(claim["num"], []),
            "dep_chain": dep_chain,   # e.g. [5, 3, 1]
            "refs": analyzed_refs,
        })

    return {"claims": result_claims}
