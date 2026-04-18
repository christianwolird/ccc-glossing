import re
import json
from pathlib import Path
from typing import List, Dict, Any


ENTRY_START_RE = re.compile(r"^([A-Z][A-Z0-9'’()./\-;,& ]+):\s*(.*)$")
SECTION_MARKER_RE = re.compile(r"^-[A-Z]-$")
PAGE_NUMBER_RE = re.compile(r"^\d{1,4}$")


def clean_line(line: str) -> str:
    """
    Clean one raw line from the glossary dump.
    """
    line = line.strip()

    # Drop repeated page header/footer junk.
    if not line:
        return ""
    if line == "Glossary":
        return ""
    if SECTION_MARKER_RE.fullmatch(line):
        return ""
    if PAGE_NUMBER_RE.fullmatch(line):
        return ""

    # Remove page numbers accidentally glued onto the end of a sentence,
    # e.g. '(114).866' or '(857).867'
    line = re.sub(r"(?<=\))\d{1,4}$", "", line)

    # Occasionally a page number may be glued after punctuation with no space.
    line = re.sub(r"(?<=[.;,])\d{1,4}$", "", line)

    return line.strip()


def parse_glossary(text: str) -> List[Dict[str, Any]]:
    """
    Parse the glossary paste dump into a list of entries.

    Returns items like:
    {
        "term": "ABORTION",
        "definition": "Deliberate termination of pregnancy ...",
        "letter": "A"
    }
    """
    entries: List[Dict[str, Any]] = []
    current_term = None
    current_parts: List[str] = []

    def flush():
        nonlocal current_term, current_parts
        if current_term is not None:
            definition = "".join(current_parts).strip()
            definition = re.sub(r"\s+", " ", definition).strip()
            entries.append({
                "term": current_term,
                "definition": definition,
                "letter": current_term[0] if current_term else None,
            })
        current_term = None
        current_parts = []

    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        if not line:
            continue

        m = ENTRY_START_RE.match(line)
        if m:
            flush()
            current_term = m.group(1).strip()
            first_text = m.group(2).strip()
            current_parts = [first_text] if first_text else []
            continue

        # Continuation line of current definition.
        if current_term is not None:
            # If previous chunk ends with a hyphen, join with no space:
            # acknowl- + edgment -> acknowledgment
            if current_parts and current_parts[-1].endswith("-"):
                current_parts[-1] = current_parts[-1][:-1] + line
            else:
                if current_parts:
                    current_parts.append(" " + line)
                else:
                    current_parts.append(line)
        else:
            # Ignore preamble/junk before the first detected term.
            continue

    flush()
    return entries


def glossary_to_dict(entries: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Convert parsed entries to a simple {term: definition} dict.
    """
    return {entry["term"]: entry["definition"] for entry in entries}


if __name__ == "__main__":
    path = Path("data/raw/glossary_paste.txt")
    text = path.read_text(encoding="utf-8")

    entries = parse_glossary(text)

    print(f"Parsed {len(entries)} entries.")
    print()

    # Example preview
    for entry in entries[:5]:
        print(entry["term"])
        print(entry["definition"])
        print()

    # Save as JSON
    Path("glossary.json").write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
