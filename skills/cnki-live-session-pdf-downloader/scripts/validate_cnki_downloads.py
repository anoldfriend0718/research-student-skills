#!/usr/bin/env python3
"""Validate CNKI queue rows against downloaded PDF/CAJ files."""
from __future__ import annotations

import argparse
import csv
import pathlib
import re
import sys
import unicodedata
from collections import Counter


def sniff(path: pathlib.Path) -> tuple[str, bytes, int]:
    data = path.read_bytes()[:256]
    size = path.stat().st_size
    if data.startswith(b"%PDF-"):
        return "PDF", data[:16], size
    if data.startswith(b"CAJ") or data.startswith(b"KDH"):
        return "CAJ", data[:16], size
    if data.lstrip().startswith(b"<"):
        return "HTML", data[:16], size
    return "unknown", data[:16], size


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"[\s\W_]+", "", text, flags=re.UNICODE)


def text_matches_title(path: pathlib.Path, title: str) -> tuple[bool, str]:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as exc:
        return False, f"pypdf unavailable: {exc}"
    try:
        reader = PdfReader(str(path))
        text = "\n".join((page.extract_text() or "") for page in reader.pages[:3])
    except Exception as exc:
        return False, f"extract_error: {exc}"
    ntext = normalize(text)
    ntitle = normalize(title)
    if not ntitle:
        return True, "empty_title"
    ok = ntitle in ntext or (len(ntitle) >= 12 and ntitle[:12] in ntext) or (len(ntitle) >= 16 and ntitle[-12:] in ntext)
    sample = re.sub(r"\s+", " ", text)[:240]
    return ok, sample


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CNKI downloaded files and queue consistency.")
    parser.add_argument("--input-dir", required=True, help="Directory containing download_queue.tsv and downloaded files")
    parser.add_argument("--queue", default="download_queue.tsv", help="Queue TSV filename or path")
    parser.add_argument("--text-check", action="store_true", help="Try PDF title/text matching with pypdf")
    args = parser.parse_args()

    base = pathlib.Path(args.input_dir).resolve()
    queue_path = pathlib.Path(args.queue)
    if not queue_path.is_absolute():
        queue_path = base / queue_path
    if not queue_path.exists():
        print(f"ERROR queue not found: {queue_path}", file=sys.stderr)
        return 2

    with queue_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    status_counts = Counter(row.get("status", "") for row in rows)
    downloaded = [row for row in rows if row.get("status") == "downloaded"]
    problems: list[str] = []
    text_mismatches: list[str] = []
    seen: set[str] = set()

    for row in downloaded:
        idx = row.get("index", "")
        saved = row.get("saved_file", "")
        if not saved:
            problems.append(f"{idx}: downloaded row has empty saved_file")
            continue
        if saved in seen:
            problems.append(f"{idx}: duplicate saved_file {saved}")
        seen.add(saved)
        path = base / saved
        if not path.exists():
            problems.append(f"{idx}: missing file {saved}")
            continue
        fmt, head, size = sniff(path)
        if fmt not in {"PDF", "CAJ"}:
            problems.append(f"{idx}: bad header fmt={fmt} size={size} head={head!r} file={saved}")
            continue
        if size < 1024:
            problems.append(f"{idx}: suspiciously small file size={size} file={saved}")
        if args.text_check and fmt == "PDF":
            ok, sample = text_matches_title(path, row.get("title", ""))
            if not ok:
                text_mismatches.append(f"{idx}: title not found by text extraction; file={saved}; sample={sample}")

    for row in rows:
        if row.get("status") != "downloaded" and row.get("saved_file"):
            problems.append(f"{row.get('index','')}: non-downloaded row has saved_file {row.get('saved_file')}")

    root_pdf_count = len(list(base.glob("*.pdf")))
    print(f"rows={len(rows)}")
    print(f"status_counts={dict(status_counts)}")
    print(f"downloaded_rows={len(downloaded)}")
    print(f"root_pdf_count={root_pdf_count}")
    print(f"header_problem_count={len(problems)}")
    for problem in problems[:50]:
        print(f"PROBLEM {problem}")
    if args.text_check:
        print(f"text_mismatch_count={len(text_mismatches)}")
        for mismatch in text_mismatches[:50]:
            print(f"TEXT_CHECK {mismatch}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
