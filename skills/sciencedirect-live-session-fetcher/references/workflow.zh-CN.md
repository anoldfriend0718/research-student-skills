# 中文流程说明

## 核心原则

这套 skill 复用用户已经合法登录、已经通过验证的真实 Chrome 或 Edge 浏览器会话。它不会创建新的访问权限，也不应被用于绕过订阅、验证码、机构认证或出版社访问控制。

优先把它理解为“浏览器会话内的串行 PDF 自动保存器”：如果当前浏览器能看到文章页，并且页面暴露了 PDF metadata、PDF 按钮、HTML viewer 或 PDF delivery endpoint，脚本才有机会下载。

## 适用范围

已验证或优先支持：

- ScienceDirect / Elsevier：稳定主路径。
- Wiley：已实测 `10.1002/ese3.506`，文章页可经 `/doi/pdf` 或 `/doi/epdf` 解析到 `/doi/pdfdirect/...`。
- IEEE Xplore：脚本包含专门逻辑，但需要用户先在同一浏览器窗口完成机构登录。
- Springer Nature、Taylor & Francis、ACS、MDPI 等：按“通用出版社 PDF 链接探测”处理，能否成功取决于页面是否暴露标准 PDF 入口。

不适用：

- 当前账号无权限的论文。
- 仍停留在验证码、登录页或机构认证失败页的会话。
- 页面完全不暴露 PDF endpoint 的出版社页面。

## CSV 准备

最少列：

```csv
number,doi,title,note
1,10.1002/ese3.506,Quantification of low-temperature oxidation of light oil and its SAR fractions with TG-DSC and TG-FTIR analysis,https://scijournals.onlinelibrary.wiley.com/doi/10.1002/ese3.506
```

经验规则：

- `doi` 尽量准确填写。
- `note` 优先放文章页 URL 或 DOI landing page。
- 不要优先放短时 PDF 直链，例如 ScienceDirect `pdfft?...md5=...`、Wiley `pdfdirect`、出版社临时 token 链接。
- 混合出版社批量时，`note` 列比只靠 DOI 自动跳转更可靠。

## Windows Edge 推荐流程

在 PowerShell 中先临时允许当前窗口执行脚本：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

启动独立 Edge 会话：

```powershell
$skill = "$HOME\.codex\skills\sciencedirect-live-session-fetcher"

& "$skill\scripts\launch_edge_clone_remote_debug.ps1" `
  -OneShotProfile `
  -DisableExtensions `
  -RemoteDebuggingPort 9222 `
  -Url "https://www.sciencedirect.com/"
```

然后在这个 Edge 窗口中手动完成：

1. 登录个人或机构账号。
2. 通过验证码或 bot verification。
3. 打开一篇代表性文章。
4. 必要时手动点一次 `View PDF` 或 `Download PDF`。
5. 保持这个 Edge 窗口打开。

## 单篇测试优先

每个新出版社或新网络环境先运行一篇：

```powershell
$skill = "$HOME\.codex\skills\sciencedirect-live-session-fetcher"

py "$skill\scripts\devtools_sciencedirect_serial_fetch.py" `
  --input-csv "C:\papers\input.csv" `
  --out-dir "C:\papers\output_test" `
  --debug-port 9222 `
  --page-wait-seconds 15 `
  --inter-item-sleep-seconds 6 `
  --limit 1
```

如果 `py` 在当前环境不可用，可改用明确的 Python 路径，例如：

```powershell
$python = (Get-Command python -ErrorAction Stop).Source
& $python "$skill\scripts\devtools_sciencedirect_serial_fetch.py" `
  --input-csv "C:\papers\input.csv" `
  --out-dir "C:\papers\output_test" `
  --debug-port 9222 `
  --page-wait-seconds 15 `
  --inter-item-sleep-seconds 6 `
  --limit 1
```

## 批量运行建议

ScienceDirect 或 Wiley 已验证后，可去掉 `--limit 1`：

```powershell
py "$skill\scripts\devtools_sciencedirect_serial_fetch.py" `
  --input-csv "C:\papers\input.csv" `
  --out-dir "C:\papers\output_all" `
  --debug-port 9222 `
  --page-wait-seconds 15 `
  --inter-item-sleep-seconds 6
```

混合出版社建议：

- `--page-wait-seconds 20` 到 `30`。
- `--inter-item-sleep-seconds 6` 到 `8`。
- 每个新出版社先测试 1–3 篇。

## 输出文件检查

每次运行后检查：

- `summary.txt`：总体成功和失败数量。
- `devtools_results.csv`：每条记录状态、PDF 路径、实际 source URL 和 note。
- `devtools_missing.csv`：失败记录。
- `pdfs/`：实际 PDF。

成功的基本验证标准：

- `status=downloaded`。
- PDF 文件存在且大小大于 0。
- 文件头为 `%PDF-`。

## 已验证经验

- ScienceDirect 页面可能保留 challenge 相关字符串；如果页面同时有 `View PDF` 和 PDF metadata，应先做单篇下载测试，不要直接判死为 challenge。
- Wiley 页面可能先显示 HTML viewer；脚本会继续解析 `/doi/pdfdirect/...`，但页面 PDF 按钮可能动态加载，因此 `page_wait_seconds` 不宜太短。
- 直接把短时 PDF 链接放到 CSV 中可能导致 DevTools target 消失或链接过期；优先放文章页 URL。
- 失败后优先重试 `devtools_missing.csv` 中的少量记录，不要立即整批重跑。