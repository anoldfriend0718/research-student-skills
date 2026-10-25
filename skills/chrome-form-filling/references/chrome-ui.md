# Chrome 与表单控件经验

## 连接：已验证事实与时效边界

本次成功路径是 BrowserAct 的 `chrome-direct`，直接使用已运行 Chrome 的认证环境。CLI 曾不在 PATH，实际位于 `%USERPROFILE%/.local/bin/browser-act.exe`。先检测再使用；不要因 PATH 缺项就重装。

在本案例中，直接地址 `https://ehall.bit.edu.cn/` 可访问填报平台；旧 WebVPN 地址反复进入认证流程。这不是“永远禁用 WebVPN”的规则：按用户实际网络和已打开标签选择入口。不要保存带 `sign=` 的完整任务链接作为长期入口。

CLI core 记录了 `browser open`、`state`、`eval --stdin`、`click --selector`、`reload`、`session close` 等命令。启动新任务时以当前文档为准，不靠本参考替代工具文档。接入原有标签的能力也须从当前工具文档发现。

曾遇到旧会话健康检查失败：确认属于本任务、无未保存变更后，关闭自己的失效会话再创建新会话解决。此动作不是常规步骤，不要关闭用户原有标签、重启整套 Chrome 或结束其他任务会话。工具清理要求与用户保留标签的要求冲突时遵循当前用户明确要求；清理前先保证保存与核验完成。

本地 Chrome 操作曾在未配置 BrowserAct API key 时正常工作；`remote-assist` 则返回需要 API key。不能因为远程协助缺少 key 就推断整个 Chrome 连接不可用，也不能声称已经生成协助链接。需要用户认证时如实说明工具限制，让用户在现有页面处理，不擅自注册服务。

## Windows 调用与编码

PowerShell 管道中的中文 JavaScript 曾触发编码错误。可用 Python 将 JS 转为 ASCII（Unicode 转义）再通过 UTF-8 stdin 传给 CLI：

```python
import json
import subprocess

# cli 与 session 来自本次发现的运行环境，不写死历史会话。
js = "JSON.stringify(document.title)"
proc = subprocess.run(
    [cli, "--session", session, "eval", "--stdin"],
    input=js.encode("ascii", "backslashreplace").decode("ascii"),
    capture_output=True, encoding="utf-8", timeout=60,
)
if proc.returncode:
    raise RuntimeError(proc.stdout + proc.stderr)
result = json.loads(proc.stdout)
```

传递数据时用 `json.dumps(payload, ensure_ascii=True)`；不用 shell 字符串插值拼接论文文本。CLI 输出形态若改变，先检查当前结果再适配解析器。

## 主表、分页与重复 DOM

北理工页面使用 Element UI 风格的表格。`.el-table__body-wrapper` 主体与 `.el-table__fixed-body-wrapper` 固定列副本会产生重复输入。全局 `[data-id=字段] input` 曾命中多项；限定到主表后唯一。

先按栏目表头找目标 `.el-table`，检查其主表和关联分页器。以下仅为曾观测结构，不保证今后不变：

- 论文主表行曾有 11 个 input：题名、期刊、FWCI、期号、起始页、终止页、作者、日期、收录情况、期刊类型、隐藏排序数值。
- 页面曾有多个 `.el-pagination`，论文分页器当时排第 7；**不要把 `[6]` 永久复用**。
- `el-table_32_column_268` 等类名会随重绘变化，不持久化。
- 日期字段的语义属性曾为 `[data-id=fbsj]`。
- 统计字段曾为 `fblwzs`（总数）、`djqk`（顶级）、`zyqk`（重要）、`zwhxqk`（中文核心）。使用前重新核对表头和命中数量。

第一次读取当前表时检查列数、字段属性、隐藏列和总记录数。翻页等待主表记录稳定后再读，不在前一进程尚未完成时发起下一次页面操作。只有当前快照确认结构后，才可在本批操作中临时使用行位置。

## 普通输入与数字框

已观测可用的 DOM 输入模式（仅适用于已识别且允许编辑的普通字段）：

```javascript
el.focus();
Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, newValue);
el.dispatchEvent(new Event('input', { bubbles: true }));
el.dispatchEvent(new Event('change', { bubbles: true }));
el.blur();
```

Element UI 数字统计框也曾接受上述模式，但不能由这一经验推断所有数字框支持文字。“FWCI”在本次表单实际是 text input，用户要求的“暂无”已成功保存；新表单若有数值约束，应报告实际校验结果，不能移除限制伪造成功。

## 日期控件：最容易产生假成功

本次出现了三种不同结果：

1. 给只读日期 input 设置 value 并派发 input/change，立即读取看似正确，翻页后恢复。
2. 点击日历中的日期后弹层仍在，模型值没有改变。
3. 真实点击日期框，再以方向键选择并 Enter 确认，翻页与保存重载后保持正确。

因此先试工具正常 UI 操作并做一次小范围持久性验证；只有前两种现象发生时再用已验证的键盘方式。不要反复用同一种失效方式填满整表。

键盘步骤：

1. 按唯一记录定位日期 input；使用工具的真实 `click --selector` 打开。只运行 `el.click()` 在本例有时没有打开弹层。
2. 检查当前日期、唯一可见日历及焦点。
3. ArrowRight/Left 移动一天，ArrowDown/Up 移动一周。每步读取实际日期，不假定每次事件一定移动预定距离。Enter 确认。
4. 日期相差较远时优先尝试日历年月选择；若采用方向键，分批有限步数执行，使用 UTC 日期计算差值，避免时区/DST 导致错误天数。
5. 若不移动或弹层意外关闭，立即结束该批。重新读取当前日期，再开控件从剩余差值继续；不是重放整个旧步骤。
6. 翻到另一页再返回、保存并刷新，检查日期真的保留。

在该站点中验证过的键盘事件示例，可作为工具正常 `keys` 操作的站点专用替代；仍须以当前页面结果确认：

```javascript
el.dispatchEvent(new KeyboardEvent('keydown', {
  key: 'ArrowLeft', code: 'ArrowLeft', keyCode: 37, which: 37, bubbles: true
}));
// 等待 DOM 更新，读回 el.value，再决定下一步。
```

禁止为了改日期访问 Vue 私有对象或直接改后台模型；也不要移除 readonly/disabled 以冒充真实控件提交。

## 下拉选项

本次论文行的两个 `.el-select` 分别为收录情况与期刊类型。先读该行字段对应关系再操作。

点击目标框后等待可见的 `.el-select-dropdown`。它可能挂载到 body，不能只在行内找。过滤隐藏弹层，断言恰好一个，再按完整选项文字选择；等待弹层关闭并回读字段。过渡动画中可能短暂出现 0 或 2 个可见弹层，先等待稳定，不立即再次点击导致反向关闭。

当时收录选项：ESI高被引、SCIE、SSCI、CSSCI、EI、Scopus、其他；期刊类型：顶级、重要、其他。不要把这个枚举当成所有未来表单的固定规则。

## 排序与删除

自定义排序入口曾是行内 `i.el-icon-edit-outline` 的父按钮；弹层包含当前全局位置与 `input[role=spinbutton]`、确认按钮。按题名定位原记录，验证显示的当前位置，填写目标位置并确认，再检查整条记录的所有值与新位置。表格分页重排后重新定位，不复用旧行号。

删除只针对用户指定记录。确认弹层文字与目标对应；随机 popover ID 曾与隐藏元素碰撞，用唯一可见弹层定位。点击删除后回读数量和记录集合，再暂存。

## 暂存证明链

`当前页正确 → 翻页回读正确 → 暂存成功提示 → reload → 所有受影响分页正确`。

出现差异时保留前后快照。不能仅凭“操作成功”断言全部字段正确，不能把“能在框里看到”当作已保存。修改失败后不要继续执行预定保存动作；明确错误是否发生在写入前、部分写入后或保存后，避免覆盖正确数据。
