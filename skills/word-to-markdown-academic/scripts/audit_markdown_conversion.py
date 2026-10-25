#!/usr/bin/env python3
"""Audit Markdown generated from academic DOCX manuscripts."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote


IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
HTML_IMAGE_RE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"'][^>]*>", re.I)
TAG_RE = re.compile(r"\\tag\{[^}]+\}")
INLINE_MATH_RE = re.compile(r"(?<!\\)\$([^$\n]+?)(?<!\\)\$")
TABLE_SYMBOL_RE = re.compile(
    r"\|.*(?:\*[A-Za-z\u0370-\u03ff][A-Za-z0-9\u0370-\u03ff]?\*|\*[A-Za-z\u0370-\u03ff]\*~[A-Za-z0-9\u0370-\u03ff]+~)"
)
ESCAPED_LINKED_CITATION_RE = re.compile(
    r"\\\[(?:\[[0-9]+\]\(#[^)]+\))(?:\s*[,，;；、–—-]\s*\[[0-9]+\]\(#[^)]+\))*\\\]"
)
SUSPICIOUS_PATTERNS = {
    "data_uri": re.compile(r"data:image", re.I),
    "wmf": re.compile(r"image/x-wmf|\.wmf\b", re.I),
    "emf": re.compile(r"\.emf\b", re.I),
    "tiff": re.compile(r"\.tiff?\b", re.I),
    "word_anchor_residue": re.compile(
        r"_Toc\d+|_Ref\d+|\[\]\{#_(?:Toc|Ref)\d+\s+\.anchor\}|"
        r"<span\s+id=[\"']_(?:Toc|Ref)\d+[\"']\s+class=[\"']anchor[\"']",
        re.I,
    ),
    "image_size_attr": re.compile(r"\{[^}]*\b(?:width|height)=", re.I),
    "html_size_attr": re.compile(
        r"\b(?:width|height)=\"[^\"]+\"|style=\"[^\"]*(?:width|height)[^\"]*\"", re.I
    ),
    "grid_table_border": re.compile(r"^\+[-=+ :]+\+\s*$", re.M),
    "simple_table_border": re.compile(r"^\s*-{5,}(?:\s+-{3,})*\s*$", re.M),
    "formula_image_number": re.compile(
        r"!\[[^\]]*\]\([^)]+\)\s*(?:\[\]\{#_Ref\d+\s+\.anchor\})?\(?\d+-\d*\)?"
    ),
    "escaped_numeric_citation": re.compile(r"\\\[[0-9, -]+\\\]"),
    "escaped_linked_citation": ESCAPED_LINKED_CITATION_RE,
    "escaped_reference_type": re.compile(r"\\\[[A-Za-z]\\\]"),
    "escaped_underscore": re.compile(r"\\_"),
    "italic_symbol_fragment": re.compile(r"(?<!\*)\*[A-Za-z][A-Za-z0-9]?\*(?!\*)"),
    "control_character": re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]"),
    "inline_adjacent_math": re.compile(r"(?m)^(?!\s*\$\$\s*$).*\$\$.*$"),
    "inline_double_subscript": re.compile(r"\$[^$\n]*_\{[^{}]*\}_\{[^$\n]*\$"),
    "math_html_subsup_fragment": re.compile(
        r"(?<!\*)\*[^*\n]+\*(?:<sub>|<sup>)|"
        r"(?<!\*)\*[^*\n]*(?:<sub>|<sup>)[^*\n]*\*(?!\*)|"
        r"\*\*\*[^*\n]*(?:<sub>|<sup>)|"
        r"\$[^$\n]+\$(?:<sub>|<sup>)",
        re.I,
    ),
    "literal_katex_error": re.compile(r"ParseError|KaTeX"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit DOCX-derived Markdown.")
    parser.add_argument("markdown", type=Path, help="Markdown file to audit")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any warning, not only hard conversion errors.",
    )
    parser.add_argument(
        "--formula-manifest",
        type=Path,
        help="Verified formula manifest that should be fully consumed by the final Markdown.",
    )
    parser.add_argument(
        "--json-report",
        type=Path,
        help="Write machine-readable audit results.",
    )
    return parser.parse_args()


def normalize_image_target(raw: str) -> str:
    target = raw.strip().strip("<>").strip()
    if (target.startswith('"') and target.endswith('"')) or (
        target.startswith("'") and target.endswith("'")
    ):
        target = target[1:-1]
    return unquote(target)


def audit_images(path: Path, text: str) -> list[str]:
    issues: list[str] = []
    targets: list[tuple[int, str]] = []
    lines = text.splitlines()
    for line_no, line in enumerate(lines, start=1):
        matches = [(match, 1) for match in IMAGE_RE.finditer(line)]
        matches.extend((match, 1) for match in HTML_IMAGE_RE.finditer(line))
        for match, group_idx in matches:
            target = normalize_image_target(match.group(group_idx))
            targets.append((line_no, target))
            lower = target.lower()
            if lower.startswith("data:"):
                issues.append(f"L{line_no}: image uses data URI")
                continue
            if "image/x-wmf" in lower or lower.endswith(".wmf"):
                issues.append(f"L{line_no}: image uses unresolved WMF target: {target}")
                continue
            if lower.endswith(".emf") or lower.endswith(".tif") or lower.endswith(".tiff"):
                issues.append(f"L{line_no}: image uses unresolved vector/raster target: {target}")
                continue
            if re.match(r"^[a-z][a-z0-9+.-]*:", lower):
                continue
            local = (path.parent / target).resolve()
            if not local.exists():
                issues.append(f"L{line_no}: local image target missing: {target}")

    counts = Counter(target for _, target in targets)
    for target, count in sorted(counts.items()):
        if count > 1:
            issues.append(f"image target repeated {count} times: {target}")

    return issues


def audit_equations(text: str) -> list[str]:
    issues: list[str] = []
    lines = text.splitlines()
    in_block = False
    block_start = 0
    block_lines: list[str] = []
    block_count = 0
    tagged_count = 0

    for line_no, line in enumerate(lines, start=1):
        if line.strip() == "$$":
            if not in_block:
                in_block = True
                block_start = line_no
                block_lines = []
            else:
                block_count += 1
                block_text = "\n".join(block_lines)
                if TAG_RE.search(block_text):
                    tagged_count += 1
                else:
                    issues.append(f"L{block_start}: display equation has no \\tag{{n}}")
                in_block = False
            continue
        if in_block:
            block_lines.append(line)

    if in_block:
        issues.append(f"L{block_start}: unclosed display equation block")
    issues.append(f"equation_blocks={block_count}; tagged_blocks={tagged_count}")
    return issues


def load_formula_manifest(path: Path | None) -> dict[str, dict[str, object]]:
    if not path:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    formulas = data.get("formulas", data)
    if not isinstance(formulas, dict):
        raise ValueError("formula manifest must be a mapping or contain a 'formulas' mapping")
    normalized: dict[str, dict[str, object]] = {}
    for raw_key, raw_value in formulas.items():
        if not isinstance(raw_value, dict):
            normalized[normalize_image_target(str(raw_key))] = {"status": "invalid"}
            continue
        normalized[normalize_image_target(str(raw_key))] = raw_value
    return normalized


def audit_formula_manifest(text: str, manifest: dict[str, dict[str, object]]) -> list[str]:
    if not manifest:
        return []
    issues: list[str] = []
    display_tags: dict[str, str] = {}
    verified = 0
    for target, item in sorted(manifest.items()):
        status = str(item.get("status", "verified")).lower()
        kind = str(item.get("kind", ""))
        tag = str(item.get("tag", ""))
        latex = str(item.get("latex", "")).strip()
        if status not in {"verified", "accepted"}:
            issues.append(f"formula_manifest_unverified: {target} status={status}")
            continue
        verified += 1
        if not latex:
            issues.append(f"formula_manifest_missing_latex: {target}")
        if kind == "display":
            if not tag:
                issues.append(f"formula_manifest_missing_tag: {target}")
            elif tag in display_tags:
                issues.append(f"formula_manifest_duplicate_tag: {tag} in {display_tags[tag]} and {target}")
            else:
                display_tags[tag] = target
            if tag and rf"\tag{{{tag}}}" not in text:
                issues.append(f"formula_manifest_tag_not_rendered: {target} tag={tag}")
        consumed_targets: list[str] = []
        if isinstance(item.get("targets"), list):
            consumed_targets.extend(str(value) for value in item["targets"])  # type: ignore[index]
        elif item.get("target"):
            consumed_targets.append(str(item["target"]))
        elif not target.startswith(("compound:", "occurrence:")):
            consumed_targets.append(target)
        for consumed_target in consumed_targets:
            if f"]({consumed_target})" in text:
                issues.append(f"formula_manifest_target_unconsumed: {consumed_target}")
    issues.append(
        f"formula_manifest_verified_entries={verified}; display_entries={len(display_tags)}"
    )
    return issues


def audit_text_patterns(text: str) -> list[str]:
    issues: list[str] = []
    for name, pattern in SUSPICIOUS_PATTERNS.items():
        line_hits: list[int] = []
        total = 0
        for line_no, line in enumerate(text.splitlines(), start=1):
            found = list(pattern.finditer(line))
            if found:
                total += len(found)
                line_hits.append(line_no)
        if total:
            preview = ", ".join(str(line_no) for line_no in line_hits[:10])
            suffix = "" if len(line_hits) <= 10 else ", ..."
            issues.append(f"{name}: {total} match(es); lines {preview}{suffix}")

    line_hits = []
    total = 0
    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in INLINE_MATH_RE.finditer(line):
            if match.end() < len(line) and re.match(r"[A-Za-z]", line[match.end()]):
                total += 1
                line_hits.append(line_no)
    if total:
        preview = ", ".join(str(line_no) for line_no in line_hits[:10])
        suffix = "" if len(line_hits) <= 10 else ", ..."
        issues.append(f"math_touching_word: {total} match(es); lines {preview}{suffix}")
    return issues


def audit_table_symbols(text: str) -> list[str]:
    line_hits = [
        line_no
        for line_no, line in enumerate(text.splitlines(), start=1)
        if TABLE_SYMBOL_RE.search(line)
    ]
    if not line_hits:
        return []
    preview = ", ".join(str(line_no) for line_no in line_hits[:10])
    suffix = "" if len(line_hits) <= 10 else ", ..."
    return [f"table_symbol_fragment: {len(line_hits)} line(s); lines {preview}{suffix}"]


def pipe_table_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def is_pipe_table_delimiter(cells: list[str] | None) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-+:?", cell) for cell in cells)


def audit_pipe_table_structure(text: str) -> list[str]:
    """Reject malformed pipe-table delimiters that render as prose or emoji."""
    issues: list[str] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        cells = pipe_table_cells(line)
        if not is_pipe_table_delimiter(cells):
            continue
        line_no = index + 1
        assert cells is not None
        short_cells = [position + 1 for position, cell in enumerate(cells) if cell.count("-") < 3]
        if short_cells:
            issues.append(
                f"pipe_table_short_delimiter: L{line_no}; cells "
                + ", ".join(str(position) for position in short_cells)
            )
        header_cells = pipe_table_cells(lines[index - 1]) if index > 0 else None
        if (
            header_cells is None
            or is_pipe_table_delimiter(header_cells)
            or len(header_cells) != len(cells)
        ):
            issues.append(f"pipe_table_delimiter_without_header: L{line_no}")
    return issues


def audit_inline_images(text: str) -> list[str]:
    line_hits: list[int] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not IMAGE_RE.search(line):
            continue
        stripped = line.strip()
        if re.fullmatch(r"!\[[^\]]*\]\([^)]+\)", stripped):
            continue
        line_hits.append(line_no)
    if not line_hits:
        return []
    preview = ", ".join(str(line_no) for line_no in line_hits[:10])
    suffix = "" if len(line_hits) <= 10 else ", ..."
    return [f"inline_image_residue: {len(line_hits)} line(s); lines {preview}{suffix}"]


def main() -> None:
    args = parse_args()
    path = args.markdown
    text = path.read_text(encoding="utf-8")

    issues = []
    issues.extend(audit_images(path, text))
    issues.extend(audit_equations(text))
    manifest = load_formula_manifest(args.formula_manifest)
    issues.extend(audit_formula_manifest(text, manifest))
    issues.extend(audit_pipe_table_structure(text))
    issues.extend(audit_table_symbols(text))
    issues.extend(audit_inline_images(text))
    issues.extend(audit_text_patterns(text))

    print(f"file={path}")
    for issue in issues:
        print(f"- {issue}")
    if args.json_report:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(
            json.dumps(
                {
                    "file": str(path),
                    "strict": args.strict,
                    "formula_manifest": str(args.formula_manifest) if args.formula_manifest else "",
                    "issues": issues,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    hard_fail = [
        issue
        for issue in issues
        if "data URI" in issue
        or "WMF" in issue
        or "unresolved vector/raster" in issue
        or "missing" in issue
        or issue.startswith("word_anchor_residue:")
        or issue.startswith("formula_image_number:")
        or issue.startswith("formula_manifest_unverified:")
        or issue.startswith("formula_manifest_missing")
        or issue.startswith("formula_manifest_duplicate_tag:")
        or issue.startswith("formula_manifest_tag_not_rendered:")
        or issue.startswith("formula_manifest_target_unconsumed:")
        or issue.startswith("grid_table_border:")
        or issue.startswith("escaped_linked_citation:")
        or issue.startswith("pipe_table_short_delimiter:")
        or issue.startswith("pipe_table_delimiter_without_header:")
        or issue.startswith("control_character:")
        or issue.startswith("inline_adjacent_math:")
        or issue.startswith("inline_double_subscript:")
        or issue.startswith("math_html_subsup_fragment:")
        or issue.startswith("literal_katex_error:")
        or "has no \\tag" in issue
        or "unclosed" in issue
    ]
    if args.strict:
        hard_fail.extend(
            issue
            for issue in issues
            if not issue.startswith("equation_blocks=")
            and not issue.startswith("formula_manifest_verified_entries=")
        )
    raise SystemExit(1 if hard_fail else 0)


if __name__ == "__main__":
    main()
