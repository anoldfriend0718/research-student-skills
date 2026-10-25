#!/usr/bin/env python3
"""Collapse DOCX-derived figure image blocks into composite PNGs."""

from __future__ import annotations

import argparse
import math
import re
import shutil
from pathlib import Path
from urllib.parse import unquote


IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
CAPTION_RE = re.compile(r"^\s*(?:Fig\.|Figure)\s+S?\d+\b|^\s*[\u56fe\u8868]\s*\d+(?:\.\d+)?", re.I)
HTML_TABLE_TAG_RE = re.compile(
    r"</?(?:table|thead|tbody|tr|td|th|colgroup|col)[^>]*>", re.I
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replace image-only layout tables immediately followed by figure "
            "captions with one generated composite PNG."
        )
    )
    parser.add_argument("markdown", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument(
        "--media-dir",
        type=Path,
        help="Relative directory for generated composites. Defaults near the first image.",
    )
    parser.add_argument(
        "--max-cell-width",
        type=int,
        default=900,
        help="Maximum width in pixels for each panel inside the composite.",
    )
    return parser.parse_args()


def normalize_image_target(raw: str) -> str:
    target = raw.strip().strip("<>").strip()
    if (target.startswith('"') and target.endswith('"')) or (
        target.startswith("'") and target.endswith("'")
    ):
        target = target[1:-1]
    return unquote(target)


def image_targets(block: str) -> list[str]:
    return [normalize_image_target(match.group(2)) for match in IMAGE_RE.finditer(block)]


def caption_starts(block: str) -> bool:
    stripped = block.strip()
    return bool(CAPTION_RE.match(stripped))


def is_layout_image_block(block: str) -> bool:
    targets = image_targets(block)
    if not targets:
        return False
    stripped = IMAGE_RE.sub("", block)
    stripped = HTML_TABLE_TAG_RE.sub("", stripped)
    stripped = re.sub(r"[:|\-+_= \t\r\n]", "", stripped)
    return not stripped


def ordered_unique(targets: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for target in targets:
        if target in seen:
            continue
        seen.add(target)
        result.append(target)
    return result


def default_media_dir(target: str) -> Path:
    parts = Path(target).parts
    if parts and parts[0] in {"media_word2latex", "media", "assets"}:
        return Path(parts[0]) / "derived_figures"
    return Path("derived_figures")


def resolve_local(markdown_dir: Path, target: str) -> Path | None:
    lower = target.lower()
    if lower.startswith("data:") or re.match(r"^[a-z][a-z0-9+.-]*:", lower):
        return None
    path = (markdown_dir / target).resolve()
    return path if path.exists() else None


def fit_size(width: int, height: int, max_width: int) -> tuple[int, int]:
    if width <= max_width:
        return width, height
    ratio = max_width / width
    return max(1, int(width * ratio)), max(1, int(height * ratio))


def compose_images(
    sources: list[Path],
    output: Path,
    max_cell_width: int,
    padding: int = 24,
    background: tuple[int, int, int] = (255, 255, 255),
) -> bool:
    try:
        from PIL import Image
    except Exception:
        return False

    panels = []
    for source in sources:
        try:
            image = Image.open(source).convert("RGBA")
        except Exception:
            continue
        new_size = fit_size(image.width, image.height, max_cell_width)
        if new_size != image.size:
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        panels.append(image)

    if not panels:
        return False

    if len(panels) == 1:
        output.parent.mkdir(parents=True, exist_ok=True)
        canvas = Image.new("RGB", panels[0].size, background)
        canvas.paste(panels[0], mask=panels[0].split()[-1])
        canvas.save(output)
        return output.exists() and output.stat().st_size > 0

    cols = 2 if len(panels) <= 4 else 3
    rows = math.ceil(len(panels) / cols)
    cell_widths = [0] * cols
    row_heights = [0] * rows
    for idx, image in enumerate(panels):
        row = idx // cols
        col = idx % cols
        cell_widths[col] = max(cell_widths[col], image.width)
        row_heights[row] = max(row_heights[row], image.height)

    width = sum(cell_widths) + padding * (cols + 1)
    height = sum(row_heights) + padding * (rows + 1)
    canvas = Image.new("RGB", (width, height), background)

    y = padding
    for row in range(rows):
        x = padding
        for col in range(cols):
            idx = row * cols + col
            if idx >= len(panels):
                break
            image = panels[idx]
            offset_x = x + (cell_widths[col] - image.width) // 2
            offset_y = y + (row_heights[row] - image.height) // 2
            canvas.paste(image, (offset_x, offset_y), mask=image.split()[-1])
            x += cell_widths[col] + padding
        y += row_heights[row] + padding

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    return output.exists() and output.stat().st_size > 0


def split_blocks(text: str) -> list[str]:
    return re.split(r"\n{2,}", text.strip())


def strip_images(block: str) -> str:
    block = IMAGE_RE.sub("", block)
    block = re.sub(r"\[\]\{#_(?:Toc|Ref)\d+\s+\.anchor\}", "", block)
    return block.strip()


def collapse_blocks(
    text: str,
    markdown_dir: Path,
    media_dir_arg: Path | None,
    max_cell_width: int,
) -> tuple[str, dict[str, int]]:
    blocks = split_blocks(text)
    output_blocks: list[str] = []
    stats = {"collapsed_blocks": 0, "source_images": 0, "failed_blocks": 0}
    idx = 0
    composite_idx = 1

    while idx < len(blocks):
        block = blocks[idx]
        if is_layout_image_block(block):
            run_end = idx
            while run_end < len(blocks) and is_layout_image_block(blocks[run_end]):
                run_end += 1
            next_block = blocks[run_end] if run_end < len(blocks) else ""
            if not caption_starts(next_block):
                output_blocks.append(block)
                idx += 1
                continue
            layout_blocks = blocks[idx:run_end]
            targets = ordered_unique(
                [
                    target
                    for layout_block in layout_blocks
                    for target in image_targets(layout_block)
                ]
                + image_targets(next_block)
            )
            sources = [path for target in targets if (path := resolve_local(markdown_dir, target))]
            if sources:
                rel_dir = media_dir_arg or default_media_dir(targets[0])
                rel_output = rel_dir / f"figure_block_{composite_idx:03d}.png"
                abs_output = (markdown_dir / rel_output).resolve()
                if compose_images(sources, abs_output, max_cell_width):
                    rel_text = str(rel_output).replace("\\", "/")
                    output_blocks.append(f"![]({rel_text})")
                    output_blocks.append(strip_images(next_block))
                    stats["collapsed_blocks"] += 1
                    stats["source_images"] += len(targets)
                    composite_idx += 1
                    idx = run_end + 1
                    continue
            stats["failed_blocks"] += 1
        output_blocks.append(block)
        idx += 1

    return "\n\n".join(output_blocks).strip() + "\n", stats


def main() -> None:
    args = parse_args()
    source = args.markdown.resolve()
    output = args.output.resolve()
    text = source.read_text(encoding="utf-8")
    processed, stats = collapse_blocks(
        text,
        source.parent,
        args.media_dir,
        args.max_cell_width,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.resolve() != source:
        output.write_text(processed, encoding="utf-8", newline="\n")
    else:
        backup = output.with_suffix(output.suffix + ".before-figure-collapse")
        shutil.copy2(output, backup)
        output.write_text(processed, encoding="utf-8", newline="\n")
    print(f"output={output}")
    for key, value in stats.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
