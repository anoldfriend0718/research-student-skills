#!/usr/bin/env python3
"""Restore display equations in fresh Markdown from a known-good baseline."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import unquote


MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
HTML_IMAGE_RE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"'][^>]*>", re.I)
DISPLAY_MATH_RE = re.compile(r"(?ms)^\$\$\s*$.*?^\$\$\s*$")
TAG_RE = re.compile(r"\\tag\{([^}]+)\}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replace formula-image placeholders in fresh Markdown with display "
            "equations extracted from a known-good Markdown baseline."
        )
    )
    parser.add_argument("--fresh", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument(
        "--allow-unmatched",
        action="store_true",
        help="Write output even when candidate/equation counts do not match exactly.",
    )
    return parser.parse_args()


def normalize_image_target(raw: str) -> str:
    target = raw.strip().strip("<>").strip()
    if (target.startswith('"') and target.endswith('"')) or (
        target.startswith("'") and target.endswith("'")
    ):
        target = target[1:-1]
    return unquote(target)


def line_images(line: str) -> list[str]:
    targets = [normalize_image_target(match.group(1)) for match in MARKDOWN_IMAGE_RE.finditer(line)]
    targets.extend(normalize_image_target(match.group(1)) for match in HTML_IMAGE_RE.finditer(line))
    return targets


def previous_nonblank(lines: list[str], idx: int) -> str:
    for pos in range(idx - 1, -1, -1):
        if lines[pos].strip():
            return lines[pos].strip()
    return ""


def next_nonblank(lines: list[str], idx: int) -> str:
    for pos in range(idx + 1, len(lines)):
        if lines[pos].strip():
            return lines[pos].strip()
    return ""


def is_markdown_image_only(line: str) -> bool:
    return bool(re.fullmatch(r"\s*(?:!\[[^\]]*\]\([^)]+\)\s*)+\s*", line))


def has_equation_number(line: str) -> bool:
    return bool(
        re.search(r"\\\(([A-Za-z]?\d+[A-Za-z]?)\\\)", line)
        or re.search(r"(?<![A-Za-z])\(([A-Za-z]?\d+[A-Za-z]?)\)(?![A-Za-z])", line)
    )


def is_figure_context(line: str, prev_line: str, next_line: str, in_figure: bool) -> bool:
    stripped = line.strip()
    return (
        in_figure
        or stripped.startswith("<figure")
        or stripped.startswith("<figcaption")
        or re.match(r"^(Fig\.|Figure|Table)\s+", stripped, re.I) is not None
        or re.match(r"^(Fig\.|Figure)\s+", next_line, re.I) is not None
        or "<figcaption" in next_line
        or "<figure" in prev_line
    )


def is_formula_candidate(line: str, prev_line: str, next_line: str, in_figure: bool) -> bool:
    if not line_images(line):
        return False
    if is_figure_context(line, prev_line, next_line, in_figure):
        return False
    if has_equation_number(line):
        return True
    if is_markdown_image_only(line) and (
        next_line.lower().startswith("where")
        or (prev_line.endswith(":") and not re.search(r"\b(?:fig\.|figure|table)\b", prev_line, re.I))
    ):
        return True
    return False


def extract_equations(baseline: Path) -> list[str]:
    text = baseline.read_text(encoding="utf-8")
    equations = [match.group(0).strip() for match in DISPLAY_MATH_RE.finditer(text)]
    return equations


def candidate_indices(lines: list[str]) -> list[int]:
    indices: list[int] = []
    in_figure = False
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("<figure"):
            in_figure = True
        prev_line = previous_nonblank(lines, idx)
        next_line = next_nonblank(lines, idx)
        if is_formula_candidate(line, prev_line, next_line, in_figure):
            indices.append(idx)
        if stripped.startswith("</figure"):
            in_figure = False
    return indices


def is_empty_pipe_row(line: str) -> bool:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return False
    core = stripped.strip("|").strip()
    return not core or re.fullmatch(r"[:\-\s|]+", core) is not None


def is_horizontal_artifact(line: str) -> bool:
    stripped = line.strip()
    return (
        re.fullmatch(r"-{6,}", stripped) is not None
        or re.fullmatch(r"\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?", stripped) is not None
        or is_empty_pipe_row(line)
    )


def restore_formulas(
    lines: list[str],
    indices: list[int],
    equations: list[str],
    drop_extra_candidates: bool = False,
) -> tuple[list[str], int, int]:
    output: list[str] = []
    index_set = set(indices)
    replacement_for: dict[int, str] = {}
    replace_count = min(len(indices), len(equations))
    for pos, idx in enumerate(indices[:replace_count]):
        replacement_for[idx] = equations[pos]
    if len(equations) > len(indices) and indices:
        last_idx = indices[-1]
        extra = "\n\n".join(equations[len(indices) :])
        replacement_for[last_idx] = replacement_for[last_idx] + "\n\n" + extra

    restored = 0
    removed_extra = 0
    for idx, line in enumerate(lines):
        if idx in replacement_for:
            while output and is_horizontal_artifact(output[-1]):
                output.pop()
            block = replacement_for[idx].strip()
            if output and output[-1].strip():
                output.append("")
            output.extend(block.splitlines())
            output.append("")
            restored += block.count("$$") // 2
            continue
        if idx in index_set:
            if drop_extra_candidates:
                while output and is_horizontal_artifact(output[-1]):
                    output.pop()
                if output and output[-1].strip():
                    output.append("")
                removed_extra += 1
                continue
            # Extra formula-like image beyond the available baseline equations. Keep it.
            output.append(line)
            continue
        if output and output[-1] == "" and is_horizontal_artifact(line):
            continue
        output.append(line)
    return output, restored, removed_extra


def main() -> None:
    args = parse_args()
    fresh = args.fresh.resolve()
    baseline = args.baseline.resolve()
    equations = extract_equations(baseline)
    lines = fresh.read_text(encoding="utf-8").splitlines()
    indices = candidate_indices(lines)
    if not args.allow_unmatched and len(indices) != len(equations):
        raise SystemExit(
            f"candidate/equation count mismatch: candidates={len(indices)} equations={len(equations)}"
        )
    restored_lines, restored, removed_extra = restore_formulas(
        lines,
        indices,
        equations,
        drop_extra_candidates=args.allow_unmatched and len(indices) > len(equations),
    )
    text = "\n".join(restored_lines).replace("\n\n\n", "\n\n").rstrip() + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8", newline="\n")
    print(f"output={args.output}")
    print(f"baseline_equations={len(equations)}")
    print(f"formula_candidates={len(indices)}")
    print(f"restored_equations={restored}")
    print(f"removed_extra_candidates={removed_extra}")
    if len(indices) != len(equations):
        print(f"warning=count_mismatch candidates={len(indices)} equations={len(equations)}")


if __name__ == "__main__":
    main()
