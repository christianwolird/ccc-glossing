import json
import re
from pathlib import Path
from collections import defaultdict


INPUT = Path("data/clean/glossary.json")
OUTPUT = Path("references.json")


SEE_RE = re.compile(r"\bSee\s+([^.]*)\.", re.IGNORECASE)


STOPWORDS = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into",
    "of", "on", "or", "the", "to", "with", "without", "through",
    "that", "this", "these", "those", "their", "his", "her", "its",
    "is", "are", "was", "were", "be", "been", "being"
}


def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("—", " ").replace("–", " ").replace("-", " ")
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def canonical_term(term: str) -> str:
    return re.sub(r"\s+", " ", term.strip().upper())


def clean_definition(defn: str) -> str:
    return re.sub(r"\s+", " ", defn.strip())


def simple_plural_forms(word: str) -> set[str]:
    forms = {word}
    if word.endswith("y") and len(word) >= 2 and word[-2] not in "aeiou":
        forms.add(word[:-1] + "ies")
    elif word.endswith(("s", "x", "z", "ch", "sh")):
        forms.add(word + "es")
    else:
        forms.add(word + "s")

    if word.endswith("ies") and len(word) >= 4:
        forms.add(word[:-3] + "y")
    if word.endswith("es"):
        base = word[:-2]
        if base.endswith(("s", "x", "z", "ch", "sh")):
            forms.add(base)
    if word.endswith("s") and not word.endswith("ss"):
        forms.add(word[:-1])

    return {f for f in forms if f}


def token_family(word: str) -> set[str]:
    """
    Conservative derivational family generator.
    This is intentionally small. Better to miss a few than hallucinate many.
    """
    out = set(simple_plural_forms(word))

    # adverb / adjective / noun-ish families
    if word.endswith("ice"):
        stem = word[:-3]   # justice -> just
        if stem:
            out.add(stem)
            out.add(stem + "ly")
            out.add("un" + stem)
            out.add("un" + stem + "ly")

    if word.endswith("ity"):
        stem = word[:-3]
        if stem:
            out.add(stem)

    if word.endswith("ion"):
        stem = word[:-3]
        if stem:
            out.add(stem)

    return {x for x in out if x and x not in STOPWORDS}


# High-value semantic aliases / triggers.
# This is the part that fixes "Jesus" -> "JESUS CHRIST", etc.
MANUAL_TRIGGERS = {
    "JESUS CHRIST": {"jesus", "jesus'"},
    "GOD": {"god's"},
    "VIRGIN MARY": {"mary"},
    "JUSTICE": {"just", "justly", "unjust", "unjustly"},
    "SALVATION": {"save", "saves", "saving", "saved"},
    "CHRISTMAS": {"nativity"},
    "EUCHARIST": {"communion"},  # optional; comment out if too aggressive
    "LITURGY": {"liturgical"},
    "HEAVEN": {"heavenly"},
    "LAW, MORAL": {"morally"},
    "REVELATION": {"revealed truth"},
}


def split_see_targets(chunk: str) -> list[str]:
    """
    Semicolons separate targets. Commas may belong to a headword.
    """
    chunk = chunk.strip()
    if not chunk:
        return []

    # First try whole chunk
    parts = [chunk]

    # Then semicolon-split alternatives
    if ";" in chunk:
        parts.extend([p.strip() for p in chunk.split(";") if p.strip()])

    # Deduplicate preserving order
    seen = set()
    out = []
    for p in parts:
        p2 = canonical_term(p.rstrip("."))
        if p2 not in seen:
            seen.add(p2)
            out.append(p2)
    return out


def extract_see_refs(defn: str, term_set: set[str]) -> set[str]:
    refs = set()
    for m in SEE_RE.finditer(defn):
        chunk = m.group(1)
        for cand in split_see_targets(chunk):
            if cand in term_set:
                refs.add(cand)
    return refs


def strip_see_clauses(defn: str) -> str:
    return SEE_RE.sub(" ", defn)


def build_surface_map(terms: list[str]) -> dict[str, set[str]]:
    """
    term -> set of normalized surface triggers
    """
    surfaces = {}

    for term in terms:
        term_norm = normalize_text(term)
        triggers = {term_norm}

        # Comma-reordered aliases
        if "," in term:
            parts = [p.strip() for p in term.split(",")]
            if len(parts) == 2 and all(parts):
                triggers.add(normalize_text(f"{parts[1]} {parts[0]}"))

        # Slash-variants
        if "/" in term:
            slash_parts = [p.strip() for p in term.split("/") if p.strip()]
            for p in slash_parts:
                triggers.add(normalize_text(p))

        # Phrase headword expansions: inflect the last word conservatively
        words = term_norm.split()
        if words:
            base_last = words[-1]
            for form in token_family(base_last):
                phrase = " ".join(words[:-1] + [form])
                triggers.add(phrase)

        # Single-word terms get token families directly
        if len(words) == 1:
            for form in token_family(words[0]):
                triggers.add(form)

        # Manual semantic triggers
        triggers.update(MANUAL_TRIGGERS.get(term, set()))

        surfaces[term] = {t for t in triggers if t}

    return surfaces


def dedupe_entries(raw_entries: list[dict]) -> list[dict]:
    """
    Keep the longest definition per term. This helps with parser-split duplicates.
    """
    best = {}
    for entry in raw_entries:
        term = canonical_term(entry["term"])
        defn = clean_definition(entry["definition"])
        if not term:
            continue
        if term not in best or len(defn) > len(best[term]["definition"]):
            best[term] = {"term": term, "definition": defn}
    return list(best.values())


def find_text_refs(defn: str, source_term: str, surfaces: dict[str, set[str]]) -> set[str]:
    refs = set()
    norm_def = normalize_text(defn)

    # longest triggers first, to reduce smaller substring noise
    candidates = []
    for term, trigset in surfaces.items():
        if term == source_term:
            continue
        best_len = max(len(t) for t in trigset)
        candidates.append((term, trigset, best_len))
    candidates.sort(key=lambda x: (-x[2], x[0]))

    occupied = [False] * len(norm_def)

    for term, trigset, _ in candidates:
        matched = False
        for trig in sorted(trigset, key=lambda s: (-len(s), s)):
            pattern = re.compile(rf"(?<![a-z0-9']){re.escape(trig)}(?![a-z0-9'])")
            for m in pattern.finditer(norm_def):
                a, b = m.span()
                if any(occupied[i] for i in range(a, b)):
                    continue
                for i in range(a, b):
                    occupied[i] = True
                refs.add(term)
                matched = True
                break
            if matched:
                break

    return refs


def build_reference_graph(entries: list[dict]) -> dict[str, list[str]]:
    term_set = {e["term"] for e in entries}
    surfaces = build_surface_map(sorted(term_set))

    graph = {}
    for entry in entries:
        term = entry["term"]
        defn = entry["definition"]

        see_refs = extract_see_refs(defn, term_set)
        main_text = strip_see_clauses(defn)
        text_refs = find_text_refs(main_text, term, surfaces)

        refs = sorted((see_refs | text_refs) - {term})
        graph[term] = refs

    return dict(sorted(graph.items()))


def main():
    raw_entries = json.loads(INPUT.read_text(encoding="utf-8"))
    entries = dedupe_entries(raw_entries)
    graph = build_reference_graph(entries)

    OUTPUT.write_text(
        json.dumps(graph, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


if __name__ == "__main__":
    main()
