#!/usr/bin/env python3
"""Add sequential MathJax equation tags to Markdown display math blocks."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


TAG_RE = re.compile(r"\\tag\{[^}]+\}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add sequential \\tag{n} labels to $$...$$ display equations."
    )
    parser.add_argument("markdown", type=Path, help="Markdown file to process")
    parser.add_argument("--start", type=int, default=1, help="First equation number")
    parser.add_argument(
        "--in-place", action="store_true", help="Modify the Markdown file in place"
    )
    parser.add_argument("--output", type=Path, help="Write to this output file")
    parser.add_argument(
        "--backup-suffix",
        default=".before-equation-tags.md",
        help="Backup suffix used with --in-place",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Replace existing tags instead of leaving them unchanged",
    )
    return parser.parse_args()


def add_tag_to_block(block: list[str], number: int, replace_existing: bool) -> tuple[list[str], bool]:
    content = block[:]
    joined = "\n".join(content)
    has_tag = bool(TAG_RE.search(joined))
    if has_tag and not replace_existing:
        return content, False
    if replace_existing:
        content = [TAG_RE.sub("", line) for line in content]

    target_idx = None
    for idx in range(len(content) - 1, -1, -1):
        if content[idx].strip():
            target_idx = idx
            break
    if target_idx is None:
        return content, False

    content[target_idx] = content[target_idx].rstrip() + f"\\tag{{{number}}}"
    return content, True


def process(text: str, start: int, replace_existing: bool) -> tuple[str, int, int]:
    lines = text.splitlines(keepends=False)
    out: list[str] = []
    block: list[str] | None = None
    equation_index = 0
    changed = 0

    for line in lines:
        if line.strip() == "$$":
            if block is None:
                block = []
                out.append(line)
            else:
                equation_number = start + equation_index
                new_block, did_change = add_tag_to_block(
                    block, equation_number, replace_existing
                )
                out.extend(new_block)
                out.append(line)
                equation_index += 1
                if did_change:
                    changed += 1
                block = None
            continue

        if block is None:
            out.append(line)
        else:
            block.append(line)

    if block is not None:
        raise SystemExit("Unclosed display math block: missing closing $$")

    trailing_newline = "\n" if text.endswith("\n") else ""
    return "\n".join(out) + trailing_newline, equation_index, changed


def main() -> None:
    args = parse_args()
    source = args.markdown
    text = source.read_text(encoding="utf-8")
    new_text, total, changed = process(text, args.start, args.replace_existing)

    if args.in_place:
        backup = source.with_name(source.stem + args.backup_suffix)
        if not backup.exists():
            backup.write_text(text, encoding="utf-8")
        source.write_text(new_text, encoding="utf-8")
        destination = source
    elif args.output:
        args.output.write_text(new_text, encoding="utf-8")
        destination = args.output
    else:
        print(new_text, end="")
        destination = None

    print(
        f"display_blocks={total} changed={changed}"
        + (f" output={destination}" if destination else "")
    )


if __name__ == "__main__":
    main()
