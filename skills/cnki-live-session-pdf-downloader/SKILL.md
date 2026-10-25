---
name: cnki-live-session-pdf-downloader
description: Download CNKI PDF or CAJ papers through an already-authorized live Chrome/Edge DevTools session. Use when the user has lawful CNKI or institutional access, direct HTTP requests are blocked by login/session/source-application checks, and Codex needs to process CNKI queue/audit TSV files, click CNKI detail-page PDF/CAJ download controls, verify saved file headers, update download_queue.tsv, or troubleshoot CNKI browser-session downloads without bypassing login, CAPTCHA, paywalls, or entitlement limits.
---

# CNKI Live Session PDF Downloader

Use this skill when the browser session is the source of truth for CNKI downloads.

This skill is designed for CNKI detail-page workflows where command-line requests or direct `bar.cnki.net` download URLs fail, but the user has already completed lawful CNKI or institutional access in Chrome or Edge.

## Core Rules

- Stay inside the user's authorized browser session. Do not bypass login, CAPTCHA, payment, institutional entitlement, or download restrictions.
- Let the user complete all manual authentication steps. Stop if the page shows a CAPTCHA, institutional login, no entitlement, or other access gate.
- Open CNKI article detail pages and click the page's `PDF下载` or `CAJ下载` control. Do not rely on bare direct `bar.cnki.net` URLs as durable download links.
- Start with `--limit 1` for a new queue or browser session. Scale only after one file is saved and verified as PDF/CAJ/KDH rather than HTML.
- Treat slow downloads as high risk. If a download is still in progress at timeout, stop the batch and audit before continuing.
- Never mark a row as downloaded unless the saved file exists and its header is verified.

## Expected Inputs

The default workflow expects a directory containing:

- `download_queue.tsv`
- `cnki_link_audit.tsv`

Recommended queue columns: `index`, `title`, `status`, `format`, `saved_file`, `note`, `safe_title`.
Recommended audit columns: `index`, `title`, `final_url`, `pdf_url`, `caj_url`.

The script opens `final_url` and clicks the CNKI detail-page download button. It uses `pdf_url` only as audit evidence, not as the primary fetch target.

## Standard Workflow

1. Read [references/workflow.zh-CN.md](references/workflow.zh-CN.md) for Chinese operational guidance, or [references/workflow.md](references/workflow.md) for English guidance.
2. Confirm Chrome or Edge is already open with remote debugging, usually `127.0.0.1:9222`, and that the user has completed CNKI/institutional authorization.
3. Run a single-row probe with [scripts/cnki_edge_devtools_fetch.js](scripts/cnki_edge_devtools_fetch.js).
4. Validate the saved file with [scripts/validate_cnki_downloads.py](scripts/validate_cnki_downloads.py).
5. Continue in small batches with a 6-8 second inter-item delay and a long enough download timeout.
6. Re-run validation and inspect any `download_incomplete_timeout`, `auth_or_error_page`, `no_download_link`, or `download_failed_or_non_document` rows before retrying.

## Commands

Probe the live Edge session from a queue directory:

```powershell
node scripts/cnki_edge_devtools_fetch.js `
  --input-dir C:\path\to\cnki_downloads `
  --debug-port 9222 `
  --limit 1 `
  --page-wait-ms 12000 `
  --download-wait-ms 180000 `
  --download-start-wait-ms 15000 `
  --inter-item-sleep-ms 6000
```

Validate headers and queue consistency:

```powershell
python scripts/validate_cnki_downloads.py --input-dir C:\path\to\cnki_downloads
```

Optional text/title audit when `pypdf` is available:

```powershell
python scripts/validate_cnki_downloads.py --input-dir C:\path\to\cnki_downloads --text-check
```

## References

- Read [references/workflow.zh-CN.md](references/workflow.zh-CN.md) for the recommended Chinese workflow and parameter choices.
- Read [references/workflow.md](references/workflow.md) for the English workflow.
- Read [references/troubleshooting.md](references/troubleshooting.md) when the DevTools port is unavailable, CNKI shows an authorization page, direct URLs fail, downloads do not start, a slow download causes file misassignment, saved files are HTML, or Windows path/encoding issues appear.
