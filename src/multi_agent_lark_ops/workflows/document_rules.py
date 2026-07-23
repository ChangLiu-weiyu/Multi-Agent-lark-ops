"""Deterministic document workflow helpers."""

from __future__ import annotations

from multi_agent_lark_ops.state import WorkflowState
from multi_agent_lark_ops.workflows.dispatcher import dispatch_work_items
from multi_agent_lark_ops.workflows.extractor import extract_work_items


def analyze_document_with_rules(document_text: str, *, source: str = "lark-doc") -> WorkflowState:
    work_items = extract_work_items(document_text, source=source)
    routing_decisions = dispatch_work_items(work_items)
    return WorkflowState(
        source_text=document_text,
        work_items=work_items,
        routing_decisions=routing_decisions,
        analysis_mode="rules",
        analysis_model=None,
        needs_human_review=True,
    )
