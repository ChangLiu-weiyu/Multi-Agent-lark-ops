# Multi-Agent Lark Ops 中文说明

Multi-Agent Lark Ops 是一个面向 Lark/飞书团队协作场景的可配置多 Agent 工作流系统。

它可以读取飞书文档，提取可执行任务，将任务分派给不同部门 Agent，生成部门增强后的任务草稿，导出人工审核包，并在明确确认后把已审核任务写入飞书任务。同时，系统会把审核和写入结果回填到各部门 Agent 的本地记忆中，让 Agent 逐步积累组织经验。

## 当前能力

- 通过本地 `lark-cli` 读取飞书 Docx/Wiki 文档。
- 从 `近期待办`、`近期重点` 等内容中提取任务。
- 将任务路由到不同角色 Agent。
- 支持规则模式和 AI 模式两种分析方式。
- 生成只供人工审核的飞书任务草稿。
- 使用部门 Agent 增强草稿，包括负责人建议、协作者、验收标准、依赖项和风险提示。
- 导出 JSON 和 Markdown 格式的审核包。
- 从审核后的 JSON 中筛选 `approved` 和 `ready_to_write` 任务。
- 支持 `lark-cli task +create --dry-run` 写入预览。
- 只有显式提供 `--confirm-writeback` 时才会真正写入飞书任务。
- 写入成功后，将 review JSON 中对应任务标记为 `written_to_lark`。
- 将审核和写入结果记录到各部门 Agent 的 `episodes.jsonl` 记忆文件中。
- 通过 `config/agents.json` 配置 Agent，而不是在代码中硬编码角色。

## 当前系统链路

```text
飞书文档
-> LarkClient
-> 文档理解
-> 任务提取
-> Agent 分派
-> 任务草稿
-> 部门 Agent 增强
-> 审核包 JSON/Markdown
-> 人工审核
-> dry-run 写入预览
-> 确认后写入飞书任务
-> review JSON 状态回填
-> Agent 记忆回填
```

## 代码结构

- `src/multi_agent_lark_ops/cli.py`：命令行入口。
- `src/multi_agent_lark_ops/lark/`：本地 `lark-cli` 适配层。
- `src/multi_agent_lark_ops/workflows/`：文档理解、任务分派、AI 分析、草稿生成、增强、审核导出和写回逻辑。
- `src/multi_agent_lark_ops/roles.py`：Agent 角色定义和路由元数据。
- `src/multi_agent_lark_ops/memory.py`：文件型 Agent 记忆存储。
- `config/agents.json`：机器可读的 Agent 配置。
- `config/agents.yaml`：便于人工编辑的 Agent 配置参考。
- `memory/agents/<role_key>/`：各部门 Agent 的 profile、episodes 和 knowledge。
- `outputs/task_drafts/`：运行时生成的审核文件，已被 Git 忽略。
- `worklog/`：架构图、任务流转图和开发进度记录。

## 已实现状态

已完成：

- 飞书文档读取。
- 基于规则的任务提取和路由。
- 基于 AI 的任务提取和路由。
- 只读审核型任务草稿生成。
- 部门 Agent 草稿增强层。
- JSON/Markdown 审核包导出。
- 已审核任务解析。
- 飞书任务 dry-run 写入预览。
- 显式确认后的飞书任务真实写入。
- review JSON 状态回填为 `written_to_lark`。
- Agent 记忆回填到 `episodes.jsonl`。
- 可配置 Agent 角色系统。
- 本地 Markdown 架构与进度文档。

暂未实现：

- 飞书消息通知。
- 自动化人工审批流。
- 更多写回目标，例如群消息、跟进记录、飞书文档更新等。

## 快速开始

建议在 PowerShell 中运行：

```powershell
$env:PYTHONPATH="src"
python -m multi_agent_lark_ops.cli --help
```

读取飞书文档：

```powershell
python -m multi_agent_lark_ops.cli --fetch-doc "<飞书文档链接>"
```

生成 AI 任务草稿：

```powershell
python -m multi_agent_lark_ops.cli --draft-tasks-ai "<飞书文档链接>"
```

生成部门 Agent 增强草稿：

```powershell
python -m multi_agent_lark_ops.cli --enhance-drafts-ai "<飞书文档链接>"
```

导出人工审核包：

```powershell
python -m multi_agent_lark_ops.cli --export-review-ai "<飞书文档链接>"
```

默认会生成两份文件：

```text
outputs/task_drafts/<review-id>.json
outputs/task_drafts/<review-id>.md
```

人工审核时，在 JSON 中将需要写入的任务状态改为：

```text
approved
```

或：

```text
ready_to_write
```

预览飞书任务写入：

```powershell
python -m multi_agent_lark_ops.cli --write-approved-tasks-dry-run "outputs/task_drafts/<review-id>.json"
```

真正写入飞书任务：

```powershell
python -m multi_agent_lark_ops.cli --write-approved-tasks "outputs/task_drafts/<review-id>.json" --confirm-writeback
```

注意：没有 `--confirm-writeback` 时，系统不会真正创建飞书任务。

## 审核状态

review JSON 中的任务支持以下状态：

- `needs_human_review`：需要人工审核。
- `approved`：已批准，可以进入写入流程。
- `rejected`：已拒绝。
- `needs_revision`：需要修改后再审核。
- `ready_to_write`：已准备好写入。
- `written_to_lark`：已经成功写入飞书任务。

只有 `approved` 和 `ready_to_write` 会被写回命令选中。

## AI 配置

当前 AI 层使用 OpenAI-compatible Chat Completions 接口，默认模型是：

```text
deepseek-v4-flash
```

环境变量示例：

```powershell
OPENAI_PROXY_BASE_URL=https://openai-proxy.miracleplus.com
DEEPSEEK_API_KEY=<your key>
DEEPSEEK_MODEL=deepseek-v4-flash
```

系统优先读取 `DEEPSEEK_API_KEY`，也支持用 `GPT_API_KEY` 作为 fallback。

## Agent 配置与记忆

Agent 角色可以不改代码直接调优：

- `config/agents.json`：运行时读取。
- `config/agents.yaml`：人工编辑参考。

每个 Agent 的记忆目录：

```text
memory/agents/<role_key>/profile.md
memory/agents/<role_key>/episodes.jsonl
memory/agents/<role_key>/knowledge/README.md
```

写入成功后，系统会把任务结果记录到对应部门的 `episodes.jsonl`。例如教务任务写入成功后，会记录到：

```text
memory/agents/education/episodes.jsonl
```

这些记忆会在后续 AI 草稿增强时作为上下文，让部门 Agent 越用越贴合实际组织流程。

## 测试

当前测试结果：

```text
46 passed
```

运行方式：

```powershell
$env:PYTHONPATH="src"
D:\Anaconda\python.exe -m pytest -q tests
```

## 开发文档

项目进度和图示在 `worklog/` 下：

- [organization-chart.md](worklog/organization-chart.md)
- [task-flow-chart.md](worklog/task-flow-chart.md)
- [system-architecture.md](worklog/system-architecture.md)
- [development-progress.md](worklog/development-progress.md)

## 下一步路线

1. 增加飞书消息通知和任务写入后的提醒。
2. 增加确认写入后的群聊/个人消息 handoff。
3. 扩展更多写回目标，例如飞书文档、任务评论、会议纪要跟进记录等。
