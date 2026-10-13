#!/usr/bin/env python3
"""Validate publish readiness for a single research run.

This complements validate_repo.py. Repo validation answers whether the corpus is
structurally healthy; run validation answers whether one run is ready to produce
reviewable corpus changes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
VALID_STATES = {
    "initialized",
    "retrieved",
    "evaluated",
    "proposed",
    "novelty_checked",
    "validated",
    "pr_ready",
    "closed",
}
VALID_CLOSE_STATUS = {"accepted", "rejected", "reference-only", "abandoned"}
PLACEHOLDER_PATTERNS = [
    r"\[Short Title\]",
    r"Describe the implementable mechanism",
    r"State one of:",
    r'path: ""',
    r'section: ""',
    r'summary: ""',
    r"Verdict: pending",
]


@dataclass
class Finding:
    severity: str
    path: str
    message: str


class RunValidator:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir.resolve()
        self.root = ROOT.resolve()
        self.findings: list[Finding] = []

    def rel(self, path: Path | str) -> str:
        p = Path(path)
        try:
            return str(p.relative_to(self.root))
        except ValueError:
            return str(p)

    def error(self, path: Path | str, message: str) -> None:
        self.findings.append(Finding("error", self.rel(path), message))

    def warn(self, path: Path | str, message: str) -> None:
        self.findings.append(Finding("warning", self.rel(path), message))

    def run(self) -> dict[str, Any]:
        if not self.run_dir.exists():
            self.error(self.run_dir, "run directory missing")
        else:
            state_data = self.validate_state()
            current_state = (state_data or {}).get("current_state")
            if current_state == "closed":
                # Closed runs are terminal. validate_run only enforces publish
                # readiness for active runs; closed runs are validated by their
                # own closure.json plus repo-level checks.
                self.validate_closure()
            else:
                self.validate_queue()
                source_status = self.validate_source_evaluation()
                self.validate_proposal(source_status)
                self.validate_novelty()
                self.validate_pr_readiness()
                self.validate_closure()

        errors = sum(1 for finding in self.findings if finding.severity == "error")
        warnings = sum(1 for finding in self.findings if finding.severity == "warning")
        return {
            "ok": errors == 0,
            "run_dir": self.rel(self.run_dir),
            "summary": {"errors": errors, "warnings": warnings},
            "findings": [asdict(finding) for finding in self.findings],
        }

    def validate_state(self) -> dict[str, Any] | None:
        path = self.run_dir / "run-state.json"
        data = self.load_json(path)
        if not isinstance(data, dict):
            return None
        current = data.get("current_state")
        if current not in VALID_STATES:
            self.error(path, f"current_state must be one of {sorted(VALID_STATES)}")
        if not isinstance(data.get("state_history"), list) or not data["state_history"]:
            self.error(path, "state_history must be a non-empty list")
        locked = data.get("locked_surfaces", [])
        for required in [
            "researcher/rubrics/content-curation.md",
            "researcher/mechanisms/registry.jsonl",
            ".claude-plugin/marketplace.json",
            ".plugin/plugin.json",
        ]:
            if required not in locked:
                self.error(path, f"locked surface missing: {required}")
        return data

    def validate_queue(self) -> None:
        queue = self.run_dir / "sources" / "queue.jsonl"
        if not queue.exists():
            self.error(queue, "source queue missing")
            return
        for line_number, line in enumerate(queue.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                self.error(queue, f"line {line_number} invalid JSONL: {exc}")
                continue
            if not record.get("id") or not record.get("title"):
                self.error(queue, f"line {line_number} must include id and title")

    def validate_source_evaluation(self) -> str | None:
        eval_dir = self.run_dir / "sources" / "evaluations"
        if not eval_dir.exists():
            self.error(eval_dir, "source evaluations directory missing")
            return None
        completed = sorted(path for path in eval_dir.glob("*.json") if "draft" not in path.stem)
        drafts = sorted(eval_dir.glob("*draft*.json"))
        if drafts and not completed:
            self.error(eval_dir, "run has only draft source evaluations")
            return None
        if not completed:
            self.error(eval_dir, "completed source evaluation missing")
            return None

        data = self.load_json(completed[0])
        if not isinstance(data, dict):
            return None
        status = data.get("source", {}).get("retrieval_status")
        if status != "retrieved":
            self.error(completed[0], "publish-ready run requires retrieved source evaluation")
        if data.get("decision", {}).get("verdict") == "REJECT":
            self.error(completed[0], "rejected source cannot produce publish-ready changes")
        return str(status) if status else None

    def validate_proposal(self, source_status: str | None) -> None:
        path = self.run_dir / "proposals" / "skill-proposal.md"
        if not path.exists():
            self.error(path, "skill proposal missing")
            return
        text = path.read_text(encoding="utf-8")
        for pattern in PLACEHOLDER_PATTERNS:
            if re.search(pattern, text):
                self.error(path, f"proposal still contains placeholder: {pattern}")
        required_prefixes = [
            "- URL:",
            "- Title:",
            "- Author or organization:",
            "- Source type:",
            "- Retrieval status:",
            "- Evaluation file:",
            "- Decision:",
            "- Target path:",
            "- Activation scenario:",
            "- Verdict:",
            "- Max mechanism overlap:",
            "- Top mechanism overlaps:",
            "- Evidence limitations:",
            "- Possible duplication:",
            "- Required human review:",
        ]
        for prefix in required_prefixes:
            if re.search(rf"^{re.escape(prefix)}\s*$", text, flags=re.MULTILINE):
                self.error(path, f"proposal field is blank: {prefix}")
        has_evidence_row = False
        for line in text.splitlines()[30:]:
            if not line.startswith("|") or line.count("|") < 3:
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if not cells or cells[0] in {"Claim", "---"} or set("".join(cells)) <= {"-", " "}:
                continue
            if any(cells):
                has_evidence_row = True
                break
        if source_status != "retrieved" and has_evidence_row:
            self.error(path, "proposal cites evidence from a source that is not fully retrieved")

    def validate_novelty(self) -> None:
        path = self.run_dir / "reports" / "novelty-result.json"
        data = self.load_json(path)
        if not isinstance(data, dict):
            return
        verdict = data.get("verdict")
        if verdict not in {"pass", "human_review", "likely_duplicate"}:
            self.error(path, "novelty verdict is invalid")
        if verdict != "pass" and not data.get("human_review_rationale"):
            self.error(path, "non-pass novelty verdict requires human_review_rationale")

    def validate_pr_readiness(self) -> None:
        path = self.run_dir / "reports" / "pr-readiness.md"
        if not path.exists():
            self.error(path, "PR readiness notes missing")
            return
        text = path.read_text(encoding="utf-8")
        for required in ["## Summary", "## Test Plan", "## Risks", "human approval"]:
            if required not in text:
                self.error(path, f"PR readiness notes missing {required}")

    def validate_closure(self) -> None:
        path = self.run_dir / "reports" / "closure.json"
        if not path.exists():
            return
        data = self.load_json(path)
        if not isinstance(data, dict):
            return
        if data.get("status") not in VALID_CLOSE_STATUS:
            self.error(path, f"closure status must be one of {sorted(VALID_CLOSE_STATUS)}")
        if not data.get("reason"):
            self.error(path, "closure reason is required")

    def load_json(self, path: Path) -> Any:
        if not path.exists():
            self.error(path, "JSON file missing")
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            self.error(path, f"invalid JSON: {exc}")
            return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate publish readiness for a research run")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = RunValidator(args.run_dir).run()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        summary = result["summary"]
        print(
            f"Run validation {'passed' if result['ok'] else 'failed'}: "
            f"{summary['errors']} errors, {summary['warnings']} warnings"
        )
        for finding in result["findings"]:
            print(f"[{finding['severity']}] {finding['path']}: {finding['message']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
