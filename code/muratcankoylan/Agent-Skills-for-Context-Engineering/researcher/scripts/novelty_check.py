#!/usr/bin/env python3
"""Check whether a proposed skill idea overlaps existing corpus content."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "when",
    "agent",
    "agents",
    "skill",
    "skills",
    "context",
    "activation",
    "artifact",
    "artifacts",
    "author",
    "candidate",
    "change",
    "changes",
    "check",
    "checks",
    "claim",
    "claims",
    "decision",
    "delta",
    "evidence",
    "existing",
    "file",
    "gaps",
    "human",
    "proposal",
    "proposed",
    "quality",
    "retrieval",
    "review",
    "risk",
    "risks",
    "source",
    "status",
    "target",
    "type",
}


STRUCTURED_SECTIONS = [
    "Mechanism",
    "Skill Target",
    "Proposed Delta",
    "Risks And Gaps",
    "Recommendation",
]


def tokens(text: str) -> set[str]:
    raw = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
    return {t.replace("_", "-") for t in raw if t not in STOPWORDS}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def read_input(args: argparse.Namespace) -> str:
    parts: list[str] = []
    if args.text:
        parts.append(args.text)
    if args.file:
        parts.append(Path(args.file).read_text(encoding="utf-8"))
    if not parts:
        parts.append(sys.stdin.read())
    return "\n".join(parts).strip()


def extract_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    for match in re.finditer(r"^##\s+(.+?)\n(.+?)(?=^##\s+|\Z)", text, flags=re.DOTALL | re.MULTILINE):
        sections[match.group(1).strip()] = match.group(2).strip()
    return sections


def structured_proposal_text(text: str) -> str:
    sections = extract_sections(text)
    values = [sections[name] for name in STRUCTURED_SECTIONS if sections.get(name)]
    return "\n".join(values) if values else salient_text(text)


def mechanism_text(entry: dict[str, Any]) -> str:
    values: list[str] = []
    for key in ["mechanism_id", "owning_skill", "activation_scenario", "behavior_change"]:
        value = entry.get(key)
        if isinstance(value, str):
            values.append(value)
    for key in ["failure_modes", "evidence"]:
        value = entry.get(key)
        if isinstance(value, list):
            values.extend(str(item) for item in value)
    return "\n".join(values)


def load_mechanisms(root: Path) -> list[dict[str, Any]]:
    path = root / "researcher" / "mechanisms" / "registry.jsonl"
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            entries.append(
                {
                    "mechanism_id": f"invalid-json-line-{line_number}",
                    "status": "invalid",
                    "activation_scenario": "",
                    "behavior_change": line,
                    "failure_modes": ["invalid registry entry"],
                }
            )
            continue
        if entry.get("status") in {"accepted", "candidate"}:
            entries.append(entry)
    return entries


def salient_text(text: str) -> str:
    """Keep the parts of a proposal most likely to contain real mechanism text."""
    section_names = [
        "Mechanism",
        "Proposed Delta",
        "Risks And Gaps",
        "Recommendation",
        "Core Concepts",
        "Detailed Topics",
        "Practical Guidance",
        "Guidelines",
        "Gotchas",
    ]
    chunks: list[str] = []
    for section in section_names:
        match = re.search(rf"^## {re.escape(section)}\n(.+?)(?:\n## |\Z)", text, flags=re.DOTALL | re.MULTILINE)
        if match:
            chunks.append(match.group(1))
    reduced = "\n".join(chunks) if chunks else text
    lines: list[str] = []
    for line in reduced.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- ["):
            continue
        if stripped in {"| --- | --- | --- |", "| --- | --- |"}:
            continue
        if "[Short Title]" in stripped or '""' in stripped:
            continue
        lines.append(stripped)
    return "\n".join(lines)


def corpus_documents(root: Path, exclude: Path | None = None) -> list[dict[str, str]]:
    docs: list[dict[str, str]] = []
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        if exclude and path.resolve() == exclude.resolve():
            continue
        docs.append({"path": str(path.relative_to(root)), "text": salient_text(path.read_text(encoding="utf-8"))})
    for path in sorted((root / "researcher" / "fixtures").glob("**/*.md")):
        if exclude and path.resolve() == exclude.resolve():
            continue
        docs.append({"path": str(path.relative_to(root)), "text": salient_text(path.read_text(encoding="utf-8"))})
    for path in sorted((root / "researcher" / "runs").glob("**/*.md")):
        if exclude and path.resolve() == exclude.resolve():
            continue
        if path.name == "skill-proposal.md":
            text = path.read_text(encoding="utf-8")
            if "Retrieval status: partial" in text or "[Short Title]" in text:
                continue
        docs.append({"path": str(path.relative_to(root)), "text": salient_text(path.read_text(encoding="utf-8"))})
    return docs


def main() -> int:
    parser = argparse.ArgumentParser(description="Check novelty of a skill proposal against corpus")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--text", help="proposal text to check")
    parser.add_argument("--file", type=Path, help="proposal file to check")
    parser.add_argument("--threshold", type=float, default=0.18)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    proposal = read_input(args)
    proposal_structured_text = structured_proposal_text(proposal)
    proposal_tokens = tokens(proposal_structured_text)

    mechanism_overlaps: list[dict[str, Any]] = []
    for entry in load_mechanisms(args.root):
        entry_tokens = tokens(mechanism_text(entry))
        score = jaccard(proposal_tokens, entry_tokens)
        if score > 0:
            mechanism_overlaps.append(
                {
                    "mechanism_id": entry.get("mechanism_id", ""),
                    "owning_skill": entry.get("owning_skill", ""),
                    "score": round(score, 4),
                    "shared_terms": sorted(proposal_tokens & entry_tokens)[:30],
                }
            )
    mechanism_overlaps.sort(key=lambda item: item["score"], reverse=True)

    overlaps: list[dict[str, Any]] = []
    exclude = args.file.resolve() if args.file else None
    for doc in corpus_documents(args.root, exclude=exclude):
        doc_tokens = tokens(doc["text"])
        score = jaccard(proposal_tokens, doc_tokens)
        shared = sorted(proposal_tokens & doc_tokens)[:30]
        if score > 0:
            overlaps.append({"path": doc["path"], "score": round(score, 4), "shared_terms": shared})
    overlaps.sort(key=lambda item: item["score"], reverse=True)

    max_mechanism_score = mechanism_overlaps[0]["score"] if mechanism_overlaps else 0.0
    max_corpus_score = overlaps[0]["score"] if overlaps else 0.0
    max_score = max(max_mechanism_score, max_corpus_score)
    verdict = "pass"
    if max_score >= args.threshold:
        verdict = "human_review"
    if max_score >= args.threshold * 1.75:
        verdict = "likely_duplicate"

    result = {
        "verdict": verdict,
        "threshold": args.threshold,
        "max_score": max_score,
        "max_mechanism_score": max_mechanism_score,
        "top_mechanism_overlaps": mechanism_overlaps[:10],
        "max_corpus_score": max_corpus_score,
        "top_overlaps": overlaps[:10],
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Novelty verdict: {verdict} (max overlap {max_score})")
        if mechanism_overlaps:
            print("Top mechanism overlaps:")
            for item in mechanism_overlaps[:5]:
                print(
                    f"- {item['mechanism_id']} ({item['owning_skill']}): "
                    f"{item['score']} shared={', '.join(item['shared_terms'][:8])}"
                )
        if overlaps:
            print("Top corpus overlaps:")
            for item in overlaps[:5]:
                print(f"- {item['path']}: {item['score']} shared={', '.join(item['shared_terms'][:8])}")

    return 0 if verdict == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
