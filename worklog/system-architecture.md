# 系统架构图（当前实现）

```mermaid
flowchart TB
    subgraph Lark[飞书 / Lark]
        L1[飞书 Docx / Wiki 文档]
        L2[飞书任务中心\n后续接入]
        L3[飞书消息 / 群通知\n后续接入]
    end

    subgraph CLI[CLI 入口 cli.py]
        CL1[--demo]
        CL2[--fetch-doc]
        CL3[--dispatch-doc\n--dispatch-doc-ai\n--dispatch-doc-rules]
        CL4[--draft-tasks\n--draft-tasks-ai\n--draft-tasks-rules]
        CL5[--enhance-drafts\n下一步]
    end

    subgraph Config[配置层 可调优]
        CF1[config/agents.json\n机器读取]
        CF2[config/agents.yaml\n人类参考]
        CF3[.env\n密钥与模型配置]
    end

    subgraph Adapter[飞书适配层]
        AD1[LarkClient\nlark-cli docs +fetch]
        AD2[Lark Writer Tool\nlark-cli task +create\n下一步]
    end

    subgraph Workflow[工作流层]
        WF1[document.py\n流程选择器]
        WF2[extractor.py\n近期待办抽取]
        WF3[dispatcher.py\n规则路由]
        WF4[ai.py\nAI 抽取与路由]
        WF5[task_drafts.py\n任务草稿生成]
        WF6[document_rules.py\n规则版封装]
    end

    subgraph Agents[Agent 层]
        AG0[Coordinator Agent\n已实现基础分派]
        AG1[Education Agent]
        AG2[Operations Agent]
        AG3[Outreach Agent]
        AG4[PR Agent]
        AG5[Academic Agent]
        AG6[Competition Agent]
    end

    subgraph Memory[记忆层 本地文件]
        M1[memory/agents/<role>/profile.md]
        M2[memory/agents/<role>/episodes.jsonl]
        M3[memory/agents/<role>/knowledge/]
    end

    subgraph State[状态模型]
        S1[WorkItem]
        S2[RoutingDecision]
        S3[TaskDraft]
        S4[WorkflowState]
    end

    subgraph Review[审核层]
        R1[Human Review\n人工确认]
        R2[Enhanced Drafts\n增强草稿\n下一步]
    end

    L1 --> AD1
    AD1 --> CL2
    AD1 --> CL3
    AD1 --> CL4
    AD1 --> CL5

    CF1 --> Agents
    CF3 --> WF4

    CL3 --> WF1
    CL4 --> WF1
    CL5 --> WF1

    WF1 --> WF2
    WF1 --> WF3
    WF1 --> WF4
    WF1 --> WF5
    WF3 --> WF6

    WF3 --> AG0
    WF4 --> AG0
    AG0 --> AG1
    AG0 --> AG2
    AG0 --> AG3
    AG0 --> AG4
    AG0 --> AG5
    AG0 --> AG6

    AG1 --> M1
    AG2 --> M1
    AG3 --> M1
    AG4 --> M1
    AG5 --> M1
    AG6 --> M1

    AG1 --> R2
    AG2 --> R2
    AG3 --> R2
    AG4 --> R2
    AG5 --> R2
    AG6 --> R2

    WF5 --> R1
    R2 --> R1
    R1 --> AD2
    AD2 --> L2
    AD2 --> L3

    WF1 --> S1
    WF1 --> S2
    WF1 --> S3
    WF1 --> S4
```

## 图例

- 实线箭头：当前已实现的数据流
- 带有"下一步"标注的节点：尚未实现，是正式 multi-agent 协作层的入口
- `Config` 层和 `Memory` 层都是本地文件，可人工编辑和调优

## 当前已实现的链路

```text
飞书文档
-> LarkClient (lark-cli docs +fetch)
-> document.py 选择规则或 AI
-> extractor + dispatcher / ai.py
-> Coordinator Agent 分派
-> task_drafts.py 生成任务草稿
-> Human Review 待确认
```

## 下一步要接的部分

```text
Coordinator Agent 分派
-> 部门 Agent 读取 profile + episodes + knowledge
-> 部门 Agent 独立增强任务草稿
-> Human Review 汇总审核
-> Lark Writer Tool (lark-cli task +create) 写入飞书任务
```

## 分层说明

| 层 | 职责 | 当前状态 |
|-|-|-|
| CLI | 用户入口 | 已实现 |
| 配置层 | 部门定义、模型配置 | 已实现，可调优 |
| 飞书适配层 | 读写飞书 | 读取已实现，写入下一步 |
| 工作流层 | 抽取、路由、草稿 | 已实现 |
| Agent 层 | 角色协作 | Coordinator 已实现，部门增强下一步 |
| 记忆层 | profile / episodes / knowledge | 骨架已实现，待积累 |
| 状态模型 | WorkItem / RoutingDecision / TaskDraft | 已实现 |
| 审核层 | 人工确认 | 草稿审核已实现，写入审核下一步 |
