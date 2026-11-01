# 新CentOS首次部署

用于新目标服务器，不代表操作系统一定是刚发行的版本。仅检查技能时不连接或部署设备；用户要求实际setup后，优先从现有记录取得SSH入口，缺少时才询问主机/别名、用户名和可用认证方式。密码由用户在终端输入，不发到聊天。

默认目标是SSH中可用的Codex CLI。只有用户要求断开本机仍可用时配置并验证独立出口/后台；只有明确要求Dot设备接入时才处理桌面。无需先安装Node、Podman、图形桌面或Mihomo。

## 不依赖Python的首次检查

先核验SSH主机身份。以下只读命令在目标服务器执行，兼容没有Python的最小安装；某条缺失时保留错误并继续采集其余项，不把缺失当作安装授权。

```sh
cat /etc/os-release
uname -m
uname -r
getconf GNU_LIBC_VERSION
id -u
date -u
test -w "$HOME" && printf 'HOME_WRITABLE\n'
df -Pk "$HOME"
for tool in codex python3 curl wget tar sha256sum rpm yum dnf bwrap unshare tmux systemctl getenforce; do
  command -v "$tool" || true
done
if command -v getenforce >/dev/null 2>&1; then getenforce; fi
if command -v python3 >/dev/null 2>&1; then python3 --version; fi
```

Python满足3.6+才运行[结构化探测脚本](../scripts/probe_linux.py)。它不会检查网络、认证或隔离启动。没有Python仍可完成CLI安装和验收；安装器要求以当前官方说明与下载脚本为准。

分清CentOS Linux、CentOS Stream及实际主版本，不根据“CentOS”三个字选择包。记录内核、glibc、CPU架构、可写目录、可用空间和当前权限。安装CLI通常可走用户级目录；系统依赖、SELinux策略或linger可能另需管理员。用户无sudo时先完成可执行的用户级准备，只为确实需要的管理员步骤安排认证。

## 安装路径选择

1. 先检查既有Codex与配置，避免覆盖另一套入口。使用[当前官方CLI安装文档](https://learn.chatgpt.com/docs/cli)选择Linux独立安装器或官方发行包；安装器先下载到私有工作目录、检查目标位置和所需环境，再在普通用户下执行。独立安装器路径可免去为npm额外安装Node的需要。
2. 服务器不能下载时，可在获准联网的机器下载官方包并经SSH传入，目标端再次校验可信摘要。安装包可以中转；登录凭据不随包迁移。包传输成功也不证明服务器能进行模型请求。
3. 旧glibc报错先确认出错程序及动态加载需求。当前官方发布确有对应架构的musl包时可评估该包；不保证未来每版都有，也不根据案例主机成功就承诺所有CentOS可用。musl不能补齐缺少的内核调用、命名空间或安全权限。
4. 新容器用户空间也共享宿主内核；不能把“放进Ubuntu容器”当成旧内核通用修复。若官方包和普通隔离在现有内核下无受支持的可行路径，记录准确限制，提出迁移到合适主机/系统的方案，不自行升级科研主机内核、glibc或整个系统。
5. 检查实际版本对应的bwrap依赖及PATH。[官方Linux隔离说明](https://learn.chatgpt.com/docs/sandboxing)要求准备bubblewrap；具体由该主机可信软件仓库和版本决定，不直接将Fedora/Ubuntu命令套给CentOS。仓库不可用或缺包时，查可信替代来源及兼容性，不全局换源、关闭签名或照搬案例主机的SELinux/seccomp规则。

## 登录和网络

沿用[CLI与网络流程](cli-network.md)。先复用实际可用的服务器出口，不默认部署代理；确需独立代理时保留loopback监听与私有凭据，测试客户端关闭不再影响服务器的链路。

[官方无头登录说明](https://learn.chatgpt.com/docs/auth?surface=cli)优先使用设备码方式；先检查当前`codex login --help`是否支持`--device-auth`，账号或工作区是否允许。不能使用时可选受控的localhost回调转发，端口以当前登录流程为准。用户完成官方认证；不为登录而默认安装浏览器/桌面，不将账号缓存打包复制。

## 分层验收

| 项目 | 必须取得的证据 |
|---|---|
| 安装 | 实际绝对路径、版本、包来源/校验；新SSH会话能解析入口 |
| 认证 | 当前版本的登录状态成功，凭据不出现在交付日志中 |
| 模型 | 私有空测试目录中完成一次真实短回复并记录退出码 |
| 普通工具 | 通过Codex普通只读权限执行无副作用命令，真实读取未知标记；没有提权/审批重试替代 |
| 隔离边界 | 明确只读profile下不能改写专用控制文件，外层回读保持原内容；只改过隔离策略或旧内核存在兼容疑点时尤其需要 |
| 按需独立运行 | 隔离本次客户端转发依赖后再次成功；所需tmux/服务实际可用 |

普通工具可使用`hostname`、`id -u`、读取本次生成的非秘密标记等。先查`codex exec --help`及`sandbox --help`，选版本支持的只读权限与禁止审批重试设置，保留实际工具记录，不能只让模型回答“已成功”。标记只告知文件路径，不预告内容。更详细的负向测试原则见[容器排障文档](bwrap-container.md#正向和负向验收)；原生宿主也适用该验证原则，但不因此引入容器策略。

遇到工具启动失败时保留命令是否真正执行、错误原文和退出码。模型能回复而工具不能启动，应交付为“模型调用通过、普通工具未通过”，继续针对原因修复；不能宣布完整部署成功。没有实际测试的新主机版本只能标为待验收。

完成后保存该主机自己的安装记录、运行入口与回退材料；技能中只保留可复用结论。整机重启和Windows真实关机不是默认测试，不把配置已完成写成已经通过这些实测。
