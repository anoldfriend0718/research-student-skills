# CNKI Live-Session PDF 下载流程

## 适用前提

- 用户已经通过 Chrome 或 Edge 完成 CNKI 或机构授权，例如高校图书馆、VPN、代理或统一身份认证。
- 浏览器以远程调试端口运行，常用端口为 `9222`。
- 任务目标是批量下载 CNKI 论文 PDF/CAJ，并更新本地 `download_queue.tsv`。
- 不能绕过登录、验证码、付费墙或机构权限限制。遇到这些页面时，停止并让用户人工处理。

## 输入文件

默认目录应包含：

- `download_queue.tsv`：下载队列和状态表。
- `cnki_link_audit.tsv`：CNKI 详情页和下载链接审计表。

推荐字段：

- 队列表：`index`, `title`, `status`, `format`, `saved_file`, `note`, `safe_title`。
- 审计表：`index`, `title`, `final_url`, `pdf_url`, `caj_url`。

实际下载应优先打开 `final_url` 对应的 CNKI 详情页，然后点击页面上的 `PDF下载` 或 `CAJ下载`。不要把 `pdf_url` 当作稳定直接下载地址；CNKI 常会因为缺少详情页上下文而返回 `来源应用不正确` 或登录错误页。

## 浏览器准备

1. 启动或确认 Edge/Chrome 已开放 DevTools 端口，例如 `127.0.0.1:9222`。
2. 在该浏览器中打开 CNKI，完成机构登录、验证码、授权确认等人工步骤。
3. 打开一篇代表性 CNKI 详情页，确认页面能看到 `PDF下载` 或 `CAJ下载`。
4. 保持浏览器窗口打开，下载期间不要关闭或切换登录状态。

## 标准详情页判据

本 workflow 只把接近 CNKI 标准单篇详情页的页面作为下载入口。页面应同时满足以下特征：

- 顶部为中国知网/CNKI 导航，常见域名为 `www.cnki.net`，详情页 URL 通常包含 `kns.cnki.net/kcms2`。
- 页面主体是单篇文献，而不是期刊主页、出版来源页、专题页、二维码阅读页或第三方聚合页。
- 页面可见题名、作者、单位、摘要、专辑/专题/分类号等题录信息。
- 页面底部或明显操作区可见 `HTML阅读`、`原版阅读`、`CAJ下载`、`PDF下载` 等按钮。

如果打开的页面与上述特征不符，应把该条记录标为 `wrong_entry_page` 或 `needs_standard_detail_page`，记录当前 URL 和原因，然后回到检索结果或题录页重新进入标准详情页。不要在错误入口上反复尝试下载，也不要把直接 `bar.cnki.net` 链接、CBPT 期刊门户或二维码阅读页当作主下载页面。

可用以下命令检查端口：

```powershell
Invoke-RestMethod http://127.0.0.1:9222/json/version
```

返回中应包含 `Browser` 和 `webSocketDebuggerUrl`。

## 单条探测

每个新会话、换机构、换网络或新批次，都先运行一条：

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

成功标准：

- 输出状态为 `downloaded`。
- `download_event_summary.state` 为 `completed`。
- 队列表对应行的 `status=downloaded`。
- `saved_file` 对应文件存在。
- 文件头为 `%PDF-`、`CAJ` 或 `KDH`，不是 HTML。

## 批量下载

单条通过后，再按小批量推进：

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

建议：

- `--limit` 从 5 到 10 开始，稳定后再增大。
- `--inter-item-sleep-ms` 保持 6000-8000 ms。
- 大论文或学位论文可能下载较慢，`--download-wait-ms` 可设为 180000-300000 ms。
- 若某条出现 `download_incomplete_timeout`，脚本会停止本批；不要继续批量，先审计目录和队列表。

## 验证

基础验证：

```powershell
python scripts/validate_cnki_downloads.py --input-dir C:\path\to\cnki_downloads
```

若安装了 `pypdf`，可做题名文本抽取审计：

```powershell
python scripts/validate_cnki_downloads.py --input-dir C:\path\to\cnki_downloads --text-check
```

注意：CNKI PDF 有时使用特殊字体编码，文本抽取可能乱码。若文件头合格且下载事件中的 `suggestedFilename` 与题名一致，可作为补充证据；不要仅因 `pypdf` 文本乱码就判定文件错误。

## 缺失 URL

如果队列表某条没有 CNKI URL，或 `cnki_link_audit.tsv` 没有该条 `final_url`，不要伪造下载成功。将其标记为 `missing_url` 或保留人工补查备注。
