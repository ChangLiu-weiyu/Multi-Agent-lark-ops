from multi_agent_lark_ops.state import RoutingDecision, WorkItem, WorkflowState
from multi_agent_lark_ops.workflows.task_drafts import (
    attach_task_drafts,
    build_task_draft,
    render_task_drafts_markdown,
)


def test_build_task_draft_from_routing_decision() -> None:
    decision = RoutingDecision(
        work_item=WorkItem(
            title="跟进湖北省创青春数字经济赛道",
            detail="部门/上下文：竞赛",
            source="doc-url",
            assigned_role="competition",
        ),
        role_key="competition",
        confidence=0.95,
        reason="Matched competition signals.",
    )

    draft = build_task_draft(decision)

    assert draft.summary == "跟进湖北省创青春数字经济赛道"
    assert draft.role_key == "competition"
    assert draft.review_status == "needs_human_review"
    assert "部门/上下文：竞赛" in draft.description
    assert "Suggested agent: Competition Planning Agent" in draft.description


def test_attach_task_drafts_to_workflow_state() -> None:
    state = WorkflowState(
        routing_decisions=[
            RoutingDecision(
                work_item=WorkItem(title="准备软著申请材料", source="doc-url"),
                role_key="academic",
                confidence=0.8,
                reason="Academic output task.",
            )
        ]
    )

    attach_task_drafts(state)

    assert len(state.task_drafts) == 1
    assert state.task_drafts[0].summary == "准备软著申请材料"


def test_render_task_drafts_markdown() -> None:
    state = WorkflowState(
        routing_decisions=[
            RoutingDecision(
                work_item=WorkItem(title="制作宣传视频", source="doc-url"),
                role_key="pr",
                confidence=0.9,
                reason="PR task.",
            )
        ]
    )
    attach_task_drafts(state)

    rendered = render_task_drafts_markdown(state.task_drafts)

    assert "# Lark Task Drafts" in rendered
    assert "制作宣传视频" in rendered
    assert "No Lark tasks have been created" in rendered
