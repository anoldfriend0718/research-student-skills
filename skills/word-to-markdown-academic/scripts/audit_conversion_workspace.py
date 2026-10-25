#!/usr/bin/env python3
"""Audit that DOCX-to-Markdown conversion artifacts are kept in the work directory."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PROCESS_FILE_RE = re.compile(
    r"(?:\.before-|before-|audit-|formula_candidates|formula_gap_report|"
    r"equation-blocks|manifest\.agent-|\.todo\.json|\.tmp)",
    re.I,
)
VECTOR_MEDIA_EXTS = {".wmf", ".emf", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report conversion process files outside the designated work directory."
    )
    parser.add_argument("--main-dir", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument(
        "--final-markdown",
        default="liu-zhiying-thesis-refined.md",
        help="Allowed final Markdown basename in the main directory.",
    )
    parser.add_argument("--json-report", type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def is_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def main() -> None:
    args = parse_args()
    main_dir = args.main_dir.resolve()
    work_dir = args.work_dir.resolve()
    allowed_top = {args.final_markdown, "media", "_conversion_work"}
    issues: list[str] = []

    for item in main_dir.iterdir():
        if item.name in allowed_top:
            continue
        if PROCESS_FILE_RE.search(item.name):
            issues.append(f"top_level_process_artifact: {item.name}")
        else:
            issues.append(f"top_level_unexpected_item: {item.name}")

    if not is_inside(work_dir, main_dir / "_conversion_work"):
        issues.append(f"work_dir_not_under_conversion_work: {work_dir}")

    media_dir = main_dir / "media"
    if media_dir.exists():
        for item in media_dir.iterdir():
            if item.is_file() and item.suffix.lower() in VECTOR_MEDIA_EXTS:
                issues.append(f"raw_vector_media_in_final_media: {item.name}")

    for issue in issues:
        print(f"- {issue}")
    if not issues:
        print("workspace_artifacts=clean")

    if args.json_report:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(
            json.dumps(
                {"main_dir": str(main_dir), "work_dir": str(work_dir), "issues": issues},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    raise SystemExit(1 if args.strict and issues else 0)


if __name__ == "__main__":
    main()
