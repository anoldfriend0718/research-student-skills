#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

function parseArgs(argv) {
  const args = {
    debugPort: 9222,
    limit: 1,
    pageWaitMs: 12000,
    downloadWaitMs: 120000,
    downloadStartWaitMs: 15000,
    interItemSleepMs: 6000,
    mode: "probe",
  };
  for (let i = 2; i < argv.length; i += 1) {
    const key = argv[i];
    const value = argv[i + 1];
    if (key === "--debug-port") {
      args.debugPort = Number(value);
      i += 1;
    } else if (key === "--input-dir") {
      args.inputDir = value;
      i += 1;
    } else if (key === "--limit") {
      args.limit = Number(value);
      i += 1;
    } else if (key === "--page-wait-ms") {
      args.pageWaitMs = Number(value);
      i += 1;
    } else if (key === "--download-wait-ms") {
      args.downloadWaitMs = Number(value);
      i += 1;
    } else if (key === "--download-start-wait-ms") {
      args.downloadStartWaitMs = Number(value);
      i += 1;
    } else if (key === "--inter-item-sleep-ms") {
      args.interItemSleepMs = Number(value);
      i += 1;
    } else if (key === "--mode") {
      args.mode = value;
      i += 1;
    }
  }
  if (!args.inputDir) {
    throw new Error("--input-dir is required");
  }
  return args;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function parseTsv(text) {
  const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/).filter(Boolean);
  if (!lines.length) return [];
  const headers = splitTsvLine(lines[0]);
  if (headers[0]) headers[0] = headers[0].replace(/^\uFEFF/, "");
  return lines.slice(1).map(line => {
    const values = splitTsvLine(line);
    const row = {};
    headers.forEach((header, index) => {
      row[header] = values[index] ?? "";
    });
    return row;
  });
}

function splitTsvLine(line) {
  const out = [];
  let current = "";
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === "\"") {
      if (quoted && line[i + 1] === "\"") {
        current += "\"";
        i += 1;
      } else {
        quoted = !quoted;
      }
    } else if (ch === "\t" && !quoted) {
      out.push(current);
      current = "";
    } else {
      current += ch;
    }
  }
  out.push(current);
  return out;
}

function quoteTsv(value) {
  return `"${String(value ?? "").replace(/"/g, "\"\"")}"`;
}

function writeTsv(filePath, rows, headers) {
  const lines = [headers.map(quoteTsv).join("\t")];
  for (const row of rows) {
    lines.push(headers.map(header => quoteTsv(row[header] ?? "")).join("\t"));
  }
  fs.writeFileSync(filePath, `${lines.join("\n")}\n`, "utf8");
}

function safeName(text, fallback) {
  const cleaned = String(text || "")
    .replace(/[<>:"/\\|?*\u0000-\u001F]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 120);
  return cleaned || fallback;
}

function listFiles(dir) {
  return new Map(
    fs.readdirSync(dir)
      .filter(name => !name.endsWith(".crdownload") && !name.endsWith(".tmp"))
      .map(name => {
        const full = path.join(dir, name);
        const st = fs.statSync(full);
        return [name, { name, full, size: st.size, mtimeMs: st.mtimeMs }];
      }),
  );
}

function changedFiles(before, dir) {
  const after = listFiles(dir);
  const changed = [];
  for (const [name, file] of after.entries()) {
    const old = before.get(name);
    if (!old || old.size !== file.size || old.mtimeMs !== file.mtimeMs) {
      changed.push(file);
    }
  }
  changed.sort((a, b) => b.mtimeMs - a.mtimeMs);
  return changed;
}

function sniffFile(filePath) {
  const st = fs.statSync(filePath);
  const buf = Buffer.alloc(Math.min(64, st.size));
  const fd = fs.openSync(filePath, "r");
  try {
    fs.readSync(fd, buf, 0, buf.length, 0);
  } finally {
    fs.closeSync(fd);
  }
  const ascii = buf.toString("latin1");
  let format = "unknown";
  if (ascii.startsWith("%PDF-")) format = "PDF";
  else if (ascii.startsWith("CAJ")) format = "CAJ";
  else if (ascii.startsWith("KDH")) format = "CAJ";
  else if (/^\s*</.test(ascii)) format = "HTML";
  return { size: st.size, headHex: buf.toString("hex").slice(0, 64), headText: ascii.slice(0, 32), format };
}

async function httpJson(base, endpoint, options = {}) {
  const resp = await fetch(`${base}${endpoint}`, options);
  if (!resp.ok) {
    throw new Error(`${endpoint} HTTP ${resp.status}`);
  }
  return await resp.json();
}

class CdpSession {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.ws = null;
    this.nextId = 1;
    this.pending = new Map();
    this.events = [];
  }

  async connect() {
    this.ws = new WebSocket(this.wsUrl);
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error(`WebSocket timeout: ${this.wsUrl}`)), 15000);
      this.ws.addEventListener("open", () => {
        clearTimeout(timer);
        resolve();
      }, { once: true });
      this.ws.addEventListener("error", event => {
        clearTimeout(timer);
        reject(new Error(`WebSocket error: ${event.message || "unknown"}`));
      }, { once: true });
    });
    this.ws.addEventListener("message", event => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject, timer } = this.pending.get(msg.id);
        clearTimeout(timer);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(`${msg.error.message || "CDP error"} (${msg.error.code || ""})`));
        else resolve(msg.result);
      } else if (msg.method) {
        this.events.push(msg);
      }
    });
  }

  call(method, params = {}, timeoutMs = 30000) {
    const id = this.nextId;
    this.nextId += 1;
    const payload = JSON.stringify({ id, method, params });
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`${method} timeout`));
      }, timeoutMs);
      this.pending.set(id, { resolve, reject, timer });
      this.ws.send(payload);
    });
  }

  takeEvents(method) {
    const found = this.events.filter(event => event.method === method);
    this.events = this.events.filter(event => event.method !== method);
    return found;
  }

  close() {
    if (this.ws) this.ws.close();
  }
}

async function evaluate(session, expression, awaitPromise = false, timeoutMs = 30000) {
  const result = await session.call("Runtime.evaluate", {
    expression,
    returnByValue: true,
    awaitPromise,
  }, timeoutMs);
  if (result.exceptionDetails) {
    return null;
  }
  return result.result ? result.result.value : null;
}

async function openPage(base, url) {
  const endpoint = `/json/new?${encodeURIComponent(url)}`;
  return await httpJson(base, endpoint, { method: "PUT" });
}

async function closePage(base, pageId) {
  try {
    await fetch(`${base}/json/close/${pageId}`);
  } catch {
    // Best-effort cleanup only.
  }
}

async function waitForLoadOrStop(page, ms) {
  await sleep(ms);
  try {
    await page.call("Page.stopLoading", {}, 5000);
  } catch {
    // Some pages finish before stopLoading; ignore.
  }
}

function pageProbeExpression() {
  return `
(() => {
  const links = Array.from(document.querySelectorAll('a, button, [role="button"]')).map((el, index) => {
    const href = el.href || el.getAttribute('href') || el.getAttribute('data-href') || '';
    const onclick = el.getAttribute('onclick') || '';
    const text = (el.innerText || el.textContent || el.getAttribute('title') || el.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim();
    const id = el.id || '';
    const cls = el.className || '';
    return { index, tag: el.tagName, text: text.slice(0, 120), href, onclick: onclick.slice(0, 200), id, cls: String(cls).slice(0, 120) };
  }).filter(x => /PDF|CAJ|濠电姷鏁搁崑鐐哄垂閸洖绠伴柟闂寸贰閺佸嫰鏌涢锝囪穿鐟滅増甯掗梻顖炴煟閺傚灝鎮戦柍閿嬪浮閺屾盯骞囬埡浣割瀴闂佹悶鍊愰崑鎾翠繆閻愵亜鈧牕煤閹达箑纭€闁告劘灏欓弳锔戒繆閵堝懏鍣归幆鐔兼⒑閹稿孩鈷掗柡鍜佸亰閸┾偓妞ゆ帒鍊瑰▍锕傛⒒閸屾瑦绁版俊妞煎妿缁牊绗熼埀顒勫箖濞差亜惟闁靛鍨甸埀顒€娼￠弻锝呂旈埀顒勬偋韫囨稑鐓濋柡鍐ㄧ墛閸婄敻鏌ㄥ┑鍡涱€楁鐐搭殘缁辨帗鎷呴悜姗嗗敪download|read/i.test([x.text, x.href, x.onclick, x.id, x.cls].join(' ')));
  return {
    href: location.href,
    title: document.title,
    bodyText: (document.body ? document.body.innerText : '').replace(/\\s+/g, ' ').slice(0, 800),
    links: links.slice(0, 80)
  };
})()
`;
}

function clickCandidateExpression(prefer) {
  return `
(() => {
  const prefer = ${JSON.stringify(prefer)};
  const candidates = Array.from(document.querySelectorAll('a, button, [role="button"]')).map((el, index) => {
    const href = el.href || el.getAttribute('href') || el.getAttribute('data-href') || '';
    const onclick = el.getAttribute('onclick') || '';
    const text = (el.innerText || el.textContent || el.getAttribute('title') || el.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim();
    const id = el.id || '';
    const cls = String(el.className || '');
    const hay = [text, href, onclick, id, cls].join(' ');
    let score = 0;
    if (/PDF/i.test(hay)) score += prefer === 'PDF' ? 100 : 25;
    if (/CAJ/i.test(hay)) score += prefer === 'CAJ' ? 100 : 15;
    if (/濠电姷鏁搁崑鐐哄垂閸洖绠伴柟闂寸贰閺佸嫰鏌涢锝囪穿鐟滅増甯掗梻顖炴煟閹烘垹绀墂nload/i.test(hay)) score += 30;
    if (/闂傚倸鍊搁崐鎼佸磹閹间礁鐤い鎰剁畱缁犵娀鏌熼悙顒併仧闁轰礁顑呴湁闁稿繐鍚嬬紞鎴犵磼閳ь剟宕掗悙瀵稿帾婵犵數濮寸换妯侯瀶椤曗偓閺岋絾鎯旈敐鍡橆仯闂傚倸鍊搁崐鎼佸磹閹间礁鐤い鎰剁畱缁犵娀鏌熼悙顒併仧闁轰礁顑夐弻锝夊Ω灏夊〒鍝竏/i.test(hay)) score += 10;
    if (/bar\\.cnki\\.net|download\\/order/i.test(href)) score += 40;
    return { el, index, text, href, onclick, id, cls, score };
  }).filter(x => x.score > 0).sort((a, b) => b.score - a.score);
  if (!candidates.length) return { ok: false, reason: 'no_candidate' };
  const chosen = candidates[0];
  chosen.el.scrollIntoView({ block: 'center', inline: 'center' });
  const rect = chosen.el.getBoundingClientRect();
  return {
    ok: true,
    index: chosen.index,
    text: chosen.text.slice(0, 120),
    href: chosen.href,
    id: chosen.id,
    cls: String(chosen.cls).slice(0, 120),
    score: chosen.score,
    x: rect.left + rect.width / 2,
    y: rect.top + rect.height / 2,
    width: rect.width,
    height: rect.height
  };
})()
`;
}

function hasCnkiDownloadLink(probe) {
  const links = Array.isArray(probe?.links) ? probe.links : [];
  return links.some(link => {
    const hay = [link.text, link.href, link.id, link.onclick, link.cls].join(" ");
    return /PDF\u4e0b\u8f7d|CAJ\u4e0b\u8f7d|\u539f\u7248\u9605\u8bfb|pdfDown|cajDown|bar\.cnki\.net\/bar\/download\/order/i.test(hay);
  });
}

function isLikelyAuthOrErrorPage(probe) {
  const href = probe?.href || "";
  const title = probe?.title || "";
  const text = probe?.bodyText || "";
  if (hasCnkiDownloadLink(probe)) return false;
  if (/ErrorMsg|auth-check|login|passport|sso|cas/i.test(href)) return true;
  if (/\u9519\u8bef|\u767b\u5f55|\u7edf\u4e00\u8eab\u4efd\u8ba4\u8bc1|\u9a8c\u8bc1\u7801|\u65e0\u6743\u9650|\u672a\u6388\u6743|\u6765\u6e90\u5e94\u7528\u4e0d\u6b63\u786e/.test(title)) return true;
  if (/\u7edf\u4e00\u8eab\u4efd\u8ba4\u8bc1|\u9a8c\u8bc1\u7801|\u6765\u6e90\u5e94\u7528\u4e0d\u6b63\u786e|\u65e0\u6743\u9650|\u672a\u6388\u6743|\u8bf7\u5148\u767b\u5f55|\u767b\u5f55\u540e\u4e0b\u8f7d/.test(text)) return true;
  return false;
}

function compactProbe(probe) {
  if (!probe) return null;
  return {
    href: probe.href || "",
    title: probe.title || "",
    bodyText: String(probe.bodyText || "").slice(0, 240),
    downloadLinks: (Array.isArray(probe.links) ? probe.links : [])
      .filter(link => /PDF\u4e0b\u8f7d|CAJ\u4e0b\u8f7d|\u539f\u7248\u9605\u8bfb|pdfDown|cajDown|bar\.cnki\.net\/bar\/download\/order/i.test([
        link.text || "",
        link.href || "",
        link.id || "",
        link.cls || "",
      ].join(" ")))
      .slice(0, 8)
      .map(link => ({
        text: link.text || "",
        href: link.href || "",
        id: link.id || "",
        cls: link.cls || "",
      })),
  };
}

function summarizeDownloadEvents(events) {
  const willBegin = events.find(event => event.method === "Browser.downloadWillBegin");
  const progress = events.filter(event => event.method === "Browser.downloadProgress");
  const lastProgress = progress.length ? progress[progress.length - 1] : null;
  return {
    eventCount: events.length,
    suggestedFilename: willBegin?.params?.suggestedFilename || "",
    guid: willBegin?.params?.guid || lastProgress?.params?.guid || "",
    state: lastProgress?.params?.state || "",
    totalBytes: lastProgress?.params?.totalBytes || 0,
    receivedBytes: lastProgress?.params?.receivedBytes || 0,
  };
}
async function main() {
  const args = parseArgs(process.argv);
  const inputDir = path.resolve(args.inputDir);
  const auditPath = path.join(inputDir, "cnki_link_audit.tsv");
  const queuePath = path.join(inputDir, "download_queue.tsv");
  const probePath = path.join(inputDir, "cnki_edge_probe_results.jsonl");

  const auditRows = parseTsv(fs.readFileSync(auditPath, "utf8"));
  const queueRows = parseTsv(fs.readFileSync(queuePath, "utf8"));
  const queueHeaders = splitTsvLine(fs.readFileSync(queuePath, "utf8").split(/\r?\n/)[0]);
  if (queueHeaders[0]) queueHeaders[0] = queueHeaders[0].replace(/^\uFEFF/, "");
  const queueByIndex = new Map(queueRows.map(row => [row.index, row]));
  const targets = auditRows
    .filter(row => row.pdf_url && row.final_url && (queueByIndex.get(row.index)?.saved_file || "") === "")
    .slice(0, args.limit || auditRows.length);

  const base = `http://127.0.0.1:${args.debugPort}`;
  const version = await httpJson(base, "/json/version");
  const browser = new CdpSession(version.webSocketDebuggerUrl);
  await browser.connect();
  await browser.call("Browser.setDownloadBehavior", {
    behavior: "allow",
    downloadPath: inputDir,
    eventsEnabled: true,
  }, 10000);

  const results = [];
  let stopBatch = false;
  for (const row of targets) {
    const queueRow = queueByIndex.get(row.index);
    const result = {
      index: row.index,
      title: row.title,
      status: "started",
      final_url: row.final_url,
    };
    const before = listFiles(inputDir);
    let pageInfo = null;
    let page = null;
    try {
      pageInfo = await openPage(base, row.final_url);
      page = new CdpSession(pageInfo.webSocketDebuggerUrl);
      await page.connect();
      await page.call("Page.enable", {}, 10000);
      await page.call("Runtime.enable", {}, 10000);
      await waitForLoadOrStop(page, args.pageWaitMs);
      const probe = await evaluate(page, pageProbeExpression(), false, 15000);
      result.page = compactProbe(probe);
      if (probe && isLikelyAuthOrErrorPage(probe)) {
        result.status = "auth_or_error_page";
        result.note = (probe.bodyText || "").slice(0, 200);
      } else {
        const click = await evaluate(page, clickCandidateExpression("PDF"), false, 15000);
        result.click = click;
        if (!click || !click.ok) {
          result.status = "no_download_link";
        } else {
          browser.takeEvents("Browser.downloadWillBegin");
          browser.takeEvents("Browser.downloadProgress");
          await page.call("Input.dispatchMouseEvent", { type: "mouseMoved", x: click.x, y: click.y }, 5000);
          await page.call("Input.dispatchMouseEvent", { type: "mousePressed", x: click.x, y: click.y, button: "left", clickCount: 1 }, 5000);
          await page.call("Input.dispatchMouseEvent", { type: "mouseReleased", x: click.x, y: click.y, button: "left", clickCount: 1 }, 5000);
          const downloadEvents = [];
          const maxDownloadLoops = Math.max(1, Math.ceil(args.downloadWaitMs / 1000));
          for (let waitIndex = 0; waitIndex < maxDownloadLoops; waitIndex += 1) {
            await sleep(1000);
            downloadEvents.push(...browser.takeEvents("Browser.downloadWillBegin"));
            downloadEvents.push(...browser.takeEvents("Browser.downloadProgress"));
            const hasBegin = downloadEvents.some(event => event.method === "Browser.downloadWillBegin");
            const finished = downloadEvents.some(event => event.method === "Browser.downloadProgress" && ["completed", "canceled"].includes(event.params?.state));
            if (finished) break;
            if (!hasBegin && (waitIndex + 1) * 1000 >= args.downloadStartWaitMs) break;
          }
          result.download_event_summary = summarizeDownloadEvents(downloadEvents);
          if (result.download_event_summary.state === "inProgress") {
            result.status = "download_incomplete_timeout";
            result.note = `download still in progress after ${args.downloadWaitMs} ms; batch stopped to avoid file misassignment`;
            if (queueRow) {
              queueRow.status = result.status;
              queueRow.note = result.note;
            }
            stopBatch = true;
          } else {
            const changed = changedFiles(before, inputDir)
              .filter(file => !["cnki_link_audit.tsv", "download_queue.tsv", "README_download_status.md", "cnki_edge_probe_results.jsonl"].includes(file.name));
            result.changed_files = changed.map(file => ({ name: file.name, size: file.size }));
            const valid = [];
            for (const file of changed) {
              const sniff = sniffFile(file.full);
              valid.push({ ...file, sniff });
            }
            result.sniffed = valid.map(file => ({
              name: file.name,
              size: file.sniff.size,
              format: file.sniff.format,
              headHex: file.sniff.headHex,
              headText: file.sniff.headText,
            }));
            const doc = valid.find(file => file.sniff.format === "PDF" || file.sniff.format === "CAJ");
            if (doc) {
              const ext = doc.sniff.format === "PDF" ? ".pdf" : ".caj";
              const desired = `${String(row.index).padStart(3, "0")}-${safeName(queueRow?.safe_title || row.title, `cnki_${row.index}`)}${ext}`;
              const desiredPath = path.join(inputDir, desired);
              let savedName = desired;
              if (path.resolve(doc.full) !== path.resolve(desiredPath)) {
                if (fs.existsSync(desiredPath)) {
                  const stamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
                  savedName = `${String(row.index).padStart(3, "0")}-${safeName(queueRow?.safe_title || row.title, `cnki_${row.index}`)}_${stamp}${ext}`;
                }
                fs.renameSync(doc.full, path.join(inputDir, savedName));
              }
              queueRow.status = "downloaded";
              queueRow.format = doc.sniff.format;
              queueRow.saved_file = savedName;
              queueRow.note = `Edge 9222 DevTools; size=${doc.sniff.size}; source=detail_page_click`;
              result.status = "downloaded";
              result.saved_file = savedName;
              result.format = doc.sniff.format;
            } else {
              result.status = "download_failed_or_non_document";
            }
          }
        }
      }
    } catch (err) {
      result.status = "error";
      result.error = String(err && err.message ? err.message : err);
    } finally {
      results.push(result);
      fs.appendFileSync(probePath, `${JSON.stringify(result, null, 0)}\n`, "utf8");
      if (page) page.close();
      if (pageInfo && pageInfo.id) await closePage(base, pageInfo.id);
    }
    if (["downloaded", "download_incomplete_timeout"].includes(result.status)) {
      writeTsv(queuePath, queueRows, queueHeaders);
    }
    if (stopBatch) break;
    await sleep(args.interItemSleepMs);
  }
  browser.close();
  const summary = results.map(item => ({
    index: item.index,
    title: item.title,
    status: item.status,
    saved_file: item.saved_file || "",
    format: item.format || "",
    bytes: item.download_event_summary?.totalBytes || item.sniffed?.[0]?.size || 0,
    event_state: item.download_event_summary?.state || "",
    note: item.note || "",
    error: item.error || "",
  }));
  process.stdout.write(JSON.stringify({ browser: version.Browser, count: results.length, results: summary }, null, 2));
}

main().catch(err => {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
