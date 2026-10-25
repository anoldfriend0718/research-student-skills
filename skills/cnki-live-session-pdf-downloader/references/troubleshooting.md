# CNKI Download Troubleshooting

## `mcp__chrome_devtools__...` tools are not exposed

Use the available live-browser route instead of waiting for tool names that are not present. If Edge/Chrome has `--remote-debugging-port=9222`, the bundled script can attach through the DevTools HTTP/WebSocket interface.

Check:

```powershell
Invoke-RestMethod http://127.0.0.1:9222/json/version
Invoke-RestMethod http://127.0.0.1:9222/json/list
```

If these fail, the browser was not started with remote debugging, the port differs, or a firewall/security setting blocks local access.

## Direct `pdf_url` gives `来源应用不正确` or an HTML error page

This is expected for many CNKI `bar.cnki.net` links. The URL is not a durable standalone download endpoint. Open the CNKI detail page (`final_url`) in the authorized browser and click `PDF下载` or `CAJ下载` from that page.

## Page shows login, CAPTCHA, or institutional authorization

Stop. Ask the user to complete the manual browser step. Do not script around CAPTCHA or entitlement checks.

Common indicators:

- `统一身份认证`
- `验证码`
- `请先登录`
- `登录后下载`
- `无权限`
- `未授权`
- `来源应用不正确`

## `no_download_link`

Possible causes:

- The detail page loaded incompletely. Increase `--page-wait-ms`.
- CNKI changed the page structure. Inspect the page manually for `PDF下载`, `CAJ下载`, `pdfDown`, or `cajDown`.
- The article only exposes CAJ or online reading. Retry with the page visible and confirm which controls exist.
- The row's `final_url` is stale. Re-audit the CNKI link.

## No `Browser.downloadWillBegin` event

Possible causes:

- The click did not hit the actual download control.
- Browser download prompts are blocking automatic download.
- CNKI opened an intermediate authorization page.
- The session lost institutional entitlement.

Use `--limit 1`, watch the browser, and inspect whether the click opens a new page, prompts, or an error message.

## `download_incomplete_timeout`

The file started but did not finish before `--download-wait-ms`. Do not continue the batch immediately. A late-completing file can be misassigned to the next row.

Recommended response:

1. Wait for the browser download UI to settle.
2. Inspect the output directory for new original CNKI filenames.
3. Validate file headers.
4. Match any late file to the row using the Edge `suggestedFilename`, PDF text/title, and queue title.
5. Rename/update the queue only after evidence matches.
6. Increase `--download-wait-ms` for the retry.

## Saved file is HTML or too small

Do not mark the row as downloaded. HTML usually means login, authorization error, or an intermediate CNKI error page. Keep the row as a failure status and let the user restore access manually.

## Duplicate or shifted files

A previous slow download may have completed during the next row. Audit adjacent rows using:

- Original download filename from `cnki_edge_probe_results.jsonl`
- `download_event_summary.suggestedFilename`
- File size and modification time
- PDF first pages or title text extraction
- Queue title and index

Move incorrect duplicates to a quarantine folder rather than deleting them.

## PowerShell shows Chinese filenames as mojibake

This can be display encoding, not file corruption. Use explicit UTF-8 reads or Python with relative paths from the current working directory.

Examples:

```powershell
Get-Content -Encoding UTF8 .\download_queue.tsv
```

Avoid hard-coding Chinese absolute paths inside native-process stdin when the console encoding is unstable. Prefer current-directory relative paths or values read from UTF-8 TSV files.

## `pypdf` title extraction is garbled

Some CNKI PDFs use embedded fonts or encodings that extract as unreadable text. Treat text extraction as advisory. Cross-check with:

- File header `%PDF-`
- Edge `suggestedFilename`
- CNKI original filename
- Page title in the detail page
- Manual visual inspection when necessary

## Writing to `.codex/skills` is blocked

Create and validate the skill in a workspace directory first. Then perform one explicit elevated copy/sync into `C:\Users\<user>\.codex\skills` after the files are correct.
