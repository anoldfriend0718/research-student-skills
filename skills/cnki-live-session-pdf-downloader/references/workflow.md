# CNKI Live-Session PDF Workflow

## Preconditions

Use this workflow only when the user already has lawful CNKI or institutional access in a live Chrome or Edge session. The browser session is the source of truth.

Do not bypass login, CAPTCHA, paywalls, entitlement checks, or institutional restrictions. If CNKI shows any manual gate, stop and let the user complete it.

## Inputs

The default batch directory contains:

- `download_queue.tsv`
- `cnki_link_audit.tsv`

Recommended queue fields: `index`, `title`, `status`, `format`, `saved_file`, `note`, `safe_title`.
Recommended audit fields: `index`, `title`, `final_url`, `pdf_url`, `caj_url`.

Open `final_url` for each row and click the CNKI detail-page download button. Treat `pdf_url` as audit data, not a stable direct-download endpoint.

## Browser Setup

1. Start or confirm Chrome/Edge with a DevTools port, commonly `127.0.0.1:9222`.
2. Let the user sign in to CNKI or the institution manually.
3. Open a representative CNKI article detail page and confirm `PDF下载` or `CAJ下载` is visible.
4. Keep that browser window open during the run.

Probe the port:

```powershell
Invoke-RestMethod http://127.0.0.1:9222/json/version
```

## Probe One Row

Always start a new session with `--limit 1`:

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

Accept success only when a local file exists and header sniffing identifies PDF/CAJ/KDH content.

## Run Batches

After the one-row probe succeeds, run small batches:

```powershell
node scripts/cnki_edge_devtools_fetch.js `
  --input-dir C:\path\to\cnki_downloads `
  --debug-port 9222 `
  --limit 10 `
  --page-wait-ms 12000 `
  --download-wait-ms 180000 `
  --download-start-wait-ms 15000 `
  --inter-item-sleep-ms 6000
```

Use 6-8 seconds between rows. Increase `--download-wait-ms` for theses or large files.

If a row reaches `download_incomplete_timeout`, stop the batch and audit before retrying. Slow downloads can otherwise be misassigned to the next row.

## Validate

Run basic validation:

```powershell
python scripts/validate_cnki_downloads.py --input-dir C:\path\to\cnki_downloads
```

Run title-text validation when `pypdf` is available:

```powershell
python scripts/validate_cnki_downloads.py --input-dir C:\path\to\cnki_downloads --text-check
```

Some CNKI PDFs extract garbled text due to font encoding. In those cases, cross-check `suggestedFilename`, file header, and queue metadata instead of treating text extraction alone as definitive.

## Missing URLs

Do not fabricate success for records without CNKI URLs. Mark them as `missing_url` or keep a manual-check note.
