# 语冰任务流转版架构图

```mermaid
flowchart TB
    subgraph I[输入来源]
        I1[飞书 Docx / Wiki 文档]
        I2[会议纪要 / 妙记\n后续接入]
        I3[群消息 / 人工输入\n后续接入]
    end

    subgraph R[读取与预处理层]
        R1[Lark Reader\nlark-cli docs +fetch]
        R2[Document Normalizer\nMarkdown / XML 文本清洗]
    end

    subgraph C[Coordinator Agent 总调度]
        C1[识别近期待办区块]
        C2[抽取 WorkItem]
        C3[判断任务归属]
        C4[生成 RoutingDecision]
    end

    subgraph A[部门 Agent 协作层]
        A1[Education Agent\n教务任务增强]
        A2[Operations Agent\n运营统筹任务增强]
        A3[Outreach Agent\n外联合作任务增强]
        A4[PR Agent\n宣传内容任务增强]
        A5[Academic Agent\n学术成果任务增强]
        A6[Competition Agent\n竞赛筹备任务增强]
    end

    subgraph E[任务草稿增强]
        E1[补充任务说明]
        E2[建议负责人 / 协作方]
        E3[建议截止时间]
        E4[验收标准]
        E5[依赖关系]
    end

    subgraph H[人工审核]
        H1[Human Review Agent\n汇总待审核清单]
        H2{是否确认创建飞书任务?}
        H3[修改 / 退回对应 Agent]
    end

    subgraph W[飞书写回层]
        W1[Lark Task Draft\n当前已实现]
        W2[Lark Writer Tool\nlark-cli task +create\n待确认后启用]
        W3[飞书任务中心]
        W4[飞书群消息 / 通知\n后续接入]
    end

    I1 --> R1
    I2 -.-> R1
    I3 -.-> R2
    R1 --> R2
    R2 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> C4

    C4 --> A1
    C4 --> A2
    C4 --> A3
    C4 --> A4
    C4 --> A5
    C4 --> A6

    A1 --> E1
    A2 --> E1
    A3 --> E1
    A4 --> E1
    A5 --> E1
    A6 --> E1

    E1 --> E2
    E2 --> E3
    E3 --> E4
    E4 --> E5
    E5 --> W1
    W1 --> H1
    H1 --> H2
    H2 -- 否 --> H3
    H3 --> A1
    H3 --> A2
    H3 --> A3
    H3 --> A4
    H3 --> A5
    H3 --> A6
    H2 -- 是 --> W2
    W2 --> W3
    W2 --> W4
```

## 当前已实现

- `Lark Reader`：通过 `lark-cli docs +fetch` 读取飞书文档。
- `Coordinator Agent` 的基础能力：抽取待办、判断归属、生成路由结果。
- `Lark Task Draft`：把路由结果转换成 review-only 飞书任务草稿。
- `Human Review` 原则：所有写回飞书前都需要人工确认。

## 下一步正式 Multi-Agent 起点

正式 multi-agent 从“部门 Agent 协作层”开始：

1. Coordinator Agent 只负责拆分和分派，不再替各部门完善任务。
2. 每个部门 Agent 接收属于自己的任务草稿。
3. 部门 Agent 独立补充负责人建议、截止时间、验收标准和依赖关系。
4. Human Review Agent 汇总所有部门草稿。
5. 用户确认后，Lark Writer Tool 才调用 `lark-cli task +create`。

## 当前不做的事

- 不自动创建飞书任务。
- 不自动给成员分配任务。
- 不自动发送群通知。
- 不绕过人工审核。
