#!/usr/bin/env python3
"""Run end-to-end DOCX-to-Markdown regression checks against golden outputs."""

from __future__ import annotations

import argparse
import collections
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote


IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
HTML_IMAGE_RE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"'][^>]*>", re.I)
DISPLAY_MATH_RE = re.compile(r"(?ms)^\$\$\s*$.*?^\$\$\s*$")
TAG_RE = re.compile(r"\\tag\{[^}]+\}")
TABLE_SYMBOL_RE = re.compile(
    r"\|.*(?:\*[A-Za-z\u0370-\u03ff][A-Za-z0-9\u0370-\u03ff]?\*|\*[A-Za-z\u0370-\u03ff]\*~[A-Za-z0-9\u0370-\u03ff]+~)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert DOCX files to fresh Markdown, audit the results, and compare "
            "them with known-good Markdown baselines."
        )
    )
    parser.add_argument(
        "--case",
        nargs=3,
        action="append",
        metavar=("NAME", "DOCX", "BASELINE_MD"),
        required=True,
        help="Regression case name, source DOCX, and known-good Markdown baseline.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--converter",
        type=Path,
        default=Path(__file__).with_name("convert_docx.py"),
        help="DOCX-to-Markdown converter executable.",
    )
    parser.add_argument(
        "--skip-convert",
        action="store_true",
        help="Reuse existing fresh.word2latex.md files in the output directory.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Report path. Defaults to OUTPUT_DIR/e2e-regression-report.md.",
    )
    parser.add_argument(
        "--postprocess",
        action="store_true",
        help="Run postprocess_markdown_conversion.py and compare the processed Markdown.",
    )
    parser.add_argument(
        "--postprocessor",
        type=Path,
        help="Postprocessor script path. Defaults to scripts/postprocess_markdown_conversion.py.",
    )
    parser.add_argument(
        "--postprocess-no-pandoc-normalize",
        action="store_true",
        help="Pass --no-pandoc-normalize to the postprocessor.",
    )
    parser.add_argument(
        "--restore-formulas-from-baseline",
        action="store_true",
        help=(
            "After postprocessing, replace formula-image placeholders with display "
            "equations from the known-good baseline."
        ),
    )
    parser.add_argument(
        "--formula-restorer",
        type=Path,
        help="Formula restorer script path. Defaults to scripts/restore_formulas_from_baseline.py.",
    )
    parser.add_argument(
        "--formula-restore-allow-unmatched",
        action="store_true",
        help="Allow formula candidate/equation count mismatches during baseline-assisted restore.",
    )
    parser.add_argument(
        "--collapse-figure-blocks",
        action="store_true",
        help=(
            "After formula restoration, collapse image-only figure layout blocks "
            "into composite PNGs before auditing."
        ),
    )
    parser.add_argument(
        "--figure-collapser",
        type=Path,
        help="Figure block collapser script path. Defaults to scripts/collapse_figure_image_blocks.py.",
    )
    return parser.parse_args()


def run_command(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    output = "\n".join(part for part in [proc.stdout, proc.stderr] if part)
    return proc.returncode, output.rstrip()


def safe_name(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)
    return cleaned[:90] or "case"


def normalize_image_target(raw: str) -> str:
    target = raw.strip().strip("<>").strip()
    if (target.startswith('"') and target.endswith('"')) or (
        target.startswith("'") and target.endswith("'")
    ):
        target = target[1:-1]
    return unquote(target)


def image_targets(text: str) -> list[str]:
    targets = [normalize_image_target(match.group(1)) for match in IMAGE_RE.finditer(text)]
    targets.extend(normalize_image_target(match.group(1)) for match in HTML_IMAGE_RE.finditer(text))
    return targets


def missing_local_images(markdown: Path, targets: list[str]) -> int:
    missing = 0
    for target in targets:
        lower = target.lower()
        if lower.startswith("data:") or re.match(r"^[a-z][a-z0-9+.-]*:", lower):
            continue
        if not (markdown.parent / target).resolve().exists():
            missing += 1
    return missing


def metrics(markdown: Path) -> dict[str, object]:
    text = markdown.read_text(encoding="utf-8")
    targets = image_targets(text)
    display_blocks = DISPLAY_MATH_RE.findall(text)
    ext_counter: collections.Counter[str] = collections.Counter()
    for target in targets:
        suffix = Path(target.split("#", 1)[0].split("?", 1)[0]).suffix.lower()
        ext_counter[suffix or "<none>"] += 1
    repeated = sum(1 for count in collections.Counter(targets).values() if count > 1)

    return {
        "bytes": markdown.stat().st_size,
        "lines": text.count("\n") + 1,
        "headings": len(re.findall(r"(?m)^#{1,6}\s+", text)),
        "images": len(targets),
        "repeated_image_targets": repeated,
        "missing_local_images": missing_local_images(markdown, targets),
        "image_exts": dict(sorted(ext_counter.items())),
        "display_equations": len(display_blocks),
        "tagged_equations": sum(1 for block in display_blocks if TAG_RE.search(block)),
        "tag_markers": len(TAG_RE.findall(text)),
        "escaped_numeric_citations": len(re.findall(r"\\\[[0-9, -]+\\\]", text)),
        "escaped_reference_types": len(re.findall(r"\\\[[A-Za-z]\\\]", text)),
        "unresolved_media_refs": len(
            re.findall(r"data:image|image/x-wmf|\.wmf\b|\.emf\b|\.tiff?\b", text, re.I)
        ),
        "image_size_attrs": len(
            re.findall(
                r"\{[^}]*\b(?:width|height)=|\b(?:width|height)=\"[^\"]+\"|style=\"[^\"]*(?:width|height)[^\"]*\"",
                text,
                re.I,
            )
        ),
        "inline_image_lines": sum(
            1
            for line in text.splitlines()
            if IMAGE_RE.search(line)
            and not re.fullmatch(r"\s*!\[[^\]]*\]\([^)]+\)\s*", line)
        ),
        "grid_table_borders": len(re.findall(r"(?m)^\+[-=+ :]+\+\s*$", text)),
        "table_symbol_lines": sum(1 for line in text.splitlines() if TABLE_SYMBOL_RE.search(line)),
        "italic_symbol_fragments": len(
            re.findall(r"(?<!\*)\*[A-Za-z][A-Za-z0-9]?\*(?!\*)", text)
        ),
        "captions": len(re.findall(r"\b(?:Fig\.|Figure|Table)\s+[S]?\d+", text)),
    }


def append_metrics(lines: list[str], label: str, values: dict[str, object]) -> None:
    lines.append(f"{label}_metrics:")
    for key, value in values.items():
        lines.append(f"  - {key}: {value}")


def main() -> None:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    audit_script = script_dir / "audit_markdown_conversion.py"
    postprocessor = args.postprocessor or (script_dir / "postprocess_markdown_conversion.py")
    formula_restorer = args.formula_restorer or (script_dir / "restore_formulas_from_baseline.py")
    figure_collapser = args.figure_collapser or (script_dir / "collapse_figure_image_blocks.py")
    report_path = args.report or (args.output_dir / "e2e-regression-report.md")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    report_lines = [
        "# DOCX To Markdown End-To-End Regression Report",
        "",
        f"generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"converter: {args.converter}",
        f"skip_convert: {args.skip_convert}",
        "",
    ]
    all_ok = True

    for raw_name, raw_docx, raw_baseline in args.case:
        name = safe_name(raw_name)
        docx = Path(raw_docx)
        baseline = Path(raw_baseline)
        case_dir = args.output_dir / name
        media_dir = case_dir / "media_word2latex"
        fresh_md = case_dir / "fresh.word2latex.md"
        processed_md = case_dir / "fresh.processed.md"
        restored_md = case_dir / "fresh.restored.md"
        figure_collapsed_md = case_dir / "fresh.figure-collapsed.md"
        case_dir.mkdir(parents=True, exist_ok=True)
        media_dir.mkdir(parents=True, exist_ok=True)

        report_lines.append(f"## {name}")
        report_lines.append(f"docx: {docx}")
        report_lines.append(f"baseline: {baseline}")
        report_lines.append(f"fresh: {fresh_md}")

        if not docx.exists():
            report_lines.append("status: FAIL missing DOCX")
            report_lines.append("")
            all_ok = False
            continue
        if not baseline.exists():
            report_lines.append("status: FAIL missing baseline")
            report_lines.append("")
            all_ok = False
            continue

        if not args.skip_convert:
            if not args.converter.exists() and not shutil.which(str(args.converter)):
                report_lines.append("convert_exit: SKIPPED missing converter")
                all_ok = False
            else:
                convert_code, convert_output = run_command(
                    [
                        *([sys.executable, str(args.converter)] if args.converter.suffix == ".py" else [str(args.converter)]),
                        str(docx),
                        "-o",
                        str(fresh_md),
                        "--extract-media",
                        str(media_dir),
                    ]
                )
                report_lines.append(f"convert_exit: {convert_code}")
                if convert_output:
                    report_lines.append("convert_output:")
                    report_lines.extend(f"  {line}" for line in convert_output.splitlines())
                if convert_code != 0:
                    all_ok = False

        if not fresh_md.exists():
            report_lines.append("status: FAIL missing fresh Markdown")
            report_lines.append("")
            all_ok = False
            continue

        markdown_to_check = fresh_md
        if args.postprocess:
            post_cmd = [sys.executable, str(postprocessor), str(fresh_md), "-o", str(processed_md), "--aggressive-symbols"]
            if args.postprocess_no_pandoc_normalize:
                post_cmd.append("--no-pandoc-normalize")
            post_code, post_output = run_command(post_cmd)
            report_lines.append(f"postprocess_exit: {post_code}")
            if post_output:
                report_lines.append("postprocess_output:")
                report_lines.extend(f"  {line}" for line in post_output.splitlines())
            if post_code != 0 or not processed_md.exists():
                all_ok = False
            else:
                markdown_to_check = processed_md
                report_lines.append(f"processed: {processed_md}")

        if args.restore_formulas_from_baseline:
            restore_cmd = [
                sys.executable,
                str(formula_restorer),
                "--fresh",
                str(markdown_to_check),
                "--baseline",
                str(baseline),
                "-o",
                str(restored_md),
            ]
            if args.formula_restore_allow_unmatched:
                restore_cmd.append("--allow-unmatched")
            restore_code, restore_output = run_command(restore_cmd)
            report_lines.append(f"formula_restore_exit: {restore_code}")
            if restore_output:
                report_lines.append("formula_restore_output:")
                report_lines.extend(f"  {line}" for line in restore_output.splitlines())
            if restore_code != 0 or not restored_md.exists():
                all_ok = False
            else:
                markdown_to_check = restored_md
                report_lines.append(f"restored: {restored_md}")

        if args.collapse_figure_blocks:
            collapse_cmd = [
                sys.executable,
                str(figure_collapser),
                str(markdown_to_check),
                "-o",
                str(figure_collapsed_md),
            ]
            collapse_code, collapse_output = run_command(collapse_cmd)
            report_lines.append(f"figure_collapse_exit: {collapse_code}")
            if collapse_output:
                report_lines.append("figure_collapse_output:")
                report_lines.extend(f"  {line}" for line in collapse_output.splitlines())
            if collapse_code != 0 or not figure_collapsed_md.exists():
                all_ok = False
            else:
                markdown_to_check = figure_collapsed_md
                report_lines.append(f"figure_collapsed: {figure_collapsed_md}")

        fresh_metrics = metrics(markdown_to_check)
        baseline_metrics = metrics(baseline)
        append_metrics(report_lines, "fresh", fresh_metrics)
        append_metrics(report_lines, "baseline", baseline_metrics)

        baseline_code, baseline_audit = run_command(
            [sys.executable, str(audit_script), "--strict", str(baseline)]
        )
        fresh_code, fresh_audit = run_command(
            [sys.executable, str(audit_script), "--strict", str(markdown_to_check)]
        )
        report_lines.append(f"baseline_strict_audit_exit: {baseline_code}")
        report_lines.append(f"fresh_strict_audit_exit: {fresh_code}")
        if baseline_audit:
            report_lines.append("baseline_strict_audit_output:")
            report_lines.extend(f"  {line}" for line in baseline_audit.splitlines())
        if fresh_audit:
            report_lines.append("fresh_strict_audit_output:")
            report_lines.extend(f"  {line}" for line in fresh_audit.splitlines())

        failures: list[str] = []
        if baseline_code != 0:
            failures.append("baseline strict audit failed")
        if fresh_code != 0:
            failures.append("fresh strict audit failed")
        expected_eqs = int(baseline_metrics["display_equations"])
        fresh_eqs = int(fresh_metrics["display_equations"])
        fresh_tags = int(fresh_metrics["tagged_equations"])
        if expected_eqs and fresh_eqs < expected_eqs:
            failures.append(
                f"fresh display equations below baseline: {fresh_eqs} < {expected_eqs}"
            )
        if expected_eqs and fresh_tags < expected_eqs:
            failures.append(f"fresh tagged equations below baseline: {fresh_tags} < {expected_eqs}")
        baseline_headings = int(baseline_metrics["headings"])
        fresh_headings = int(fresh_metrics["headings"])
        if baseline_headings and fresh_headings + 2 < baseline_headings:
            failures.append(
                f"fresh heading count below baseline: {fresh_headings} < {baseline_headings}"
            )
        baseline_images = int(baseline_metrics["images"])
        fresh_images = int(fresh_metrics["images"])
        image_tolerance = max(3, int(round(baseline_images * 0.25)))
        if baseline_images and fresh_images > baseline_images + image_tolerance:
            failures.append(
                f"fresh image count exceeds baseline tolerance: "
                f"{fresh_images} > {baseline_images}+{image_tolerance}"
            )
        for metric_name in (
            "unresolved_media_refs",
            "escaped_numeric_citations",
            "escaped_reference_types",
            "image_size_attrs",
            "inline_image_lines",
            "grid_table_borders",
            "missing_local_images",
        ):
            if int(fresh_metrics[metric_name]) > int(baseline_metrics[metric_name]):
                failures.append(
                    f"fresh {metric_name} exceeds baseline: "
                    f"{fresh_metrics[metric_name]} > {baseline_metrics[metric_name]}"
                )
        if int(fresh_metrics["table_symbol_lines"]) > int(baseline_metrics["table_symbol_lines"]):
            failures.append(
                "fresh table symbol residue exceeds baseline: "
                f"{fresh_metrics['table_symbol_lines']} > {baseline_metrics['table_symbol_lines']}"
            )

        if failures:
            report_lines.append("status: FAIL")
            report_lines.append("failures:")
            report_lines.extend(f"  - {failure}" for failure in failures)
            all_ok = False
        else:
            report_lines.append("status: PASS")
        report_lines.append("")

    report_lines.append(f"overall: {'PASS' if all_ok else 'FAIL'}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8", newline="\n")
    print(report_path)
    raise SystemExit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
