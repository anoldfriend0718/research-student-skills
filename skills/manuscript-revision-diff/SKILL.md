---
name: manuscript-revision-diff
description: Generate English-only, word-level side-by-side HTML comparisons of two academic Markdown manuscript versions, including bilingual working copies, tables, captions, equations and relocated paragraphs. Use for revision review, student-versus-author comparison, or a locally synchronized comparison page.
---

# Manuscript Revision Diff

Create a reviewable comparison without editing either source. Designed for GPT-6/Codex workflows; no model-specific API or external service is required.

## Resolve the versions

Use the user's chosen baseline and current version. Read project handoff/version notes when names are ambiguous. A student-faithful revision, a submitted manuscript and a previous authoritative manuscript are distinct baselines: never substitute one silently. Show meaningful left/right labels. Do not rewrite, polish, accept comments, or normalize scientific content as part of comparison.

Inputs are UTF-8 Markdown. For Word-only sources, first use an available document conversion workflow with an explicit tracked-change/comment policy; this tool does not read DOCX or decide whether to adopt comments. It ignores Markdown bold/italic formatting differences, Chinese prose and images, but retains English captions, table text and equations. It supports separate bilingual paragraphs and common bilingual headings/cells; inspect extracted text for other layouts. It is not a bilingual or visual-layout diff.

## Generate

Run `scripts/english_diff.py` with Python 3.10+:

```text
python english_diff.py --baseline BASE.md --current CURRENT.md --out OUTPUT_DIR --baseline-label "Student revision" --current-label "Current author revision"
```

Use a new derived-output directory when creating a different comparison; preserve existing comparison pages and source files. Paths are explicit, not inferred from this skill's location. Outputs: `英文逐词对比.html`, both extracted English text files, `provenance.json` (input hashes, labels and counts), and `relocated_blocks.json`.

Math requires local Pandoc with MathML support. It is converted in whole units, not split by word highlighting. Prefer a verified Pandoc executable. If the environment uses a Python wrapper, pass `--pandoc-command-json` as a JSON argument array, e.g. `["/path/python", "/path/pandoc_shim.py"]`; use subprocess argument lists or proper shell quoting. No network/CDN is required for the HTML. Unsupported math fails visibly; do not silently ship raw broken TeX as rendered equations.

For requested live sync, add `--serve --port PORT` on an available local port. The server binds only to 127.0.0.1 and rebuilds on source changes when the page polls. On Windows launch a background process with a hidden window. Do not stop other preview servers. Static HTML is a snapshot; a running server is required for synchronization. Restart after script changes.

## Review the result

Check provenance identifies the intended files and confirm their hashes remain unchanged. The script checks that alignment preserves both extracted block multisets and current reading order. Review extracted English for omissions, particularly mixed-language lines and unusual tables. Inspect a changed numbered item, renamed heading, long revised paragraph, table and equation when present. Search/changes-only controls should work in the browser.

Structural anchors and conservative text similarity pair corresponding blocks. Confident relocated blocks are displayed at their current location with a relocation badge; ambiguous cases remain separate. Do not force unrelated text together just to eliminate blank cells. Formula source changes can be highlighted even when their rendered appearance is equivalent. Formatting-only edits are intentionally excluded.

Report the two versions, a clickable HTML link, verification performed, and material extraction limitations. Do not claim independent GPT-6 evaluation or scientific validation merely because the script ran.
