"""Convert a DOCX into a new Markdown working copy without overwriting sources."""
import argparse
import os
from pathlib import Path
import subprocess
from pandoc_cli import find_pandoc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docx", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--extract-media", type=Path)
    args = parser.parse_args()
    source, output = args.docx.resolve(), args.output.resolve()
    if not source.is_file() or source.suffix.lower() != ".docx":
        parser.error("Input must be an existing .docx file")
    if output.suffix.lower() != ".md" or output.exists():
        parser.error("Output must be a new .md file; existing files are preserved")
    media_root = args.extract_media.resolve() if args.extract_media else output.parent
    existing_media = media_root / "media"
    if existing_media.exists() and any(existing_media.iterdir()):
        parser.error("Media folder is not empty; use a new output directory")
    pandoc = find_pandoc()
    output.parent.mkdir(parents=True, exist_ok=True)
    media_root.mkdir(parents=True, exist_ok=True)
    media_argument = os.path.relpath(media_root, output.parent)
    subprocess.run([pandoc, str(source), "--standalone", "--wrap=none",
                    "-t", "markdown+tex_math_dollars+pipe_tables",
                    f"--extract-media={media_argument}", "-o", str(output)],
                   cwd=output.parent, check=True)
    print("Created:", output)
    print("Inspect formulas, captions, and media; conversion does not prove scientific correctness.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
