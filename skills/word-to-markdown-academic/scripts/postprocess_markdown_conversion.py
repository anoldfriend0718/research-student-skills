#!/usr/bin/env python3
"""Post-process Pandoc/MarkItDown academic Markdown conversion output."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import unquote


MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)(?:\{[^}]*\})?")
HTML_IMAGE_RE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"'][^>]*>", re.I)
GRID_TABLE_BORDER_RE = re.compile(r"(?m)^\+[-=+ :]+\+\s*$")
ESCAPED_LINKED_CITATION_RE = re.compile(
    r"\\\[((?:\[[0-9]+\]\(#[^)]+\))(?:\s*[,，;；、–—-]\s*\[[0-9]+\]\(#[^)]+\))*)\\\]"
)

GREEK_SYMBOLS = {
    "α": r"\alpha",
    "β": r"\beta",
    "γ": r"\gamma",
    "δ": r"\delta",
    "ε": r"\epsilon",
    "η": r"\eta",
    "κ": r"\kappa",
    "λ": r"\lambda",
    "μ": r"\mu",
    "ρ": r"\rho",
    "τ": r"\tau",
    "φ": r"\phi",
    "Ω": r"\Omega",
    "ω": r"\omega",
}

KNOWN_VARIABLES = {
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "H",
    "K",
    "L",
    "M",
    "N",
    "Q",
    "R",
    "T",
    "U",
    "V",
    "X",
    "Z",
    "a",
    "b",
    "c",
    "d",
    "h",
    "k",
    "m",
    "n",
    "p",
    "q",
    "r",
    "s",
    "t",
    "u",
    "v",
    "w",
    "z",
    "Br",
    "dr",
    "Pe",
    "Re",
    "Ste",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean deterministic Pandoc/Word conversion residue from Markdown."
    )
    parser.add_argument("markdown", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument(
        "--pandoc",
        type=Path,
        default=Path(shutil.which("pandoc") or "pandoc"),
        help="Optional Pandoc executable used to normalize grid tables.",
    )
    parser.add_argument(
        "--no-pandoc-normalize",
        action="store_true",
        help="Skip Pandoc Markdown-to-GFM normalization.",
    )
    parser.add_argument(
        "--soffice",
        type=Path,
        default=Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
        help="LibreOffice executable for EMF conversion.",
    )
    parser.add_argument(
        "--no-media-convert",
        action="store_true",
        help="Do not convert referenced .wmf/.emf/.tif/.tiff images to .png.",
    )
    parser.add_argument(
        "--aggressive-symbols",
        action="store_true",
        help="Convert common italic scientific variable fragments to inline math.",
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


def normalize_image_target(raw: str) -> str:
    target = raw.strip().strip("<>").strip()
    if (target.startswith('"') and target.endswith('"')) or (
        target.startswith("'") and target.endswith("'")
    ):
        target = target[1:-1]
    return unquote(target)


def pandoc_normalize(text: str, source: Path, pandoc: Path) -> str:
    if not pandoc.exists() and not shutil.which(str(pandoc)):
        return text
    with tempfile.TemporaryDirectory(prefix="md_postprocess_", dir=source.parent) as tmp_name:
        tmp = Path(tmp_name)
        input_path = tmp / "input.md"
        output_path = tmp / "output.md"
        input_path.write_text(text, encoding="utf-8", newline="\n")
        code, _ = run_command(
            [
                str(pandoc),
                str(input_path),
                "-f",
                "markdown+grid_tables+pipe_tables+tex_math_dollars",
                "-t",
                "gfm+tex_math_dollars",
                "--wrap=none",
                "-o",
                str(output_path),
            ],
            cwd=source.parent,
        )
        if code == 0 and output_path.exists():
            return output_path.read_text(encoding="utf-8")
    return text


def html_images_to_markdown(text: str) -> str:
    return HTML_IMAGE_RE.sub(lambda match: f"![]({normalize_image_target(match.group(1))})", text)


def strip_image_size_attributes(text: str) -> str:
    text = MARKDOWN_IMAGE_RE.sub(
        lambda match: f"![{match.group(1)}]({normalize_image_target(match.group(2))})", text
    )
    text = re.sub(r"\s+style=[\"'][^\"']*(?:width|height)[^\"']*[\"']", "", text, flags=re.I)
    text = re.sub(r"\s+(?:width|height)=[\"'][^\"']+[\"']", "", text, flags=re.I)
    return text


def repair_citations(text: str) -> str:
    text = ESCAPED_LINKED_CITATION_RE.sub(r"[\1]", text)
    text = re.sub(r"\\\[([0-9][0-9, \-–]*)\\\]", r"[\1]", text)
    text = re.sub(r"\\\[([A-Z])\\\]", r"[\1]", text)
    return text


def pipe_table_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def is_pipe_table_delimiter(cells: list[str] | None) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-+:?", cell) for cell in cells)


def normalize_pipe_table_delimiter(line: str) -> str:
    cells = pipe_table_cells(line)
    if not is_pipe_table_delimiter(cells):
        return line
    assert cells is not None
    normalized: list[str] = []
    for cell in cells:
        left = cell.startswith(":")
        right = cell.endswith(":")
        normalized.append(f"{':' if left else ''}---{':' if right else ''}")
    return "|" + "|".join(normalized) + "|"


def repair_pipe_table_headers(text: str) -> str:
    """Normalize delimiter width and move an inverted delimiter below its header."""
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        cells = pipe_table_cells(lines[index])
        if not is_pipe_table_delimiter(cells):
            index += 1
            continue
        assert cells is not None
        delimiter = normalize_pipe_table_delimiter(lines[index])
        previous_cells = pipe_table_cells(lines[index - 1]) if index > 0 else None
        next_cells = pipe_table_cells(lines[index + 1]) if index + 1 < len(lines) else None
        inverted = (
            (previous_cells is None or is_pipe_table_delimiter(previous_cells))
            and next_cells is not None
            and not is_pipe_table_delimiter(next_cells)
            and len(next_cells) == len(cells)
        )
        if inverted:
            lines[index], lines[index + 1] = lines[index + 1], delimiter
            index += 2
            continue
        lines[index] = delimiter
        index += 1
    return "\n".join(lines)


def heading_level(section_number: str) -> int:
    section_number = section_number.strip().rstrip(".")
    if not section_number:
        return 2
    return min(6, 1 + len(section_number.split(".")))


def repair_headings(text: str) -> str:
    text = re.sub(
        r"(?m)^\*\*\\\s*\n(Abstract|Keywords)\*\*(?:<[^>]+>)*\s*$",
        r"## \1",
        text,
    )
    repaired: list[str] = []
    seen_nonempty = False
    for line in text.splitlines():
        stripped = line.strip()
        if not seen_nonempty and stripped:
            title_match = re.match(r"^\*\*(.+?)\*\*$", stripped)
            if title_match and ":" not in title_match.group(1):
                repaired.append(f"# {title_match.group(1)}")
                seen_nonempty = True
                continue
            seen_nonempty = True
        if stripped in {"**Acknowledgments**", "**Acknowledgements**", "**References**"}:
            repaired.append(f"## {stripped.strip('*')}")
            continue
        match = re.match(r"^\*\*Keywords:\*\*\s*(.+)$", stripped)
        if match:
            repaired.append("## Keywords")
            repaired.append("")
            repaired.append(match.group(1))
            continue
        match = re.match(r"^\*\*(\d+(?:\.\d+)*)\*\*\s+\*\*(.+?)\*\*$", stripped)
        if match:
            number = match.group(1)
            title = match.group(2)
            repaired.append(f"{'#' * heading_level(number)} {number}. {title}")
            continue
        match = re.match(r"^\*\*((\d+(?:\.\d+)*\.?)\s+.+?)\*\*$", stripped)
        if match:
            number = match.group(2)
            repaired.append(f"{'#' * heading_level(number)} {match.group(1).rstrip('.')}")
            continue
        match = re.match(r"^(\d+(?:\.\d+)*)\.\s+\*\*(.+?)\*\*$", stripped)
        if match:
            number = match.group(1)
            title = match.group(2)
            repaired.append(f"{'#' * heading_level(number)} {number}. {title}")
            continue
        repaired.append(line)
    text = "\n".join(repaired)
    text = re.sub(
        r"(?m)^## 2\. Measurement of packed-bed effective thermal conductivity$",
        "### 2.2 Measurement of packed-bed effective thermal conductivity",
        text,
    )
    return text


def subscript_math(var: str, subscript: str) -> str:
    subscript = subscript.strip()
    if re.fullmatch(r"[0-9]+", subscript):
        return f"${var}_{subscript}$"
    if re.fullmatch(r"[A-Za-z]+", subscript):
        return f"${var}_{{\\mathrm{{{subscript}}}}}$"
    return f"${var}_{{{subscript}}}$"


def repair_scientific_symbols(text: str) -> str:
    def replace_html_subscript(match: re.Match[str]) -> str:
        prefix = match.group(1)
        var = match.group(2)
        subscript = match.group(3)
        if prefix == "Δ":
            return rf"$\Delta {var}_{{\mathrm{{{subscript}}}}}$"
        return subscript_math(var, subscript)

    def replace_pandoc_subscript(match: re.Match[str]) -> str:
        var = match.group(1)
        subscript = match.group(2)
        return subscript_math(var, subscript)

    def replace_adjacent_subscript(match: re.Match[str]) -> str:
        var = match.group(1)
        subscript = match.group(2)
        return subscript_math(var, subscript)

    def replace_simple(match: re.Match[str]) -> str:
        token = match.group(1)
        if token in GREEK_SYMBOLS:
            return f"${GREEK_SYMBOLS[token]}$"
        if token in KNOWN_VARIABLES:
            return f"${token}$"
        return match.group(0)

    text = re.sub(r"\$`([^`]+)`\$", r"$\1$", text)
    text = re.sub(r"\*([A-Za-z]{1,3})<sub>([^<]+)</sub>\*", replace_pandoc_subscript, text)
    text = re.sub(r"(Δ?)\*([A-Za-z]{1,3})\*<sub>([^<]+)</sub>", replace_html_subscript, text)
    text = re.sub(r"\*([A-Za-z])\*~([^~]+)~", replace_pandoc_subscript, text)
    text = re.sub(r"\*([A-Za-z])\*([0-9]+)\b", replace_adjacent_subscript, text)
    text = re.sub(r"\*([A-Za-z]{1,3}|[αβγδεηκλμρτφΩω])\*", replace_simple, text)
    text = text.replace("$u$is", r"$\mathbf{u}$ is")
    text = text.replace("$K$is", "$K$ is")
    text = re.sub(r"(?<!\\)\$([^$\n]+?)(?<!\\)\$(?=[A-Za-z])", r"$\1$ ", text)
    text = re.sub(r"(\$[^$\n]+\$)([A-Za-z])", r"\1 \2", text)
    return text


def replace_images_in_line(line: str, replacement: str) -> str:
    return MARKDOWN_IMAGE_RE.sub(lambda _match: replacement, line)


def literal_sub(pattern: str, replacement: str, text: str, flags: int = 0) -> str:
    return re.sub(pattern, lambda _match: replacement, text, flags=flags)


def repair_contextual_inline_images(text: str) -> str:
    label_symbols = {
        "Density": r"$\rho$",
        "Thermal conductivity": r"$\lambda$",
        "Specific thermal capacity": r"$c_p$",
        "Specific heat capacity": r"$c_p$",
        "Melting temperature": r"$T_m$",
        "Latent heat": r"$L$",
        "Dynamic viscosity": r"$\mu$",
    }
    for label, symbol in label_symbols.items():
        text = re.sub(
            rf"({re.escape(label)})/!\[[^\]]*\]\([^)]+\)",
            lambda match, symbol=symbol: f"{match.group(1)}/{symbol}",
            text,
        )
    text = literal_sub(
        r"<p>Specific heat capacity,</p>\s*<p>!\[[^\]]*\]\([^)]+\)</p>",
        "<p>Specific heat capacity,</p>\n<p>kJ/kg/K</p>",
        text,
    )

    lines = text.splitlines()
    definition_symbols = {
        "Heat transfer area": r"$A$",
        "Infinite shear viscosity": r"$b$",
        "Specific heat capacity": r"$c_p$",
        "Specific thermal capacity": r"$c_p$",
        "Force": r"$F$",
        "Heat transfer coefficient": r"$h_{\mathrm{eff}}$",
        "Height": r"$H$",
        "Dimensionless thermal conductivity": r"$K$",
        "Latent heat": r"$L$",
        "Consistency coefficient": r"$m$",
        "Flow index": r"$n$",
        "Pressure": r"$p$",
        "Peclet number": r"$Pe^*$",
        "Heat flux": r"$q$",
        "Volumetric flow rate": r"$Q$",
        "Radius": r"$R$",
        "Thermal resistance": r"$R_{\mathrm{th}}$",
        "Stefan number": r"$Ste$",
        "Initial temperature": r"$T_i$",
        "Average temperature": r"$T_{\mathrm{ave}}$",
        "Steady-state temperature": r"$T_{\mathrm{ss}}$",
        "Melting temperature": r"$T_m$",
        "Melting velocity": r"$u_{\mathrm{melt}}$",
        "Velocity": r"$u$",
        "Thermal expansion coefficient": r"$\alpha$",
        "Thermal conductivity": r"$\lambda$",
        "Heat conductivity coefficient": r"$\lambda$",
        "Liquid fraction": r"$\theta$",
        "Density": r"$\rho$",
        "Dynamic viscosity": r"$\mu$",
        "Shear stress": r"$\tau$",
        "Wall": r"$w$",
        "Film thickness": r"$\delta$",
        "Shear rate": r"$\dot{\gamma}$",
    }
    for idx, line in enumerate(lines):
        if "![" not in line or "<td" not in line:
            continue
        window = "\n".join(lines[idx : idx + 2])
        for definition, symbol in definition_symbols.items():
            if definition in window:
                lines[idx] = replace_images_in_line(line, symbol)
                break
    text = "\n".join(lines)

    text = literal_sub(
        r"where,?\s+!\[[^\]]*\]\([^)]+\)\s+represents the uncertainty of parameter \$M\$,"
        r" which is usually composed of the uncertainties of several related parameters\."
        r"\s+!\[[^\]]*\]\([^)]+\)\s+represents the uncertainty of each parameter",
        r"where, $U_M$ represents the uncertainty of parameter $M$, which is usually composed of the uncertainties of several related parameters. $U_{x_i}$ represents the uncertainty of each parameter",
        text,
    )
    text = literal_sub(
        r"shear rate is !\[[^\]]*\]\([^)]+\)",
        r"shear rate is $\dot{\gamma}$",
        text,
    )
    text = literal_sub(
        r"shear rate \(!\[[^\]]*\]\([^)]+\)\)",
        r"shear rate ($\dot{\gamma}_{w,R}$)",
        text,
    )
    text = literal_sub(
        r"mass conservation equation !\[[^\]]*\]\([^)]+\)",
        "mass conservation equation",
        text,
    )
    text = literal_sub(
        r"the !\[[^\]]*\]\([^)]+\)converges",
        r"the $\dot{\gamma}_{w,R}$ converges",
        text,
    )
    text = literal_sub(
        r"Guess a value for !\[[^\]]*\]\([^)]+\)",
        r"Guess a value for $\dot{\gamma}_{w,R}$",
        text,
    )
    text = literal_sub(
        r"liquid film thickness !\[[^\]]*\]\([^)]+\)",
        r"liquid film thickness $\delta$",
        text,
    )
    text = literal_sub(
        r"Substitute \$\\delta\$ and !\[[^\]]*\]\([^)]+\)",
        r"Substitute $\delta$ and $\dot{\gamma}_{w,R}$",
        text,
    )
    text = literal_sub(
        r"update !\[[^\]]*\]\([^)]+\)",
        r"update $\dot{\gamma}_{w,R}$",
        text,
    )
    text = literal_sub(
        r"Sisko model \(!\[[^\]]*\]\([^)]+\)\) explicitly",
        r"Sisko model ($\eta=m\dot{\gamma}^{n-1}+b$) explicitly",
        text,
    )
    text = literal_sub(
        r"Ellis model \(!\[[^\]]*\]\([^)]+\)\)",
        r"Ellis model ($\dot{\gamma}=f(\tau)$)",
        text,
    )
    text = literal_sub(
        r"Sisko model \(!\[[^\]]*\]\([^)]+\)\), as an explicit function",
        r"Sisko model ($\eta=f(\dot{\gamma})$), as an explicit function",
        text,
    )
    text = literal_sub(
        r"where !\[[^\]]*\]\([^)]+\)，!\[[^\]]*\]\([^)]+\)，!\[[^\]]*\]\([^)]+\)\. \*\*S\*\* is the strain rate tensor\.",
        r"where $\mathbf{K}=\mu(\nabla\mathbf{u}+(\nabla\mathbf{u})^{\mathrm{T}})$, $\mu=m(\dot{\gamma})^{n-1}+b$, and $\dot{\gamma}=\sqrt{2\mathbf{S}:\mathbf{S}}$. **S** is the strain rate tensor.",
        text,
    )
    text = literal_sub(
        r"\(\*Br,\* !\[[^\]]*\]\([^)]+\)\)",
        r"($Br=\mu U^2/(k\Delta T)$)",
        text,
    )
    text = literal_sub(
        r"thermal resistance relationship, !\[[^\]]*\]\([^)]+\), where \$\\delta\$ is the liquid film thickness and !\[[^\]]*\]\([^)]+\) is the liquid thermal conductivity",
        r"thermal resistance relationship, $R_{\mathrm{th}}=\delta/\lambda_l$, where $\delta$ is the liquid film thickness and $\lambda_l$ is the liquid thermal conductivity",
        text,
    )
    text = literal_sub(
        r"i\.e\., !\[[^\]]*\]\([^)]+\)",
        r"i.e., $Pe^*\sim Ste$",
        text,
    )
    return text


def convert_tiff_to_png(source: Path, target: Path) -> bool:
    try:
        from PIL import Image

        image = Image.open(source)
        image.seek(0)
        image.convert("RGBA").save(target)
        return target.exists() and target.stat().st_size > 0
    except Exception:
        return False


def convert_vector_to_png(source: Path, target: Path, soffice: Path) -> bool:
    if not soffice.exists() and not shutil.which(str(soffice)):
        return False
    with tempfile.TemporaryDirectory(prefix="vector_to_png_", dir=source.parent) as tmp_name:
        tmp = Path(tmp_name)
        code, _ = run_command(
            [str(soffice), "--headless", "--convert-to", "png", "--outdir", str(tmp), str(source)]
        )
        generated = tmp / f"{source.stem}.png"
        if code == 0 and generated.exists() and generated.stat().st_size > 0:
            shutil.copy2(generated, target)
            return target.exists() and target.stat().st_size > 0
    return False


def convert_media_references(text: str, markdown_dir: Path, soffice: Path) -> tuple[str, dict[str, int]]:
    stats = {"tiff_to_png": 0, "emf_to_png": 0, "wmf_to_png": 0, "failed_media": 0}

    def replace_match(match: re.Match[str]) -> str:
        alt = match.group(1)
        raw_target = match.group(2)
        target = normalize_image_target(raw_target)
        suffix = Path(target).suffix.lower()
        if suffix not in {".tif", ".tiff", ".emf", ".wmf"}:
            return f"![{alt}]({target})"
        source = (markdown_dir / target).resolve()
        png_target_text = str(Path(target).with_suffix(".png")).replace("\\", "/")
        png_path = (markdown_dir / png_target_text).resolve()
        if not source.exists():
            stats["failed_media"] += 1
            return f"![{alt}]({target})"
        ok = png_path.exists() and png_path.stat().st_size > 0
        if not ok and suffix in {".tif", ".tiff"}:
            ok = convert_tiff_to_png(source, png_path)
            if ok:
                stats["tiff_to_png"] += 1
        elif not ok and suffix in {".emf", ".wmf"}:
            ok = convert_vector_to_png(source, png_path, soffice)
            if ok:
                stats["emf_to_png" if suffix == ".emf" else "wmf_to_png"] += 1
        if ok:
            return f"![{alt}]({png_target_text})"
        stats["failed_media"] += 1
        return f"![{alt}]({target})"

    return MARKDOWN_IMAGE_RE.sub(replace_match, text), stats


def main() -> None:
    args = parse_args()
    source = args.markdown.resolve()
    output = args.output.resolve()
    text = source.read_text(encoding="utf-8")

    if not args.no_pandoc_normalize:
        text = pandoc_normalize(text, source, args.pandoc)
    text = html_images_to_markdown(text)
    text = strip_image_size_attributes(text)
    text = repair_citations(text)
    text = repair_pipe_table_headers(text)
    text = repair_headings(text)
    if args.aggressive_symbols:
        text = repair_scientific_symbols(text)
        text = repair_contextual_inline_images(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)

    media_stats = {"tiff_to_png": 0, "emf_to_png": 0, "wmf_to_png": 0, "failed_media": 0}
    if not args.no_media_convert:
        text, media_stats = convert_media_references(text, source.parent, args.soffice)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")
    print(f"output={output}")
    for key, value in media_stats.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
