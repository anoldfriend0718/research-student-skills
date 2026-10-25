# 来源、署名与配套软件

本仓库由 anoldfriend0718 整理发布。打包、环境适配和新增辅助文件不改变上游内容的原始归属。

## 随包的上游组件

| 组件 | 来源依据 | 许可与处理 |
|---|---|---|
| nature-downloader | 本地版本随附 `LICENSE`，版权所有者为 `baihe26` | 原 MIT License 原样保留在 `skills/nature-downloader/LICENSE`；本仓库不将其全部源码声明为原创 |
| web-access | [eze-is/web-access](https://github.com/eze-is/web-access)，作者元数据为一泽Eze | 上游 `SKILL.md` 标注 MIT；该快照无独立 LICENSE。保留原作者和许可元数据，固定提交见该目录 `UPSTREAM.md`，不改运行脚本 |

Web Access 的发布适配仅限：收窄自动选择范围以服务文献工作流、统一技能目录占位符、去掉“继续即接受”措辞。下载器适配技能目录名为 `web-access`。

## 单独安装的第三方软件

以下软件不以完整源码、二进制或虚拟环境随包复制，使用者按各项目许可安装和使用：

- [Pandoc](https://pandoc.org/)，以及 Python 的 pypandoc / pypandoc_binary 启动和分发包。
- [MarkItDown](https://github.com/microsoft/markitdown)。
- [Pillow](https://python-pillow.org/)、pypdf、pdfplumber、PyYAML、jsonschema。
- [Selenium](https://www.selenium.dev/)、websocket-client。
- [LibreOffice](https://www.libreoffice.org/)（旧图像转换可选）。
- [BrowserAct](https://github.com/browser-act/skills)（网页表单的一种可选浏览器工具，未随包复制）。

未收录通用 `convert-documents-to-markdown` 技能（上游署名 Firecrawl）：当前入选技能没有必须通过它完成的调用。未复制 Word2Latex-Agent 项目：本地项目缺少独立许可文件，发布版以自己的轻量 Pandoc 启动器提供转换入口。

除上述明确保留上游声明的内容外，用户选择发布的工作流及本次新增打包辅助文件适用根目录 LICENSE。历史备份、浏览器会话、个人数据和过程材料不属于发布内容。
