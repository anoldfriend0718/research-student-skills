# Cleanup Patterns For Academic DOCX To Markdown

Use these patterns as review prompts, not blind replacements. Check the surrounding sentence and preserve the author's notation.

## Inline Math Artifacts

Common converter output -> preferred Markdown:

- `k\_{eff}` -> `$k_{\mathrm{eff}}$`
- `Q\_{rxn}` -> `$Q_{\mathrm{rxn}}$`
- `c\_{Ca(OH)\_{2}}` -> `$c_{\mathrm{Ca(OH)}_2}$`
- `*T*max` -> `$T_{\max}$`
- `*T*min` -> `$T_{\min}$`
- `*p*eq` -> `$p_{\mathrm{eq}}$`
- `$u$is` -> `$\mathbf{u}$ is`
- `R_g` -> `$R_g$`
- `T_eq` -> `$T_{\mathrm{eq}}$`
- `Omega_rec` -> `$\Omega_{\mathrm{rec}}$`
- `E_input` -> `$E_{\mathrm{input}}$`
- `eta_HX` -> `$\eta_{\mathrm{HX}}$`

## Table Symbol Artifacts

Treat table cells the same as prose. Word converters often split a symbol into italic text plus plain or Pandoc subscript syntax; this loses the mathematical subscript in Markdown preview.

Common table output -> preferred Markdown:

- `*L*1` or `*L*~1~` -> `$L_1$`
- `*L*f` or `*L*~f~` -> `$L_f$`
- `*delta*f` or `*delta*~f~` -> `$\delta_f$`
- `*R*3` or `*R*~3~` -> `$R_3$`
- `*a*` in a symbol column -> `$a$`
- table coefficient headers `*A*`, `*B*`, `*C*`, `*D*`, `*E*` -> `$A$`, `$B$`, `$C$`, `$D$`, `$E$`

Only convert true symbol cells or coefficient headers. Do not convert ordinary emphasized words in prose-like table text.

## Formula Numbering

Use `\tag{n}` inside display math when the source Word equation has a visible number:

```latex
$$
\Delta T=T_{\max}-T_{\min}\tag{10}
$$
```

For multi-line equations:

```latex
$$
\begin{aligned}
a&=b,\\
c&=d.
\end{aligned}\tag{18}
$$
```

## Mojibake And MathJax Hazards

Pandoc may escape numeric citations as `\[1\]` or `\[43, 44\]`. In MathJax-aware Markdown previews this can render as display math and push citation numbers onto separate lines. Reference lists may also contain escaped type markers such as `\[J\]` and `\[M\]`.

Common repairs:

- `\[1\]` -> `[1]`
- `\[43, 44\]` -> `[43, 44]`
- `\[J\]` -> `[J]` in reference lists
- `\[M\]` -> `[M]` in reference lists
- `\[[1](#ref-1),[2](#ref-2)\]` -> `[[1](#ref-1),[2](#ref-2)]`; preserve the inner Markdown links and remove only the outer escapes
- corrupted superscript minus in units such as `s^U+922D?^` -> `s$^{-1}$` after context check
- corrupted degree-C text -> `\u00b0C` or literal degree-C only after confirming the file is written as UTF-8
- corrupted plus-minus, micro, Ohm, multiplication, and approximate signs -> infer from units/equations and write with code points or LaTeX (`\pm`, `\mu`, `\Omega`, `\times`, `\approx`)

When repairing with Python from PowerShell on Windows, avoid literal non-ASCII replacement strings in piped scripts if console encoding is uncertain. Use relative ASCII filenames from the output directory and Unicode/code-point construction such as `chr(0x00B1)`, `chr(0x00B0) + "C"`, `chr(0x03BC)`, and `chr(0x03A9)`. After writing, scan for accidental `?` substitutions around units.

## Layout And Short Formula Image Pass

- After cleanup, prose paragraphs should be unwrapped into one logical Markdown paragraph, not hard-wrapped at 60-90 characters.
- Preserve blank lines around headings, figures, tables, captions, fenced code, and `$$` display math.
- Convert short symbol/formula images inside sentences to LaTeX. Examples: `mu`, `lambda_l`, `c_p`, `T_m`, `delta`, `dot gamma`, `dot gamma_w`, `R_th`, `Pe^*`, and `u_melt`.
- Convert equation-image + number patterns to display math with `\tag{n}` whenever the equation can be visually reconstructed.
- Keep real figure panels as images, but do not leave formula images as sentence fragments.

## Pipe Table Parse Hazards

- The header must precede the delimiter: `| Symbol | Meaning |` then `|:---:|:---:|`.
- Each delimiter cell must contain at least three hyphens. Do not emit `|:--:|`; some renderers treat it as prose or an emoji token.
- Treat a delimiter line without a same-width pipe header immediately above it as a conversion error, not as an acceptable table variant.

## Media Red Flags

These must be resolved before the Markdown is considered usable:

- `![](data:image/png;base64...)`
- `image/x-wmf`
- `.wmf`
- `.emf`
- `.tiff`
- image links pointing to non-existent local files
- two consecutive figure images before one caption when the Word source has only one figure

## Search Patterns

Useful searches:

```powershell
python scripts/audit_markdown_conversion.py --strict manuscript.md
rg -n "data:image|image/x-wmf|\\.wmf|\\.emf|\\.tiff|\\_|\\*[A-Za-z]\\*|\\$[^$]+\\$[A-Za-z]" manuscript.md
rg -n "\\\\\[[0-9, -]+\\\\\]|\\\\\[\\[[0-9]+\\]\\(#[^)]+\\).*\\\\\]|\\\\\[[A-Za-z]\\\\\]|\\x{922D}\\?|\\x{9225}\\?|\\x{807D}|\\x{9230}|\\x{951B}|\\x{FFFD}|\\{width=|height=" manuscript.md
rg -n "^!\\[.*\\]\\(" manuscript.md
rg -n "\\\\tag\\{[0-9]+\\}" manuscript.md
```
