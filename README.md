# 学生科研常用 Skills

把论文写作、文献下载与知识消纳、文档转换、修订对比、网页填报和任务交接中反复使用的流程整理为可复用的 Agent Skills。面向使用 Codex、Claude Code 或其他支持 `SKILL.md` 工具的学生，从当前任务选择所需技能即可。

当前仓库版本为 **v0.2.0**，包含 **9 个主要技能和 1 个第三方配套组件，共 10 个目录**。各技能的版本与适用范围分别维护；工程论文写作目前为 v0.1.0 学生试用版。

本仓库包含维护者的工作流与适配，也随包提供实际需要的第三方组件；第三方内容保留原署名和许可，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。`nature` 是现有技能名称的前缀，不表示与 Nature Portfolio 存在隶属关系，也不保证发表或下载权限。

## 技能清单

| 任务 | 技能入口 | 可以获得什么 |
|---|---|---|
| 论文写作与修订 | [xuqh-engineering-paper-writing](skills/xuqh-engineering-paper-writing/SKILL.md) | 根据现有证据组织贡献、主线和各节；新手分步学习，熟手按指定范围评审与润色 |
| 学术 Word 转换 | [word-to-markdown-academic](skills/word-to-markdown-academic/SKILL.md) | 保留原稿，生成含公式、图表、编号的 Markdown 工作副本并检查转换问题 |
| 英文修订对照 | [manuscript-revision-diff](skills/manuscript-revision-diff/SKILL.md) | 比较两份 Markdown 的英文内容，生成逐词 HTML 对照 |
| 全文获取路线选择 | [nature-downloader](skills/nature-downloader/SKILL.md) | 按出版商 API、OA 与用户机构授权选择全文获取路线 |
| 知网批量下载 | [cnki-live-session-pdf-downloader](skills/cnki-live-session-pdf-downloader/SKILL.md) | 在已授权 Chrome/Edge 会话中处理 PDF/CAJ 下载队列并核验文件 |
| 出版商会话下载 | [sciencedirect-live-session-fetcher](skills/sciencedirect-live-session-fetcher/SKILL.md) | 使用活跃浏览器会话串行下载 ScienceDirect、IEEE 等文献并记录失败项 |
| 知识库消纳 | [researchwiki-steward](skills/researchwiki-steward/SKILL.md) | 将材料整理为有来源的证据卡、知识连接、项目综述与写作证据 |
| 网页资料填报 | [chrome-form-filling](skills/chrome-form-filling/SKILL.md) | 根据有来源的材料填写表单，暂存后刷新核对 |
| 任务交接 | [codex-handoff](skills/codex-handoff/SKILL.md) | 保存当前目标、文件状态、已验证结果和后续任务，便于继续工作 |
| 第三方配套 | [web-access](skills/web-access/UPSTREAM.md) | 为机构全文下载提供本地浏览器 CDP 组件，保留上游来源与版本 |

本仓库不收录本机安装的所有技能，也不包含浏览器用户目录、登录会话、个人论文、API key 或历史申报明细。`literature-fulltext-fetcher` 统一路由器依赖未随包发布的检索和全文阅读技能，暂不收录；请直接选择上表中的下载入口。

## 选择与安装

先安装 Git、Python 3.11+。需要浏览器文献下载路线时，再按技能说明准备 Node.js 22+、浏览器及自己的合法访问权限。

```text
git clone https://github.com/anoldfriend0718/research-student-skills.git
cd research-student-skills
```

建议先安装当前任务需要的技能。以下为几种选择，每条都可单独执行；正式安装前加 `--dry-run` 查看计划：

```text
python install.py --agent codex --only xuqh-engineering-paper-writing --dry-run
python install.py --agent codex --only xuqh-engineering-paper-writing
python install.py --agent codex --only word-to-markdown-academic manuscript-revision-diff
python install.py --agent codex --only nature-downloader
python install.py --agent codex --only researchwiki-steward
```

其他技能同样使用 `--only 技能名` 选择；需要全部安装时，执行 `python install.py --agent codex --dry-run`，确认后去掉 `--dry-run`。安装 `nature-downloader` 自动携带 `web-access`；安装 `researchwiki-steward` 自动携带 `word-to-markdown-academic`。

Codex 默认复制到 `~/.agents/skills/`。Claude Code 使用 `--agent claude`，复制到 `~/.claude/skills/`。也可用 `--destination PATH` 指定已有环境的技能目录，例如 `~/.codex/skills/`。不要把同名技能同时装入多个发现目录，以免重复。

安装器会先检查整批目标，已有任一同名目录时停止，保留原文件。连续执行上面的示例时，自动配套的技能也可能触发这一检查。升级前先备份已有安装，再选择新的安装位置；不会静默覆盖。

技能源文件安装与运行依赖准备是两步。建议使用独立 Python 环境，按实际任务安装运行库：

```text
python -m venv .venv
```

激活环境后，文档处理与全文核验的常用依赖可安装 `requirements.txt`；活跃会话下载另有自己的依赖清单：

```text
python -m pip install -r requirements.txt
python -m pip install -r skills/sciencedirect-live-session-fetcher/scripts/requirements.txt
python check_environment.py
```

纯文本写作建议和本地交接文件通常无需上述文档处理依赖。Pandoc 可由 `pypandoc_binary` 提供；如不在 PATH，可使用技能内的 `scripts/pandoc_cli.py`。旧 WMF/EMF 图像转换可选用 LibreOffice；扫描文档还需另配 OCR。其他第三方软件通过官方渠道安装，不复制整个软件或环境目录。

安装完成后重新载入 Agent 的技能列表。可以按任务自然描述，也可显式使用 `$技能名`。

## 调用示例

提供当前材料、希望获得的产物和允许修改的范围。先完成一个小任务并核对输出，再扩大到整篇论文、批量下载或完整表单。

| 当前任务 | 可直接使用的请求 |
|---|---|
| 新手组织论文 | 用 `$xuqh-engineering-paper-writing` 带我分析现有图表，先判断各图回答什么问题，给候选主线和最少核对任务，不编造创新结论。 |
| 熟手局部修订 | 用 `$xuqh-engineering-paper-writing` 只检查这一段的科学逻辑和英文表达，保留数字与比较口径，先给意见和候选改法，不写入文件。 |
| 准备 Word 工作稿 | 用 `$word-to-markdown-academic` 把这份论文转为 Markdown，保留公式编号和图表，不改原 Word，列出未核实的转换部分。 |
| 查看英文改动 | 用 `$manuscript-revision-diff` 比较 student.md 与 revised.md，生成英文逐词对照页面。 |
| 按 DOI 获取正文 | 用 `$nature-downloader` 下载以下 DOI 的正文，不需要补充材料；保存到本次任务的新目录。 |
| 处理知网队列 | 用 `$cnki-live-session-pdf-downloader` 处理这个目录中的队列，使用我已授权的会话，先下载一篇并核验。 |
| 处理出版商队列 | 用 `$sciencedirect-live-session-fetcher` 根据 input.csv 下载文献，使用我已授权的浏览器会话，先测试一篇并检查结果记录。 |
| 消纳阅读材料 | 用 `$researchwiki-steward` 将这篇论文消纳到我指定的知识库，先检查已有笔记，再整理有来源的证据、术语、知识连接和项目综述。 |
| 填写网页资料 | 用 `$chrome-form-filling` 根据这些材料填写当前网页，只暂存；完成后刷新核对。 |
| 保存任务进度 | 用 `$codex-handoff` 整理本地交接文件，记录已完成内容、文件位置、验证结果和下一步。 |

`web-access` 随机构下载路线使用，通常无需单独调用。写作任务需要文献、复杂 Word 或知识库时，可选用对应配套技能；局部文字修订无需完整重跑流程。写作的更多入口见[学生使用说明](skills/xuqh-engineering-paper-writing/README.md)。

## 依赖与能力边界

| 技能或组件 | 使用条件与边界 |
|---|---|
| 工程论文写作 | v0.1.0 学生试用版。普通文本意见可独立执行；复杂文档、全文与知识库操作依赖当前环境。审稿回复为案例较少的初步模块，优先核查回复与当前实稿的一致性。贡献和结论必须由当次证据支持。 |
| Word 转 Markdown | Pandoc 为主要结构转换工具，Pillow 处理图像，MarkItDown 可选用于文本对照。Markdown 保存引文显示文本及来源对应，不承诺保留可操作的 EndNote 域；复杂公式、对象和版式须核对。未捆绑 Word2Latex-Agent。 |
| 英文修订对照 | 基本对照使用 Python 标准库；包含公式时需要 Pandoc，可用 `--pandoc-command-json` 指定 Python 启动器参数数组。对照展示文字差异，不判断修改的科学正确性。 |
| 全文路线选择 | 按路线准备 Node.js、Python 依赖；OA/API 路线不依赖浏览器组件，机构浏览器路线使用随包 Web Access。出版商 API key 不等同于全文权限。 |
| 知网队列下载 | Node.js 22+、现有 Chrome/Edge DevTools 会话；可选 pypdf 核验文本。队列格式和参数见技能参考文件。 |
| 活跃会话下载 | 使用 Selenium / websocket-client，提供 Windows、macOS 启动脚本；按文献和页面选择 DevTools 或 Firefox 路线。支持范围取决于授权页面是否暴露可用 PDF 目标。 |
| 知识库消纳 | `researchwiki-steward` 是个人 `xuqh-researchwiki-steward` 的通用版，随包提供基本卡片模板，不依赖教师私有 vault 的注册表或内部脚本。全文阅读和独立审查能力按实际环境选择，未完成的审查须标明。 |
| 网页填报 | 需要当前 Agent 可用的浏览器控制工具；BrowserAct 是可选实现，未随包提供。北理工参考文件仅保留技术案例，不含个人业绩，也不替代学校现行规则。 |
| 任务交接 | 写本地交接文件可独立使用；跨聊天操作需要 Codex 应用实际提供对应工具，其他 Agent 不保证支持。 |
| Web Access | 为下载提供浏览器连接能力，不提供机构授权；上游版本及打包适配见[来源说明](skills/web-access/UPSTREAM.md)。 |

登录、验证码和机构授权由使用者在自己的浏览器完成。输出以实际文件头、来源及保存后回查结果为准。网页结构、出版商权限和浏览器版本变化可能影响路线。

写作方法与示例来自作者手册、可访问修改任务和公开论文选定页段；分享包仅含可迁移方法、公开来源与匿名教学示例。术语表中 39 条有公开来源，8 条为匿名教学构造，均不能替代当前稿件的术语定义和证据。私有稿件、调查记录和教师知识库不随包提供。

## 检查与验证

仓库提供以下离线检查，可在本机依赖就绪后运行：

```text
python tests/test_package.py
node --test skills/nature-downloader/tests/unit/*.test.mjs
python -m unittest discover -s skills/nature-downloader/tests/python
python -m unittest discover -s skills/manuscript-revision-diff/scripts -p test_english_diff.py
```

发布检查与任务效果应分别理解：

| 检查范围 | 已检查内容与适用限制 |
|---|---|
| 仓库打包与安装 | 6 项包检查通过，覆盖目录与链接、敏感路径模式、Python 语法、安装依赖与不覆盖行为、填报快照比较、第三方来源记录。它们不等于学生电脑兼容性或在线业务路线验证。 |
| 写作内容与文本试跑 | 已进行独立内容审核、结构与链接检查；3 个文本场景有限试跑，分别涉及熟手指定两句合并、回复与给定正文一致、新手依据三图组织候选主线。不能据此推定整篇写作或完整返修流程均已验证。 |
| Word 转换试跑 | 实际任务中检查了原 DOCX 保护、媒体与链接、表格及部分公式/符号；复杂对象语义、活动引文域迁移和逐页视觉尚未全面验证。 |
| 下载、填报与知识库任务 | 离线检查不能证明每所学校、每个出版商或当前页面均可用；每次仍需核对权限、代表性输入、保存后的文件或页面，以及实际引用的来源。 |

这些检查不构成对实验、模拟、数据或论文结论的独立验证。随包源码、原始许可和第三方组件版本可在各技能目录与 [DEPENDENCIES.json](DEPENDENCIES.json) 中查阅。
