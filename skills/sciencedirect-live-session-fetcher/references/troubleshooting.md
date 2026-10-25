# Troubleshooting

## `no_pdf_metadata`

Common causes:

- the page is still on a bot verification or sign-in screen
- the article page did not fully load
- the session can see the article landing page but not the PDF metadata

What to do:

1. keep the same Chrome or Edge window open
2. manually open the target article in that window
3. click `View PDF`
4. rerun only the failed rows

## `viewer_extract_failed`

Common causes:

- the in-browser PDF viewer did not finish loading
- the tab opened a non-PDF error page
- the session expired between the article page and the PDF viewer page

What to do:

- increase `PageWaitSeconds`
- keep `InterItemSleepSeconds` at `5+`
- manually test one failed DOI in the same session
- if the page already exposed a signed `pdf.sciencedirectassets.com` URL, prefer rerunning with the current Chrome or Edge DevTools path instead of relying only on the in-viewer extractor

## `viewer_extract_failed` with a valid ScienceDirect signed URL

Common causes:

- the signed PDF URL is valid only inside the current authorized browser context
- a direct HTTP fetch outside the page context gets `403 Forbidden`
- the browser extension PDF viewer changed the page shape before PDF.js finished loading

What to do:

1. keep the same Chrome or Edge window open
2. disable PDF-handling extensions in the next fresh session
3. retry one row first
4. use the current DevTools fetcher, which now prefers in-page fetch for ScienceDirect signed URLs before falling back to viewer extraction

## The browser keeps showing bot verification pages

Likely causes:

- the session is not fully authorized yet
- the current network path is triggering a bot verification page
- the browser profile is too clean and needs a complete sign-in flow

What to do:

- finish the bot verification in the same Chrome or Edge window
- open a real article and its PDF manually first
- avoid opening too many articles quickly

## Probe says challenge page, but also shows PDF metadata

This can happen on ScienceDirect.

What to do:

1. trust the positive signals first: `has_view_pdf=true`, `has_pdf_metadata=true`, or a populated `pdf_url`
2. run a one-row probe download before the full batch
3. only continue to the full batch after that probe row is saved successfully

## The fetcher cannot attach to the session

Check:

- Chrome or Edge was launched with `--remote-debugging-port`
- the port matches your command, for example `9222`
- the Chrome or Edge window is still open

If needed, start a fresh Chrome session on macOS with:

```bash
bash ./scripts/launch_chrome_clone_remote_debug_macos.sh \
  --direct-connection \
  --disable-extensions \
  --one-shot-profile
```

## Existing main Chrome or Edge windows interfere

If you reuse a live profile, close all browser windows first. The recommended path is to use the dedicated launcher and isolated user-data directory instead.

## Chrome or Edge opens `extension://.../pdfjs/web/viewer.html?file=...`

Common causes:

- Adobe or another PDF-handling extension intercepted the PDF
- the extension wrapped the real short-lived ScienceDirect URL in its own viewer page

What to do:

1. start a fresh Chrome session with `--disable-extensions`
2. prefer `--one-shot-profile` for a clean run
3. do not reuse an old `file=` link after a few minutes; ScienceDirect signed URLs expire quickly

## Article rows with only DOI and no candidate URLs

This is supported. The fetcher will open `https://doi.org/<doi>` first.

## Network-specific access problems

This workflow does not solve access or routing problems by itself. If your institution requires a specific network path, VPN split tunneling, or campus egress route, fix that first and then rerun the workflow.

## Recommended default for ScienceDirect after repeated failures

Use a fresh one-shot Chrome session on macOS:

```bash
bash ./scripts/launch_chrome_clone_remote_debug_macos.sh \
  --direct-connection \
  --disable-extensions \
  --one-shot-profile \
  --remote-debugging-port 9222 \
  --url "https://doi.org/<doi>"
```

## Practical status guide

| Status or symptom | Likely cause | Recommended action |
| --- | --- | --- |
| `downloaded` | A valid PDF was saved. | Verify the file starts with `%PDF-`; continue or scale up. |
| `challenge_page` | The page looks like a bot verification page, or the page contains challenge markers. | If the browser visibly shows a challenge, finish it manually. If the probe also reports `has_view_pdf=true` and `has_pdf_metadata=true`, run one test row before judging it as failed. |
| `no_pdf_metadata` | The article loaded but no PDF candidate was visible when inspected. Some publisher pages populate links late. | Increase `page_wait_seconds` to `20` or `30`; manually open the article and click `View PDF` or `Download PDF` once; retry only failed rows. |
| `generic_pdf_fetch_failed` | A candidate PDF URL was found, but it returned HTML, a viewer page, an expired link, or an access page instead of PDF bytes. | Keep the same live browser open, increase wait time, and test one row. For Wiley, verify that the article page exposes `/doi/pdf`, `/doi/epdf`, or nested `/doi/pdfdirect/...`. |
| `access_not_in_subscription` | The current user/session lacks access. | Fix institutional login, VPN, campus route, or subscription access first; do not retry as an automation problem. |
| `existing_file` | The target PDF already exists. | Inspect or delete/move the existing output only if a fresh download is required. |

## Wiley and other HTML PDF viewer pages

Observed Wiley route:

1. Open the article page, for example `https://scijournals.onlinelibrary.wiley.com/doi/10.1002/ese3.506`.
2. The page may expose `citation_pdf_url`, `/doi/pdf/<doi>`, or `/doi/epdf/<doi>`.
3. Those URLs can return HTML viewer pages instead of PDF bytes.
4. The viewer can expose a nested endpoint such as `/doi/pdfdirect/<doi>`.
5. Fetch that nested endpoint inside the authorized page context.

Operational guidance:

- Keep CSV `note` on the article page or DOI landing page. Do not start from `pdfdirect` unless there is no normal article page.
- Use `page_wait_seconds` around `15` for Wiley and `20` to `30` for mixed publishers.
- If the first pass gives `no_pdf_metadata`, open the article manually in the same browser, confirm that `PDF` or `Download PDF` is visible, then retry one row.
- Treat Springer Nature, Taylor & Francis, ACS, MDPI, and similar publishers as best-effort unless each publisher has been tested with at least one accessible article.

## Recommended retry strategy

1. Do not rerun the full batch immediately.
2. Inspect `devtools_missing.csv` and group failures by status.
3. For `challenge_page`, solve the browser state first.
4. For `no_pdf_metadata`, increase `page_wait_seconds` and retry only those rows.
5. For `generic_pdf_fetch_failed`, test one representative article manually in the same browser and check whether the PDF button opens a viewer or a real PDF.
6. After one successful retry writes a valid `%PDF-` file, rerun the failed subset.

## Field-tested examples

- ScienceDirect: article page -> `pdfDownload` metadata -> signed `pdf.sciencedirectassets.com` URL -> in-page fetch.
- Wiley DOI `10.1002/ese3.506`: article page -> `/doi/pdf` or `/doi/epdf` HTML viewer -> `/doi/pdfdirect/...` -> in-page fetch. Verified output status: `downloaded`; verified PDF header: `%PDF-`.
