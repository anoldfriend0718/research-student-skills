#!/usr/bin/env python3
"""Run strict Markdown conversion regression checks for a set of manuscripts."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run strict audit and optional Pandoc render checks on Markdown files."
    )
    parser.add_argument("markdown", nargs="+", type=Path, help="Markdown file(s) to test")
    parser.add_argument("--report", type=Path, help="Markdown report path")
    parser.add_argument("--html-dir", type=Path, help="Directory for rendered HTML files")
    parser.add_argument(
        "--pandoc",
        type=Path,
        help="Pandoc executable. If omitted, the script uses PATH when available.",
    )
    return parser.parse_args()


def run_command(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    output = "\n".join(part for part in [proc.stdout, proc.stderr] if part)
    return proc.returncode, output.rstrip()


def safe_name(path: Path, used: set[str]) -> str:
    stem = path.stem
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in stem)
    cleaned = cleaned[:80] or "manuscript"
    candidate = cleaned
    idx = 2
    while candidate in used:
        candidate = f"{cleaned}_{idx}"
        idx += 1
    used.add(candidate)
    return candidate


def find_pandoc(explicit: Path | None) -> str | None:
    if explicit:
        return str(explicit)
    found = shutil.which("pandoc")
    if found:
        return found
    return None


def main() -> None:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    audit_script = script_dir / "audit_markdown_conversion.py"
    pandoc = find_pandoc(args.pandoc)

    report_lines = [
        "# Word-to-Markdown Academic Regression Report",
        "",
        f"generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]
    html_dir = args.html_dir
    if html_dir:
        html_dir.mkdir(parents=True, exist_ok=True)

    all_ok = True
    used_names: set[str] = set()
    for markdown in args.markdown:
        report_lines.append(f"## {markdown.name}")
        report_lines.append(f"path: {markdown}")
        if not markdown.exists():
            report_lines.append("status: FAIL missing file")
            report_lines.append("")
            all_ok = False
            continue

        stat = markdown.stat()
        report_lines.append(f"bytes: {stat.st_size}")
        report_lines.append(
            f"mtime: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}"
        )

        audit_code, audit_output = run_command(
            [sys.executable, str(audit_script), "--strict", str(markdown)]
        )
        report_lines.append(f"strict_audit_exit: {audit_code}")
        report_lines.append("strict_audit_output:")
        report_lines.extend(f"  {line}" for line in audit_output.splitlines())
        if audit_code != 0:
            all_ok = False

        if html_dir:
            if not pandoc:
                report_lines.append("pandoc_exit: SKIPPED missing pandoc")
                all_ok = False
            else:
                html_name = safe_name(markdown, used_names) + ".html"
                html_path = html_dir / html_name
                pandoc_code, pandoc_output = run_command(
                    [pandoc, str(markdown), "-s", "--mathjax", "-o", str(html_path)]
                )
                report_lines.append(f"pandoc_exit: {pandoc_code}")
                if html_path.exists():
                    report_lines.append(f"html: {html_path}")
                    report_lines.append(f"html_bytes: {html_path.stat().st_size}")
                else:
                    report_lines.append("html: MISSING")
                if pandoc_output:
                    report_lines.append("pandoc_output:")
                    report_lines.extend(f"  {line}" for line in pandoc_output.splitlines())
                if pandoc_code != 0 or not html_path.exists():
                    all_ok = False
        report_lines.append("")

    report_lines.append(f"overall: {'PASS' if all_ok else 'FAIL'}")
    report = "\n".join(report_lines) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8", newline="\n")
    print(report)
    raise SystemExit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
