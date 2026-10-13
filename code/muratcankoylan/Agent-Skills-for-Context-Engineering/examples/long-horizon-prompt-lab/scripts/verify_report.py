#!/usr/bin/env python3
"""Verify the locally fetched CDC prompt matches the skill's annotated reference.

This is the deterministic provenance gate for the report the long-horizon-prompting
skill is anchored on. It re-extracts the published prompt PDF and asserts that every
block-quote in the skill's annotated reference appears verbatim in the source, so the
skill cannot silently drift from the primary artifact.

Usage:
    python3 examples/long-horizon-prompt-lab/scripts/verify_report.py

Exit code 0 means the annotated reference is faithful to the published prompt.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent
REPO = LAB.parents[1]
PROMPT_PDF = LAB / "report" / "cdc_prompt.pdf"
PROMPT_TXT = LAB / "report" / "cdc_prompt.txt"
ANNOTATED = REPO / "skills" / "long-horizon-prompting" / "references" / "cdc-prompt-annotated.md"


def normalize(text: str) -> str:
    text = (
        text.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u2014", "-")
        .replace("\u2013", "-")
    )
    return re.sub(r"\s+", " ", text).strip()


def load_prompt_text() -> str:
    if PROMPT_PDF.exists():
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(PROMPT_PDF))
            return "\n".join(page.extract_text() for page in reader.pages)
        except ImportError:
            pass
    if PROMPT_TXT.exists():
        return PROMPT_TXT.read_text(encoding="utf-8")
    print(f"ERROR: neither {PROMPT_PDF} nor {PROMPT_TXT} found; run fetch_report.sh first.", file=sys.stderr)
    sys.exit(2)


def extract_blockquotes(markdown: str) -> list[str]:
    quotes: list[str] = []
    current: list[str] = []
    for line in markdown.splitlines():
        if line.startswith(">"):
            current.append(line[1:].strip())
        elif current:
            quotes.append(" ".join(x for x in current if x))
            current = []
    if current:
        quotes.append(" ".join(x for x in current if x))
    return quotes


def main() -> int:
    prompt = normalize(load_prompt_text())
    annotated = ANNOTATED.read_text(encoding="utf-8")
    quotes = extract_blockquotes(annotated)

    missing: list[str] = []
    checked = 0
    for quote in quotes:
        for sentence in re.split(r"(?<=[.:])\s+", quote):
            sentence = sentence.strip()
            if len(sentence) < 15:
                continue
            checked += 1
            if normalize(sentence) not in prompt:
                missing.append(sentence)

    print(f"Checked {checked} annotated block-quote fragments against the published prompt.")
    if missing:
        print(f"FAIL: {len(missing)} fragment(s) not found verbatim in the published prompt:", file=sys.stderr)
        for item in missing:
            print(f"  - {item[:140]}", file=sys.stderr)
        return 1
    print("PASS: skill's annotated CDC reference is faithful to the published prompt (0 drift).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
