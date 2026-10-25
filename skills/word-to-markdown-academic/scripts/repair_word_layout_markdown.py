#!/usr/bin/env python3
"""Repair DOCX-derived Markdown when Word layout tables leak into text."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote


IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
IMAGE_LINE_RE = re.compile(r"^\s*!\[(?P<alt>.*)\]\((?P<target>[^)]+)\)\s*$")
DOCX_ANCHOR_RE = re.compile(r"\\?\[\\?\]\{#\\?(?P<anchor>_(?:Toc|Ref)\d+)\s+\.anchor\}")
SPLIT_DOCX_ANCHOR_RE = re.compile(
    r"(?m)^(?P<prefix>\|\s*!\[[^\]]*\]\([^)]+\))\s+\\?\[\\?\]\{#\\?_(?:Toc|Ref)\d+\s*\|\s*\n"
    r"\|\s*\.anchor\}(?P<tag>\(\d+(?:[\-\u2011]\d+)?\))\s*\|?\s*$"
)
SPAN_ANCHOR_RE = re.compile(
    r"<span\s+id=[\"'](?P<anchor>_(?:Toc|Ref)\d+)[\"']\s+class=[\"']anchor[\"']></span>",
    re.I,
)
TOC_HEADING_RE = re.compile(
    r"^\s*(?:\\?\[\\?\]\{#\\?(?P<a1>_Toc\d+)\s+\.anchor\}|"
    r"<span\s+id=[\"'](?P<a2>_Toc\d+)[\"']\s+class=[\"']anchor[\"']></span>)"
    r"\s*(?:\*\*)?(?P<title>.+?)(?:\*\*)?\s*$"
)
MARKDOWN_NUMBERED_HEADING_RE = re.compile(
    r"^(?P<marks>#{1,6})\s+(?P<title>\d+(?:\.\d+)*\s+.+?)\s*$"
)
CAPTION_RE = re.compile(
    r"^\s*(?::\s*)?"
    r"(?:\\?\[\\?\]\{#\\?(?P<a1>_Ref\d+)\s+\.anchor\}|"
    r"<span\s+id=[\"'](?P<a2>_Ref\d+)[\"']\s+class=[\"']anchor[\"']></span>)?"
    r"\s*(?P<kind>[\u56fe\u8868])\s*(?P<num>\d+(?:\.\d+)?)(?P<rest>.*)$"
)
FORMULA_NUMBER_RE = re.compile(r"\((?P<tag>\d+(?:[\-\u2011]\d+)?)\)")
RULE_RE = re.compile(r"^\s*(?:\+[-=+: ]+\+|-{5,}|[-= ]{5,})\s*$")
GRID_RULE_RE = re.compile(r"^\s*\+[-=+: ]+\+\s*$")
PIPE_ONLY_RE = re.compile(r"^\s*\|+\s*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repair Word anchors, formula tables, layout tables, and captions."
    )
    parser.add_argument("markdown", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument(
        "--formula-manifest",
        type=Path,
        help="JSON mapping formula image targets to LaTeX and equation tags.",
    )
    parser.add_argument(
        "--manifest-report",
        type=Path,
        help="Write a manifest validation and consumption report.",
    )
    parser.add_argument(
        "--allow-unverified",
        action="store_true",
        help="Load non-verified manifest entries. By default only verified/accepted entries are applied.",
    )
    return parser.parse_args()


def normalize_target(raw: str) -> str:
    target = unquote(raw.strip().strip("<>").strip())
    if (target.startswith('"') and target.endswith('"')) or (
        target.startswith("'") and target.endswith("'")
    ):
        target = target[1:-1]
    while target.startswith("./"):
        target = target[2:]
    return target.replace("\\", "/")


def load_formula_manifest(
    path: Path | None, allow_unverified: bool = False
) -> tuple[dict[str, dict[str, str]], list[str]]:
    if not path:
        return {}, ["formula_manifest=none"]
    data = json.loads(path.read_text(encoding="utf-8"))
    formulas = data.get("formulas", data)
    if not isinstance(formulas, dict):
        raise ValueError("formula manifest must be a mapping or contain a 'formulas' mapping")

    loaded: dict[str, dict[str, str]] = {}
    report: list[str] = [f"formula_manifest={path}"]
    tags: dict[str, str] = {}
    skipped = 0
    invalid = 0
    for raw_key, raw_value in formulas.items():
        key = normalize_target(str(raw_key))
        if key.startswith("compound:"):
            skipped += 1
            report.append(f"skipped_compound_entry={key}")
            continue
        if not isinstance(raw_value, dict):
            invalid += 1
            report.append(f"invalid_entry={key}: value is not an object")
            continue
        value = {str(k): str(v) for k, v in raw_value.items() if v is not None}
        status = value.get("status", "verified").lower()
        if not allow_unverified and status not in {"verified", "accepted"}:
            skipped += 1
            report.append(f"skipped_unverified={key}: status={status}")
            continue
        kind = value.get("kind")
        latex = value.get("latex", "").strip()
        tag = value.get("tag", "").strip()
        if kind not in {"display", "inline"}:
            invalid += 1
            report.append(f"invalid_entry={key}: kind={kind!r}")
            continue
        if not latex:
            invalid += 1
            report.append(f"invalid_entry={key}: missing latex")
            continue
        if kind == "display":
            if not tag:
                invalid += 1
                report.append(f"invalid_entry={key}: display entry missing tag")
                continue
            if tag in tags:
                invalid += 1
                report.append(f"duplicate_tag={tag}: {tags[tag]} and {key}")
                continue
            tags[tag] = key
        loaded[key] = value
    report.append(f"formula_entries_loaded={len(loaded)}")
    report.append(f"formula_entries_skipped={skipped}")
    report.append(f"formula_entries_invalid={invalid}")
    return loaded, report


def sec_id(title: str) -> str:
    clean = re.sub(r"\*+", "", title).strip()
    match = re.match(r"^(\d+(?:\.\d+)*)", clean)
    if match:
        return "sec-" + match.group(1).replace(".", "-")
    if "reference" in clean.lower() or "\u53c2\u8003\u6587\u732e" in clean:
        return "sec-references"
    if "\u7ed3\u8bba" in clean:
        return "sec-conclusion"
    return "sec-" + re.sub(r"[^A-Za-z0-9]+", "-", clean).strip("-").lower()


def numbered_heading_level(title: str) -> int:
    clean = re.sub(r"\*+", "", title).strip()
    match = re.match(r"^(\d+(?:\.\d+)*)", clean)
    if not match:
        return 1
    return min(6, 1 + match.group(1).count("."))


def caption_id(kind: str, number: str) -> str:
    prefix = "fig" if kind == "\u56fe" else "tbl"
    return f"{prefix}-{number.replace('.', '-')}"


def eq_id(tag: str) -> str:
    clean = tag.replace("\u2011", "-").replace(".", "-").replace("(", "").replace(")", "")
    return "eq-" + clean


def collect_anchor_maps(
    text: str, formulas: dict[str, dict[str, str]]
) -> tuple[dict[str, str], dict[str, str]]:
    toc_map: dict[str, str] = {}
    ref_map: dict[str, str] = {}

    for line in text.splitlines():
        image_line = IMAGE_LINE_RE.match(line.strip())
        if image_line:
            caption = CAPTION_RE.match(clean_table_cell(image_line.group("alt")))
            if caption:
                anchor = caption.group("a1") or caption.group("a2")
                if anchor:
                    ref_map[anchor] = caption_id(caption.group("kind"), caption.group("num"))
        heading = TOC_HEADING_RE.match(line.strip())
        if heading:
            anchor = heading.group("a1") or heading.group("a2")
            if anchor:
                toc_map[anchor] = sec_id(heading.group("title"))
        caption = CAPTION_RE.match(clean_table_cell(line))
        if caption:
            anchor = caption.group("a1") or caption.group("a2")
            if anchor:
                ref_map[anchor] = caption_id(caption.group("kind"), caption.group("num"))

    for item in formulas.values():
        anchor = item.get("anchor")
        tag = item.get("tag")
        if anchor and tag:
            ref_map[anchor] = eq_id(tag)

    return toc_map, ref_map


def repair_citation_links(text: str) -> str:
    text = re.sub(r"\[\^?/\[([0-9, \-]+?)/\]\^?\]\(#_Ref\d+\)", r"[\1]", text)
    text = re.sub(r"\^/\[([0-9, \-]+?)/\]\^", r"[\1]", text)
    text = re.sub(r"/\[([A-Z]+(?:/[A-Z]+)?)/\]", r"[\1]", text)
    return text


def repair_split_docx_anchors(text: str) -> str:
    """Collapse Pandoc's escaped, line-split equation anchors before block repair."""
    return SPLIT_DOCX_ANCHOR_RE.sub(r"\g<prefix> | \g<tag> |", text)


def update_cross_links(text: str, toc_map: dict[str, str], ref_map: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        anchor = match.group(1).replace("\\_", "_")
        if anchor in toc_map:
            return f"(#{toc_map[anchor]})"
        if anchor in ref_map:
            return f"(#{ref_map[anchor]})"
        return ""

    return re.sub(r"\(#\\?(_(?:Toc|Ref)\d+)\)", replace, text)


def cleanup_math_fragments(text: str) -> str:
    text = text.replace("[]{.mark}", "")
    text = text.replace("−", "-")
    text = text.replace("$/mathcal{/sim O}$(1 μm)", r"$\mathcal{O}(1\,\mu\mathrm{m})$")
    replacements = {
        "*ϕ*": r"$\phi$",
        "*C*": r"$C$",
        "*D*": r"$D$",
        "*P*": r"$P$",
        "*X*": r"$X$",
        "*Y*": r"$Y$",
        "*Z*": r"$Z$",
        "*S*": r"$S$",
        "*s*": r"$s$",
        "*r*": r"$r$",
        "*γ*": r"$\gamma$",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(
        r"\*\*([A-Za-z])\*\*~([^~]+)~",
        lambda m: f"$\\mathbf{{{m.group(1)}}}_{{{m.group(2)}}}$",
        text,
    )
    text = re.sub(r"\*\*([A-Za-z])\*\*", lambda m: f"$\\mathbf{{{m.group(1)}}}$", text)
    text = re.sub(r"\*([A-Za-z])\*~([^~]+)~", lambda m: f"${m.group(1)}_{{{m.group(2)}}}$", text)
    text = re.sub(r"\*([A-Za-z]~[^~]+~)\*", lambda m: "$" + m.group(1).replace("~", "_", 1).replace("~", "") + "$", text)
    text = re.sub(r"\*([A-Za-z])\*", r"$\1$", text)
    text = re.sub(r"([0-9]+(?:\.[0-9]+)?)×10\^(-?\d+)\^", r"$\1\\times10^{\2}$", text)
    text = re.sub(r"([A-Za-z]+)~([0-9A-Za-z,\-]+)~", r"\1<sub>\2</sub>", text)
    text = re.sub(r"cm\^[−-]1\^", r"cm$^{-1}$", text)
    text = re.sub(r"m\^2\^", r"m$^2$", text)
    text = re.sub(r"m\^3\^", r"m$^3$", text)
    text = re.sub(r"(?<=\d)/~(?=\d)", "-", text)
    text = re.sub(r"(?<=[\uff08(])/~(?=\d)", "\u7ea6", text)
    text = re.sub(r"(?<=[\w\)$\]\u4e00-\u9fff])\s*/>\s*(?=\d)", " > ", text)
    return text


def clean_table_cell(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("|") and stripped.endswith("|"):
        stripped = stripped[1:-1].strip()
    return stripped


def is_rule(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return bool(RULE_RE.match(stripped))


def is_tableish(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if is_rule(stripped) or stripped.startswith("|") or stripped.startswith("+"):
        return True
    if CAPTION_RE.match(clean_table_cell(stripped)):
        return True
    if IMAGE_RE.search(stripped):
        residue = IMAGE_RE.sub("", stripped)
        residue = DOCX_ANCHOR_RE.sub("", residue)
        residue = SPAN_ANCHOR_RE.sub("", residue)
        residue = re.sub(r"\(\d+-\d*\)", "", residue)
        residue = re.sub(r"[\[\]{}#_.A-Za-z0-9:|+=\-\s]", "", residue)
        return residue == ""
    return bool(re.search(r"\S\s{2,}\S", stripped))


def formula_image(line: str, formulas: dict[str, dict[str, str]]) -> tuple[str, dict[str, str]] | None:
    match = IMAGE_RE.search(line)
    if not match:
        return None
    target = normalize_target(match.group(2))
    item = formulas.get(target)
    if not item:
        return None
    return target, item


def is_display_formula_line(line: str, formulas: dict[str, dict[str, str]]) -> bool:
    found = formula_image(line, formulas)
    if not found:
        return False
    _, item = found
    if item.get("kind") != "display":
        return False
    residue = IMAGE_RE.sub("", line)
    residue = DOCX_ANCHOR_RE.sub("", residue)
    residue = SPAN_ANCHOR_RE.sub("", residue)
    residue = re.sub(r"\(\d+-\d*\)|\(\d+(?:-\d+)?\)", "", residue)
    residue = re.sub(r"[|:+=\-\s]", "", residue)
    return residue == ""


def render_display_formula(item: dict[str, str]) -> list[str]:
    latex = item["latex"].strip()
    tag = item.get("tag")
    if tag and r"\tag{" not in latex:
        latex = latex + rf"\tag{{{tag}}}"
    lines: list[str] = []
    if tag:
        lines.extend([f'<a id="{eq_id(tag)}"></a>', ""])
    lines.extend(["$$", latex, "$$"])
    return lines


def replace_inline_images(line: str, formulas: dict[str, dict[str, str]]) -> str:
    def replace(match: re.Match[str]) -> str:
        target = normalize_target(match.group(2))
        item = formulas.get(target)
        if item and item.get("kind") == "inline":
            return "$" + item["latex"].strip().strip("$") + "$"
        return f"![{match.group(1)}]({target})"

    return IMAGE_RE.sub(replace, line)


def render_caption(line: str) -> list[str] | None:
    cleaned = clean_table_cell(line)
    caption = CAPTION_RE.match(cleaned)
    if not caption:
        return None
    kind = caption.group("kind")
    num = caption.group("num")
    rest = caption.group("rest").strip()
    rest = cleanup_math_fragments(rest)
    cid = caption_id(kind, num)
    label = f"{kind}{num}"
    if rest and not rest.startswith((":", "\uff1a")):
        rest = " " + rest
    return [f'<a id="{cid}"></a>', "", f"**{label}**{rest}"]


def render_heading(line: str) -> list[str] | None:
    heading = TOC_HEADING_RE.match(line.strip())
    if heading:
        title = re.sub(r"\*\*\s+\*\*", " ", heading.group("title"))
        title = re.sub(r"\*+", "", title).strip()
        title = cleanup_math_fragments(title)
        level = numbered_heading_level(title)
        return [f'<a id="{sec_id(title)}"></a>', "", f"{'#' * level} {title}"]

    markdown_heading = MARKDOWN_NUMBERED_HEADING_RE.match(line.strip())
    if not markdown_heading:
        return None
    title = re.sub(r"\*+", "", markdown_heading.group("title")).strip()
    title = cleanup_math_fragments(title)
    level = numbered_heading_level(title)
    return [f'<a id="{sec_id(title)}"></a>', "", f"{'#' * level} {title}"]


def render_image_alt_caption(line: str) -> list[str] | None:
    match = IMAGE_LINE_RE.match(line.strip())
    if not match:
        return None
    alt = match.group("alt").strip()
    if not CAPTION_RE.search(alt):
        return None
    target = normalize_target(match.group("target"))
    caption_text = alt
    return [f"![]({target})", "", *(render_caption(caption_text) or [caption_text])]


def render_formula_image_line(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    image_matches = list(IMAGE_RE.finditer(stripped))
    if len(image_matches) != 1:
        return None
    cleaned = clean_table_cell(stripped)
    number = FORMULA_NUMBER_RE.search(cleaned)
    if not number:
        return None
    target = normalize_target(image_matches[0].group(2))
    residue = IMAGE_RE.sub("", cleaned)
    residue = FORMULA_NUMBER_RE.sub("", residue, count=1)
    residue = residue.replace("|", " ").strip()
    residue = re.sub(r"\s+", " ", residue)
    display_tag = number.group("tag")
    suffix = f" {residue}" if residue else ""
    return [f'<a id="{eq_id(display_tag)}"></a>', "", f"![]({target})", "", f"**式({display_tag})**{suffix}"]


def render_image_only_table_line(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    image_matches = list(IMAGE_RE.finditer(stripped))
    if len(image_matches) != 1:
        return None
    cleaned = clean_table_cell(stripped)
    residue = IMAGE_RE.sub("", cleaned).replace("|", " ").strip()
    if residue:
        return None
    return [f"![]({normalize_target(image_matches[0].group(2))})"]


def is_pipe_alignment(line: str) -> bool:
    return bool(re.match(r"^\s*\|[\s:\-|]+\|\s*$", line))


def is_empty_pipe_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and not stripped.strip("|").strip()


def render_toc_entry(line: str) -> list[str] | None:
    stripped = line.strip()
    quote = ""
    if stripped.startswith(">"):
        quote = "> "
        stripped = stripped[1:].strip()
    match = re.match(r"^\[(?P<title>.+)\s+\[[0-9]+\]\(#(?P<id>[^)]+)\)\]\(#(?P=id)\)$", stripped)
    if not match:
        simple_match = re.match(
            r"^-\s+\[(?P<title>[^\]]+)\]\(#(?P<id>[^)]+)\)$", stripped
        )
        if not simple_match:
            return None
        title = cleanup_math_fragments(simple_match.group("title").strip())
        if re.match(r"^\d+(?:\.\d+)*\s+", title):
            return [f"{quote}- [{title}](#{sec_id(title)})"]
        return [f"{quote}- [{title}](#{simple_match.group('id')})"]
    title = match.group("title").strip()
    title = re.sub(r"\s+\[[0-9]+\]$", "", title).strip()
    title = cleanup_math_fragments(title)
    return [f"{quote}- [{title}](#{match.group('id')})"]


def parse_rows_from_block(block: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw in block:
        line = raw.strip()
        if not line or is_rule(line) or IMAGE_RE.search(line) or CAPTION_RE.match(clean_table_cell(line)):
            continue
        if set(line) <= {"|", ":", "-", "+", " "}:
            continue
        if line.startswith("|") and line.endswith("|"):
            cells = [cell.strip() for cell in line[1:-1].split("|")]
        else:
            cells = [cell.strip() for cell in re.split(r"\s{2,}", line) if cell.strip()]
        if len(cells) >= 2:
            rows.append([cleanup_math_fragments(cell) for cell in cells])
    return rows


def render_pipe_table(rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    width = max(len(row) for row in rows)
    normalized = [row + [""] * (width - len(row)) for row in rows]
    output = ["| " + " | ".join(normalized[0]) + " |"]
    output.append("| " + " | ".join(["---"] * width) + " |")
    output.extend("| " + " | ".join(row) + " |" for row in normalized[1:])
    return output


def repair_layout_block(block: list[str], formulas: dict[str, dict[str, str]]) -> list[str]:
    output: list[str] = []
    has_image = any(IMAGE_RE.search(line) for line in block)
    has_display_formula = any(is_display_formula_line(line, formulas) for line in block)
    has_caption = any(CAPTION_RE.match(clean_table_cell(line)) for line in block)

    if has_display_formula:
        for line in block:
            if is_display_formula_line(line, formulas):
                _, item = formula_image(line, formulas)  # type: ignore[misc]
                if output and output[-1] != "":
                    output.append("")
                output.extend(render_display_formula(item))
                output.append("")
            elif CAPTION_RE.match(clean_table_cell(line)):
                rendered = render_caption(line)
                if rendered:
                    output.extend(rendered)
                    output.append("")
        return trim_blank(output)

    if has_image:
        for line in block:
            if is_rule(line) or PIPE_ONLY_RE.match(line.strip()):
                continue
            rendered_formula = render_formula_image_line(line)
            if rendered_formula:
                output.extend(rendered_formula)
                output.append("")
                continue
            rendered_alt = render_image_alt_caption(line)
            if rendered_alt:
                output.extend(rendered_alt)
                output.append("")
                continue
            rendered_caption = render_caption(line)
            if rendered_caption:
                output.extend(rendered_caption)
                output.append("")
                continue
            imgs = IMAGE_RE.findall(line)
            if imgs:
                for _, target in imgs:
                    output.append(f"![]({normalize_target(target)})")
                output.append("")
                continue
            cleaned = clean_table_cell(line)
            if cleaned:
                output.append(cleanup_math_fragments(cleaned))
        return trim_blank(output)

    rows = parse_rows_from_block(block)
    if rows:
        captions: list[str] = []
        for line in block:
            rendered = render_caption(line)
            if rendered:
                captions.extend(rendered)
                captions.append("")
        if captions:
            return trim_blank(captions + render_pipe_table(rows))
        return render_pipe_table(rows)
    if has_caption:
        for line in block:
            rendered = render_caption(line)
            if rendered:
                output.extend(rendered)
    return trim_blank(output)


def trim_blank(lines: list[str]) -> list[str]:
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def repair_normal_line(line: str, formulas: dict[str, dict[str, str]]) -> list[str]:
    if not line.strip():
        return [""]
    rendered_toc = render_toc_entry(line)
    if rendered_toc:
        return rendered_toc
    rendered_formula = render_formula_image_line(line)
    if rendered_formula:
        return rendered_formula
    rendered_alt = render_image_alt_caption(line)
    if rendered_alt:
        return rendered_alt
    rendered_heading = render_heading(line)
    if rendered_heading:
        return rendered_heading
    rendered_caption = render_caption(line)
    if rendered_caption:
        return rendered_caption
    if is_display_formula_line(line, formulas):
        _, item = formula_image(line, formulas)  # type: ignore[misc]
        return render_display_formula(item)
    line = replace_inline_images(line, formulas)
    line = DOCX_ANCHOR_RE.sub("", line)
    line = SPAN_ANCHOR_RE.sub("", line)
    line = cleanup_math_fragments(line)
    if PIPE_ONLY_RE.match(line):
        return []
    return [line.strip()]


def repair_blocks(text: str, formulas: dict[str, dict[str, str]]) -> str:
    lines = text.splitlines()
    output: list[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        rendered_formula = render_formula_image_line(line)
        if rendered_formula:
            output.extend(rendered_formula)
            output.append("")
            idx += 1
            if idx < len(lines) and is_pipe_alignment(lines[idx]):
                idx += 1
            continue
        rendered_image_only = render_image_only_table_line(line)
        if rendered_image_only:
            output.extend(rendered_image_only)
            output.append("")
            idx += 1
            if idx < len(lines) and is_pipe_alignment(lines[idx]):
                idx += 1
            continue
        if (
            is_empty_pipe_row(line)
            and idx + 2 < len(lines)
            and is_pipe_alignment(lines[idx + 1])
            and (
                render_formula_image_line(lines[idx + 2])
                or render_image_only_table_line(lines[idx + 2])
            )
        ):
            idx += 2
            continue
        if GRID_RULE_RE.match(line.strip()) or re.match(r"^\s*-{5,}\s*$", line):
            block = [line]
            idx += 1
            while idx < len(lines) and is_tableish(lines[idx]):
                block.append(lines[idx])
                idx += 1
            repaired = repair_layout_block(block, formulas)
            if repaired:
                if output and output[-1] != "":
                    output.append("")
                output.extend(repaired)
                output.append("")
            continue
        repaired_line = repair_normal_line(line, formulas)
        output.extend(repaired_line)
        idx += 1
    return "\n".join(output)


def normalize_blank_lines(text: str) -> str:
    text = cleanup_math_fragments(text)
    text = re.sub(
        r"(?m)^((?:> )?-\s+\[(?P<title>\d+(?:\.\d+)*\s+[^\]]+)\])\(#(?!sec-)[^)]+\)$",
        lambda m: f"{m.group(1)}(#{sec_id(m.group('title'))})",
        text,
    )
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip() + "\n"


def main() -> None:
    args = parse_args()
    source = args.markdown
    formulas, manifest_report = load_formula_manifest(args.formula_manifest, args.allow_unverified)
    text = source.read_text(encoding="utf-8")
    text = repair_split_docx_anchors(text)
    toc_map, ref_map = collect_anchor_maps(text, formulas)
    text = repair_citation_links(text)
    text = update_cross_links(text, toc_map, ref_map)
    text = repair_blocks(text, formulas)
    text = DOCX_ANCHOR_RE.sub("", text)
    text = SPAN_ANCHOR_RE.sub("", text)
    text = update_cross_links(text, toc_map, ref_map)
    text = normalize_blank_lines(text)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8", newline="\n")
    if args.manifest_report:
        args.manifest_report.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_report.write_text("\n".join(manifest_report) + "\n", encoding="utf-8")
    print(f"output={args.output}")
    print(f"toc_anchors={len(toc_map)}")
    print(f"ref_anchors={len(ref_map)}")
    print(f"formula_entries={len(formulas)}")


if __name__ == "__main__":
    main()
