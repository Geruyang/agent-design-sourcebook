#!/usr/bin/env python3
"""Deterministic validation for the Long-Horizon Prompting static site."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


LAB = Path(__file__).resolve().parent.parent
UI = LAB / "ui"
REPO = LAB.parents[1]
PAGES = ["index.html", "guide.html", "lab.html", "references.html", "404.html"]
PRIMARY_PAGES = PAGES[:-1]
REQUIRED_NAV = {"index.html", "guide.html", "lab.html", "references.html"}


class DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.links: list[str] = []
        self.assets: list[str] = []
        self.scripts: list[str] = []
        self.h1_count = 0
        self.title = ""
        self.meta: dict[str, str] = {}
        self.current_title = False
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs_raw: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in attrs_raw}
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        if tag in {"link", "img", "script"}:
            key = "href" if tag == "link" else "src"
            if attrs.get(key):
                self.assets.append(attrs[key])
        if tag == "script" and attrs.get("src"):
            self.scripts.append(attrs["src"])
        if tag == "h1":
            self.h1_count += 1
        if tag == "title":
            self.current_title = True
        if tag == "meta":
            key = attrs.get("name") or attrs.get("property") or attrs.get("http-equiv")
            if key:
                self.meta[key.lower()] = attrs.get("content", "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.current_title = False

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self.text_parts.append(stripped)
            if self.current_title:
                self.title += stripped


def is_external(value: str) -> bool:
    return urlparse(value).scheme in {"http", "https", "mailto"}


def local_target(page: Path, value: str) -> Path | None:
    if not value or value.startswith("#") or is_external(value) or value.startswith("data:"):
        return None
    clean = value.split("#", 1)[0].split("?", 1)[0]
    if not clean:
        return None
    project_prefix = "/Agent-Skills-for-Context-Engineering/"
    if clean.startswith(project_prefix):
        suffix = clean[len(project_prefix):] or "index.html"
        return (UI / suffix).resolve()
    return (page.parent / clean).resolve()


def parse_page(path: Path) -> DocumentParser:
    parser = DocumentParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def validate() -> list[str]:
    errors: list[str] = []
    parsed: dict[str, DocumentParser] = {}

    for filename in PAGES:
        path = UI / filename
        if not path.exists():
            errors.append(f"{filename}: missing")
            continue
        doc = parse_page(path)
        parsed[filename] = doc

        if doc.h1_count != 1:
            errors.append(f"{filename}: expected one h1, found {doc.h1_count}")
        if not doc.title:
            errors.append(f"{filename}: missing title")
        duplicates = sorted({item for item in doc.ids if doc.ids.count(item) > 1})
        if duplicates:
            errors.append(f"{filename}: duplicate ids {duplicates}")
        if filename in PRIMARY_PAGES:
            for key in ("description", "content-security-policy", "og:title", "og:url", "og:image"):
                if not doc.meta.get(key):
                    errors.append(f"{filename}: missing metadata {key}")
            canonical = [
                href for href in doc.assets
                if "muratcankoylan.github.io/Agent-Skills-for-Context-Engineering" in href
            ]
            if not canonical:
                errors.append(f"{filename}: missing project-path canonical URL")

        for value in doc.links + doc.assets:
            target = local_target(path, value)
            if target is not None and not target.exists():
                errors.append(f"{filename}: broken local reference {value}")

        nav_targets: set[str] = set()
        for value in doc.links:
            clean = value.split("#", 1)[0]
            if clean in REQUIRED_NAV:
                nav_targets.add(clean)
                continue
            project_prefix = "/Agent-Skills-for-Context-Engineering/"
            if clean.startswith(project_prefix):
                basename = "index.html" if clean == project_prefix else Path(clean).name
                if basename in REQUIRED_NAV:
                    nav_targets.add(basename)
                continue
            parsed_link = urlparse(clean)
            if parsed_link.netloc == "muratcankoylan.github.io":
                normalized_path = parsed_link.path.rstrip("/")
                basename = (
                    "index.html"
                    if normalized_path.endswith("/Agent-Skills-for-Context-Engineering")
                    else Path(normalized_path).name
                )
                if basename in REQUIRED_NAV:
                    nav_targets.add(basename)
        if nav_targets != REQUIRED_NAV:
            errors.append(f"{filename}: incomplete primary navigation {sorted(nav_targets)}")

    lab = parsed.get("lab.html")
    if lab and lab.scripts != ["site.js", "data.js", "app.js"]:
        errors.append(f"lab.html: script order must be site.js, data.js, app.js; got {lab.scripts}")

    references = parsed.get("references.html")
    if references:
        external_sources = [
            link for link in references.links
            if link.startswith("https://") and "github.com" not in link
        ]
        if len(set(external_sources)) < 25:
            errors.append(
                f"references.html: expected at least 25 external sources, found {len(set(external_sources))}"
            )
        text = " ".join(references.text_parts).lower()
        for phrase in ("unreviewed", "no component ablation", "vendor", "preprint"):
            if phrase not in text:
                errors.append(f"references.html: missing evidence caveat {phrase!r}")

    sitemap = UI / "sitemap.xml"
    try:
        root = ET.parse(sitemap).getroot()
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = {node.text for node in root.findall("s:url/s:loc", ns)}
        for page in PRIMARY_PAGES:
            suffix = "" if page == "index.html" else page
            expected = f"https://muratcankoylan.github.io/Agent-Skills-for-Context-Engineering/{suffix}"
            if expected not in locations:
                errors.append(f"sitemap.xml: missing {expected}")
    except (ET.ParseError, OSError) as exc:
        errors.append(f"sitemap.xml: {exc}")

    site_js = (UI / "site.js").read_text(encoding="utf-8")
    install_ref = re.search(r'INSTALL_REF = "([0-9a-f]+)"', site_js)
    if not install_ref or len(install_ref.group(1)) != 40:
        errors.append("site.js: install command must pin a full 40-character commit")

    rubric_source = (
        REPO / "skills" / "long-horizon-prompting" / "references" / "task-brief-template.md"
    )
    source_rows: list[tuple[str, str]] = []
    for line in rubric_source.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\| \d+ \| ([^|]+) \| ([^|]+) \|", line)
        if match:
            source_rows.append((match.group(1).strip(), match.group(2).strip().rstrip(".")))
    prompt_data = json.loads((LAB / "data" / "prompt-pairs.json").read_text(encoding="utf-8"))
    site_rows = [
        (row["name"].strip(), row["two"].strip().rstrip("."))
        for row in prompt_data.get("rubric", [])
    ]
    if site_rows != source_rows:
        errors.append("prompt rubric drifted from references/task-brief-template.md")

    for required in ("favicon.svg", "robots.txt", "styles.css", "site.js", "data.js", "app.js"):
        if not (UI / required).exists():
            errors.append(f"ui/{required}: missing")

    prompt_files = sorted((UI / "prompts").glob("*.txt")) if (UI / "prompts").exists() else []
    if len(prompt_files) != 8:
        errors.append(f"ui/prompts: expected 8 generated prompt files, found {len(prompt_files)}")
    for prompt_file in prompt_files:
        if len(prompt_file.read_text(encoding="utf-8").split()) < 50:
            errors.append(f"{prompt_file.relative_to(UI)}: unexpectedly short")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "Site validation passed: "
        f"{len(PAGES)} pages, complete navigation, metadata, local links, references, and sitemap"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
