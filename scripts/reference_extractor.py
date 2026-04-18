import json
import re
from pathlib import Path
from typing import Dict, List, Set


SEE_ONLY_RE = re.compile(r'^\s*See\s+(.+?)\.\s*$', re.IGNORECASE)
INLINE_SEE_RE = re.compile(r'\bSee\s+([^.]*)\.', re.IGNORECASE)

BAD_SINGLE_WORD_TERMS = {
    "A", "AN", "AND", "AS", "AT", "BY", "FOR", "FROM", "IN", "INTO",
    "OF", "ON", "OR", "THE", "TO", "WITH"
}


def clean_term(term: str) -> str:
    term = term.strip()
    term = term.replace("’", "'")
    term = re.sub(r"\s+", " ", term)

    # Strip punctuation from the ends only
    term = re.sub(r"^[^A-Z0-9'/(),;.\-]+", "", term)
    term = re.sub(r"[^A-Z0-9'/(),;.\-]+$", "", term)

    # Additional cleanup for dangling punctuation
    term = re.sub(r"^[,.;:)\]]+", "", term)
    term = re.sub(r"[,.;:(\[]+$", "", term)

    return term.strip()


def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("’", "'")
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def canonicalize_phrase(phrase: str) -> str:
    phrase = phrase.strip()
    phrase = re.sub(r"[.]+$", "", phrase)
    phrase = phrase.replace("’", "'")
    phrase = re.sub(r"\s+", " ", phrase)
    return clean_term(phrase.upper())


def is_valid_term(term: str) -> bool:
    if not term:
        return False

    if not re.search(r"[A-Z]", term):
        return False

    if " " not in term and "/" not in term and term in BAD_SINGLE_WORD_TERMS:
        return False

    return True


def load_and_clean_entries(path: Path) -> List[dict]:
    raw_entries = json.loads(path.read_text(encoding="utf-8"))

    cleaned = []
    seen_terms = set()

    for entry in raw_entries:
        term = clean_term(entry["term"])
        definition = entry["definition"].strip()

        if not is_valid_term(term):
            continue

        if term in seen_terms:
            continue
        seen_terms.add(term)

        cleaned.append({
            "term": term,
            "definition": definition,
            "letter": entry.get("letter")
        })

    return cleaned


def term_variants(term: str) -> List[str]:
    """
    Variants used for matching a glossary term in running text.

    Examples:
      "HOLY SPIRIT" -> ["holy spirit", maybe pluralized if relevant]
      "EPISCOPAL/EPISCOPATE" -> ["episcopal", "episcopate"]
      "PSALM" -> ["psalm", "psalms"]
    """
    pieces = [p.strip() for p in term.split("/") if p.strip()]
    variants = []

    if len(pieces) >= 2:
        for piece in pieces:
            variants.extend(simple_plural_variants_phrase(piece))
    else:
        variants.extend(simple_plural_variants_phrase(term))

    # deduplicate while preserving longest-first-ish behavior
    out = []
    seen = set()
    for v in sorted(set(variants), key=lambda s: (-len(s), s)):
        if v not in seen:
            out.append(v)
            seen.add(v)
    return out


def simple_plural_variants_phrase(phrase: str) -> List[str]:
    """
    Generate conservative singular/plural surface variants for a phrase.

    We only inflect the last word of the phrase.
    Example:
      "capital sins" -> ["capital sins"]
      "psalm" -> ["psalm", "psalms"]
      "church" -> ["church", "churches"]
      "charity" -> ["charity", "charities"]
    """
    phrase = normalize_text(phrase)
    if not phrase:
        return []

    words = phrase.split()
    last = words[-1]

    variants = {phrase}

    def replace_last(new_last: str):
        variants.add(" ".join(words[:-1] + [new_last]))

    # plural rules
    if last.endswith("y") and len(last) >= 2 and last[-2] not in "aeiou":
        replace_last(last[:-1] + "ies")
    elif last.endswith(("s", "x", "z", "ch", "sh")):
        replace_last(last + "es")
    else:
        replace_last(last + "s")

    # singular rules, if the term itself is plural-looking
    if last.endswith("ies") and len(last) >= 4:
        replace_last(last[:-3] + "y")
    elif last.endswith("es") and (
        last[:-2].endswith(("s", "x", "z", "ch", "sh"))
    ):
        replace_last(last[:-2])
    elif last.endswith("s") and not last.endswith("ss"):
        replace_last(last[:-1])

    return sorted(variants, key=lambda s: (-len(s), s))


def extract_inline_see_targets(definition: str, candidate_terms: Set[str]) -> Set[str]:
    """
    Extract explicit references from clauses like:
      'See Bible; Covenant.'
    """
    refs = set()

    for m in INLINE_SEE_RE.finditer(definition):
        chunk = m.group(1)

        # Split on semicolons/commas
        pieces = re.split(r"[;,]", chunk)
        for piece in pieces:
            candidate = canonicalize_phrase(piece)
            if candidate in candidate_terms:
                refs.add(candidate)

    return refs


def remove_inline_see_clause_text(definition: str) -> str:
    """
    Remove 'See X; Y.' clauses before free-text term matching,
    so those explicit references are not double-counted.
    """
    definition = INLINE_SEE_RE.sub(" ", definition)
    definition = re.sub(r"\s+", " ", definition).strip()
    return definition


def find_non_overlapping_references(
    definition: str,
    source_term: str,
    candidate_terms: Set[str]
) -> List[str]:
    """
    Find references to glossary terms in a definition.

    Longest matches win first, so OLD TESTAMENT wins over TESTAMENT
    on the same span.

    Slash terms like EPISCOPAL/EPISCOPATE match on either variant.
    """
    norm_def = normalize_text(definition)

    term_infos = []
    for term in candidate_terms:
        if term == source_term:
            continue
        variants = term_variants(term)
        if not variants:
            continue
        max_len = max(len(v) for v in variants)
        term_infos.append((term, variants, max_len))

    # Longest first
    term_infos.sort(key=lambda x: (-x[2], x[0]))

    occupied = [False] * len(norm_def)
    found = []

    for term, variants, _ in term_infos:
        matched_this_term = False

        for variant in sorted(variants, key=lambda v: (-len(v), v)):
            pattern = re.compile(rf"(?<![a-z0-9']){re.escape(variant)}(?![a-z0-9'])")

            for match in pattern.finditer(norm_def):
                start, end = match.span()

                if any(occupied[i] for i in range(start, end)):
                    continue

                for i in range(start, end):
                    occupied[i] = True

                found.append(term)
                matched_this_term = True
                break

            if matched_this_term:
                break

    return sorted(found)


def build_reference_dictionary(entries: List[dict]) -> Dict[str, List[str]]:
    """
    Every entry becomes a node/key.

    References are the union of:
      1. explicit See-targets
      2. glossary terms mentioned in the non-See explanatory text
    """
    all_terms = {entry["term"] for entry in entries}
    ref_dict: Dict[str, List[str]] = {}

    for entry in entries:
        source_term = entry["term"]
        original_definition = entry["definition"]

        explicit_refs = extract_inline_see_targets(original_definition, all_terms)

        main_definition = remove_inline_see_clause_text(original_definition)
        text_refs = set(find_non_overlapping_references(
            definition=main_definition,
            source_term=source_term,
            candidate_terms=all_terms
        ))

        refs = sorted((explicit_refs | text_refs) - {source_term})
        ref_dict[source_term] = refs

    return dict(sorted(ref_dict.items()))


def main():
    input_path = Path("data/clean/glossary.json")
    output_path = Path("references.json")

    entries = load_and_clean_entries(input_path)
    ref_dict = build_reference_dictionary(entries)

    output_path.write_text(
        json.dumps(ref_dict, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Wrote {len(ref_dict)} entries to {output_path}")
    print()
    print(json.dumps(ref_dict, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
