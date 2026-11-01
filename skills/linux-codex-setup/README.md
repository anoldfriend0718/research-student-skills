# Linux Codex部署与排障

版本：v0.1.0。供Agent使用的部署工作流，适用于新CentOS及其他Linux服务器；不是保证兼容所有系统的一键安装脚本。

## 能完成什么

- 核验SSH目标、发行版、架构、内核、glibc、权限及既有安装；没有Python时用基础shell检查。
- 按当前官方分发选择用户级安装和无头登录方式，按需配置独立网络与后台会话。
- 分别验证认证、真实模型请求、普通隔离工具和只读边界，保留回退记录。
- 用户明确需要时，再处理ChatGPT桌面和Dot设备接入。该能力取决于当前产品、账号和系统环境。

## 安装

在本仓库目录执行：

```text
python install.py --agent codex --only linux-codex-setup --dry-run
python install.py --agent codex --only linux-codex-setup
```

仓库安装器需要Python3.11+，运行在安装技能的客户端；这不是目标CentOS服务器的Python要求。独立ZIP也可解压，将`linux-codex-setup`目录放到Agent实际使用的技能目录。Codex通常为`~/.agents/skills/`，已有环境也可能使用`~/.codex/skills/`；只选择一处，同名目录存在时先备份，不直接覆盖。

重新载入技能后，例如请求：

> 使用 $linux-codex-setup，在SSH别名 my-centos 指向的服务器安装Codex。先检查系统和已有配置，采用用户级安装，验证真实模型调用和普通工具执行；我需要断开本机后继续运行。

首次部署需要可用SSH入口和官方账号认证；密码在终端或官方登录页输入，不粘贴到聊天。技能本身不会提供账号、网络出口或管理员权限。

## 内容与验证边界

入口为[SKILL.md](SKILL.md)。新机器先读[首次部署流程](references/new-centos.md)，容器隔离问题参考[排障方法](references/bwrap-container.md)。`scripts/probe_linux.py`仅使用标准库，需要目标Linux已有Python3.6+；它不联网、不安装、不启动服务，也不检查登录凭据。

[匿名CentOS8案例](references/centos8-case.md)记录真实测试，但未完成对所有CentOS版本的安装矩阵验证。musl包不能补齐旧内核能力；容器也共享宿主内核。旧系统的实际可用性以新目标上的测试为准。公开包不含原服务器地址、私人目录、账号缓存或安全策略安装脚本。

许可沿用仓库MIT License；包内附副本。官方文档与第三方产品名称不表示本技能获得官方认证。
