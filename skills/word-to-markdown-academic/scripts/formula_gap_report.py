#!/usr/bin/env python3
"""Report formula-image gaps between fresh DOCX Markdown and a known-good baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote


MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
HTML_IMAGE_RE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"'][^>]*>", re.I)
DISPLAY_MATH_RE = re.compile(r"(?ms)^\$\$\s*$.*?^\$\$\s*$")
TAG_RE = re.compile(r"\\tag\{([^}]+)\}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a formula gap report and optional contact sheet."
    )
    parser.add_argument("--fresh", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--max-images", type=int, default=80)
    parser.add_argument(
        "--manifest-skeleton",
        action="store_true",
        help="Write machine-readable formula candidate skeleton JSON files.",
    )
    parser.add_argument(
        "--agent-count",
        type=int,
        default=1,
        help="Split manifest skeleton candidates into this many agent shards.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        help="Split manifest skeleton candidates by fixed candidate count.",
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


def is_formula_candidate(line: str, prev_line: str, next_line: str) -> bool:
    if not line_images(line):
        return False
    stripped = line.strip()
    if re.match(r"^(Fig\.|Figure|Table)\s+", stripped, re.I):
        return False
    if re.match(r"^(Fig\.|Figure)\s+", next_line, re.I):
        return False
    if re.fullmatch(r"(?:!\[[^\]]*\]\([^)]+\)\s*)+", stripped):
        return True
    if re.search(r"(?:\\\()?([1-9][0-9]?)\\?\)", stripped):
        return True
    if prev_line.endswith(":") and re.fullmatch(r"(?:!\[[^\]]*\]\([^)]+\)\s*)+", stripped):
        return True
    if prev_line.endswith(":") and next_line.lower().startswith("where"):
        return True
    if "equation" in prev_line.lower() and next_line.lower().startswith("where"):
        return True
    return False


def extract_candidates(fresh: Path) -> list[dict[str, object]]:
    lines = fresh.read_text(encoding="utf-8").splitlines()
    candidates: list[dict[str, object]] = []
    for idx, line in enumerate(lines):
        targets = line_images(line)
        if not targets:
            continue
        prev_line = previous_nonblank(lines, idx)
        next_line = next_nonblank(lines, idx)
        if is_formula_candidate(line, prev_line, next_line):
            candidates.append(
                {
                    "line": idx + 1,
                    "targets": targets,
                    "text": line.strip(),
                    "prev": prev_line,
                    "next": next_line,
                }
            )
    return candidates


def extract_equations(baseline: Path) -> list[dict[str, str]]:
    text = baseline.read_text(encoding="utf-8")
    equations = []
    for idx, match in enumerate(DISPLAY_MATH_RE.finditer(text), start=1):
        block = match.group(0)
        tag_match = TAG_RE.search(block)
        equations.append({"index": str(idx), "tag": tag_match.group(1) if tag_match else "", "block": block})
    return equations


def image_metadata(fresh: Path, target: str) -> dict[str, object]:
    path = (fresh.parent / target).resolve()
    data: dict[str, object] = {"target": target, "exists": path.exists()}
    if not path.exists():
        return data
    data["sha1"] = hashlib.sha1(path.read_bytes()).hexdigest()
    try:
        from PIL import Image

        with Image.open(path) as image:
            data["width"] = image.width
            data["height"] = image.height
    except Exception as exc:
        data["image_error"] = str(exc)
    return data


def candidate_to_manifest_entry(
    fresh: Path, candidate: dict[str, object], index: int
) -> dict[str, object]:
    targets = [str(target) for target in candidate["targets"]]  # type: ignore[index]
    return {
        "candidate_id": f"candidate-{index:04d}",
        "kind": "display" if len(targets) == 1 else "compound",
        "status": "todo",
        "source_line": candidate["line"],
        "targets": targets,
        "images": [image_metadata(fresh, target) for target in targets],
        "context_before": candidate["prev"],
        "source_text": candidate["text"],
        "context_after": candidate["next"],
        "latex": "",
        "tag": "",
        "anchor": "",
        "assigned_agent": "",
        "notes": "",
    }


def write_manifest_skeletons(
    fresh: Path,
    candidates: list[dict[str, object]],
    output_dir: Path,
    name: str,
    agent_count: int,
    chunk_size: int | None,
) -> list[Path]:
    entries = [
        candidate_to_manifest_entry(fresh, candidate, index)
        for index, candidate in enumerate(candidates, start=1)
    ]
    if chunk_size and chunk_size > 0:
        chunks = [entries[index : index + chunk_size] for index in range(0, len(entries), chunk_size)]
    else:
        agent_count = max(1, agent_count)
        chunk_len = max(1, math.ceil(len(entries) / agent_count))
        chunks = [entries[index : index + chunk_len] for index in range(0, len(entries), chunk_len)]

    paths: list[Path] = []
    for index, chunk in enumerate(chunks, start=1):
        for entry in chunk:
            entry["assigned_agent"] = f"agent-{index:02d}"
        payload = {
            "fresh": str(fresh),
            "name": name,
            "schema": "formula_manifest_skeleton.v1",
            "candidates": chunk,
        }
        path = output_dir / f"{name}_formula_manifest.agent-{index:02d}.todo.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def write_contact_sheet(
    fresh: Path, candidates: list[dict[str, object]], output_dir: Path, name: str, max_images: int
) -> Path | None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None

    image_items: list[tuple[str, Path, int]] = []
    for candidate in candidates:
        line_no = int(candidate["line"])
        for raw_target in candidate["targets"]:  # type: ignore[index]
            target = str(raw_target)
            lower = target.lower()
            if lower.startswith("data:") or re.match(r"^[a-z][a-z0-9+.-]*:", lower):
                continue
            path = (fresh.parent / target).resolve()
            if path.exists() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
                image_items.append((target, path, line_no))
    image_items = image_items[:max_images]
    if not image_items:
        return None

    thumb_w, thumb_h = 260, 160
    label_h = 44
    cols = 3
    rows = math.ceil(len(image_items) / cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    for idx, (target, path, line_no) in enumerate(image_items):
        col = idx % cols
        row = idx // cols
        x = col * thumb_w
        y = row * (thumb_h + label_h)
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((thumb_w - 12, thumb_h - 12))
            ox = x + (thumb_w - img.width) // 2
            oy = y + 6 + (thumb_h - img.height) // 2
            sheet.paste(img, (ox, oy))
        except Exception:
            draw.text((x + 8, y + 24), "unreadable image", fill="red", font=font)
        draw.rectangle((x, y, x + thumb_w - 1, y + thumb_h + label_h - 1), outline="#888888")
        label = f"L{line_no} {Path(target).name}"
        draw.text((x + 8, y + thumb_h + 6), label[:42], fill="black", font=font)

    output_dir.mkdir(parents=True, exist_ok=True)
    sheet_path = output_dir / f"{name}_formula_candidates.png"
    sheet.save(sheet_path)
    return sheet_path


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    equations = extract_equations(args.baseline) if args.baseline else []
    candidates = extract_candidates(args.fresh)
    all_targets = [
        target
        for candidate in candidates
        for target in candidate["targets"]  # type: ignore[index]
    ]
    repeated = {target: count for target, count in Counter(all_targets).items() if count > 1}
    sheet = write_contact_sheet(args.fresh, candidates, output_dir, args.name, args.max_images)

    lines = [
        f"# Formula Gap Report: {args.name}",
        "",
        f"fresh: {args.fresh}",
        f"baseline: {args.baseline or ''}",
        f"baseline_display_equations: {len(equations)}",
        f"fresh_formula_image_candidates: {len(candidates)}",
        f"repeated_candidate_targets: {len(repeated)}",
    ]
    if sheet:
        lines.append(f"contact_sheet: {sheet}")
    skeletons: list[Path] = []
    if args.manifest_skeleton:
        skeletons = write_manifest_skeletons(
            args.fresh, candidates, output_dir, args.name, args.agent_count, args.chunk_size
        )
        for path in skeletons:
            lines.append(f"manifest_skeleton: {path}")
    lines.append("")
    lines.append("## Baseline Equations")
    for equation in equations:
        first_line = next((line for line in equation["block"].splitlines() if line and line != "$$"), "")
        tag = equation["tag"] or "untagged"
        lines.append(f"- eq_index={equation['index']} tag={tag}: `{first_line[:140]}`")
    lines.append("")
    lines.append("## Fresh Formula-Image Candidates")
    for idx, candidate in enumerate(candidates, start=1):
        targets = ", ".join(Path(str(target)).name for target in candidate["targets"])  # type: ignore[index]
        lines.append(f"- candidate={idx} line={candidate['line']} targets={targets}")
        lines.append(f"  prev: {str(candidate['prev'])[:180]}")
        lines.append(f"  text: {str(candidate['text'])[:180]}")
        lines.append(f"  next: {str(candidate['next'])[:180]}")
    if repeated:
        lines.append("")
        lines.append("## Repeated Candidate Targets")
        for target, count in sorted(repeated.items()):
            lines.append(f"- {target}: {count}")

    report = output_dir / f"{args.name}_formula_gap_report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(report)


if __name__ == "__main__":
    main()
