# 学生科研常用 Skills

将科研中反复使用的文档转换、文献下载、修订对比和任务交接流程整理为可复用的 Agent Skills。面向使用 Codex、Claude Code 或其他支持 `SKILL.md` 的工具的学生。

本仓库包含维护者的工作流与适配，也随包提供实际需要的第三方组件；第三方内容保留原署名和许可，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。`nature` 是现有技能名称的前缀，不表示与 Nature Portfolio 存在隶属关系，也不保证发表或下载权限。

## 技能清单

| 分组 | 技能 | 用途 |
|---|---|---|
| 科研常用 | [word-to-markdown-academic](skills/word-to-markdown-academic/SKILL.md) | 学术 Word 转 Markdown，处理公式、图表、编号和转换残留 |
| 科研常用 | [manuscript-revision-diff](skills/manuscript-revision-diff/SKILL.md) | 对比两个 Markdown 稿件的英文内容，生成逐词 HTML 对照 |
| 文献下载 | [nature-downloader](skills/nature-downloader/SKILL.md) | 按出版商 API、OA 与用户机构授权选择全文获取路线 |
| 文献下载 | [cnki-live-session-pdf-downloader](skills/cnki-live-session-pdf-downloader/SKILL.md) | 在已授权 Chrome/Edge 会话中处理知网 PDF/CAJ 下载队列 |
| 文献下载 | [sciencedirect-live-session-fetcher](skills/sciencedirect-live-session-fetcher/SKILL.md) | 在活跃浏览器会话中串行下载 ScienceDirect、IEEE 等文献 |
| 进阶工具 | [codex-handoff](skills/codex-handoff/SKILL.md) | 保存当前目标、文件状态和已验证结果，支持后续继续任务 |
| 知识消纳 | [researchwiki-steward](skills/researchwiki-steward/SKILL.md) | 将材料转为有来源的证据卡、知识连接、项目综述与写作证据 |
| 进阶工具 | [chrome-form-filling](skills/chrome-form-filling/SKILL.md) | 根据有来源的资料填网页表单，并暂存、刷新核验 |
| 第三方配套 | [web-access](skills/web-access/UPSTREAM.md) | 为机构全文下载提供本地浏览器 CDP 组件，保留上游来源 |

首版不收录本机安装的所有技能，也不包含浏览器用户目录、登录会话、个人论文、API key 或历史申报明细。`literature-fulltext-fetcher` 统一路由器暂不收录：它还依赖未随本包发布的文献检索和全文阅读技能；当前直接调用上表中的专用入口。

## 安装

先安装 Git、Python 3.11+。文献下载还需要 Node.js 22+。浏览器路线使用学生自己的合法访问权限。

```text
git clone https://github.com/anoldfriend0718/research-student-skills.git
cd research-student-skills
python install.py --agent codex --dry-run
python install.py --agent codex
```

默认复制到 `~/.agents/skills/`，Claude Code 使用 `python install.py --agent claude`，复制到 `~/.claude/skills/`。也可显式指定 `--destination PATH`，例如已有环境使用的 `~/.codex/skills/`。不要同时把同名技能安装到多个发现目录，以免重复。

安装前会检查所有目标目录；已有同名技能时整批停止，保留原文件，不会静默覆盖。升级前请自行备份已有技能，再选择新的安装位置。可只装部分技能：

```text
python install.py --agent codex --only word-to-markdown-academic manuscript-revision-diff
python install.py --agent codex --only nature-downloader
```

安装 `nature-downloader` 会自动携带 `web-access`。其他第三方软件通过其官方包安装，不把整个软件或环境目录复制进本仓库。

建议在独立 Python 环境安装实际需要的运行库：

```text
python -m venv .venv
```

激活环境后按需安装：

```text
python -m pip install -r requirements.txt
python -m pip install -r skills/sciencedirect-live-session-fetcher/scripts/requirements.txt
python check_environment.py
```

`requirements.txt` 提供 Markdown、图像和全文核验常用依赖。Pandoc 可由其中的 `pypandoc_binary` 提供；如 `pandoc` 不在 PATH，技能内的 `scripts/pandoc_cli.py` 可作为 Python 启动器。LibreOffice 是旧 WMF/EMF 图像转换的可选系统依赖；扫描文档仍需要另外配置 OCR。

安装完成后重新载入 Agent 的技能列表。技能可按请求自动选择，也可显式使用 `$技能名`。

## 示例请求

```text
用 $word-to-markdown-academic 把这份学生论文转换为 Markdown，保留公式编号和图表，不改原 Word。

用 $manuscript-revision-diff 比较 student.md 与 revised.md，生成英文逐词对照页面。

用 $nature-downloader 下载以下 DOI 的正文，不需要补充材料；保存在本次任务的新目录。

用 $cnki-live-session-pdf-downloader 处理这个目录中的知网队列，先下载一篇并核验。

用 $sciencedirect-live-session-fetcher 根据 input.csv 下载文献，使用我已授权的浏览器会话，先测试一篇。

用 $codex-handoff 把当前任务整理为交接文件，记录已完成内容、文件位置、验证结果和下一步。

用 $researchwiki-steward 将这篇论文消纳到我指定的 Obsidian 知识库，先检查已有笔记，再更新证据、知识连接和项目综述。

用 $chrome-form-filling 根据这些材料填写当前网页，只暂存，不正式提交；完成后刷新核对。
```

## 配套关系与使用边界

- Word 转换：Pandoc 为主要结构转换工具；MarkItDown 是可选文本对照工具；图像处理使用 Pillow。未捆绑缺少明确再分发许可的 Word2Latex-Agent 项目，发布版使用自带 Pandoc 启动器。
- 英文稿件对照：Python 标准库；包含公式时需要 Pandoc。可通过 `--pandoc-command-json` 指定 Python 启动器的参数数组。
- 综合文献下载：Node.js、Python 常用库；OA/API 路线不依赖浏览器组件，机构浏览器路线使用随包的 Web Access。出版商 API key 不等同于全文权限。
- 知网队列：Node.js 22+、现有 Chrome/Edge DevTools 会话；可选 pypdf 做文本核验。队列格式与脚本参数见该技能参考文件。
- 活跃会话下载：Selenium / websocket-client；Windows、macOS 启动脚本分别提供，Firefox 路线按文献情况选择。
- 网页填报：需要当前 Agent 可用的浏览器控制工具；BrowserAct 仅是可选实现，不是已捆绑的软件。北理工参考文件只保留技术案例边界，不包含个人业绩，也不替代学校现行规则。
- 任务交接：写本地交接文件可独立使用；跨聊天操作还需要 Codex 应用实际提供对应工具，其他 Agent 不保证支持。
- 知识库消纳：`researchwiki-steward` 是个人 `xuqh-researchwiki-steward` 的通用版，随包提供基本卡片模板，不依赖作者私有 vault 的注册表或内部脚本。Word 材料自动配套 Word 转 Markdown；全文阅读和独立审查工具按使用者实际环境选择，未完成的审查须明确标注。

登录、验证码和机构授权由使用者在自己的浏览器完成。输出文件以实际文件头、来源及保存后回查结果为准。网页结构、出版商权限和浏览器版本变化可能影响下载路线。

## 验证

```text
python tests/test_package.py
node --test skills/nature-downloader/tests/unit/*.test.mjs
python -m unittest discover -s skills/nature-downloader/tests/python
python -m unittest discover -s skills/manuscript-revision-diff/scripts -p test_english_diff.py
```

离线检查不代表每所学校或所有出版商的在线路线均已验证。随包源码、原始许可和第三方组件版本可分别在各技能目录与 [DEPENDENCIES.json](DEPENDENCIES.json) 中查阅。
