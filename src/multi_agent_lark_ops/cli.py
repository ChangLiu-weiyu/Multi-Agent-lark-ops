"""Command-line entry points for local smoke tests."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from multi_agent_lark_ops.config import load_settings
from multi_agent_lark_ops.lark import LarkClient
from multi_agent_lark_ops.memory import AgentMemoryStore
from multi_agent_lark_ops.roles import DEFAULT_ROLES, get_role
from multi_agent_lark_ops.state import WorkItem, WorkflowState
from multi_agent_lark_ops.workflows.dispatcher import dispatch_work_items
from multi_agent_lark_ops.workflows.document import (
    dispatch_document_text,
    dispatch_document_text_ai,
    dispatch_document_text_rules,
)
from multi_agent_lark_ops.workflows.enhance_drafts import (
    enhance_task_drafts_auto,
    enhance_task_drafts_with_ai,
    enhance_task_drafts_with_rules,
)
from multi_agent_lark_ops.workflows.review import build_review_bundle, export_review_bundle
from multi_agent_lark_ops.workflows.task_drafts import (
    attach_task_drafts,
    render_task_drafts_markdown,
)
from multi_agent_lark_ops.workflows.writeback import (
    build_writeback_plan,
    execute_writeback_plan,
    render_writeback_execution_markdown,
    render_writeback_plan_markdown,
)


DEMO_ITEMS = (
    WorkItem(title="整理暑期实践队行前会议待办", detail="需要提取负责人、截止时间和未完成事项。"),
    WorkItem(title="生成 AI 课程试讲课件检查清单", detail="包含主讲、助教、设备和教案准备情况。"),
    WorkItem(title="跟进学校合作渠道", detail="外联组需要沉淀合作方需求并同步给教务组。"),
    WorkItem(title="准备软著申请材料", detail="学术成果组整理内部工具说明和代码截图。"),
)


def _configure_utf8_output() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def run_demo() -> None:
    print("Configured roles:")
    for role in DEFAULT_ROLES:
        print(f"- {role.key}: {role.name}")

    print("\nDemo dispatch:")
    for decision in dispatch_work_items(DEMO_ITEMS):
        print(f"- [{decision.role_key}] {decision.work_item.title} (confidence={decision.confidence:.2f})")


def fetch_doc(document: str) -> None:
    client = LarkClient(load_settings())
    print(client.read_docx(document))


def _print_state(state: WorkflowState, *, heading: str) -> None:
    print(heading)
    print(f"Extracted {len(state.work_items)} work item(s).")
    print(f"Generated {len(state.task_drafts)} task draft(s).")
    print(f"Analysis mode: {state.analysis_mode}")
    if state.analysis_model:
        print(f"Analysis model: {state.analysis_model}")
    print("Human review required before writing back to Lark: yes")

    for index, decision in enumerate(state.routing_decisions, start=1):
        role = get_role(decision.role_key)
        print(f"\n{index}. [{decision.role_key}] {role.name}")
        print(f"   Task: {decision.work_item.title}")
        if decision.work_item.detail:
            one_line_detail = " / ".join(decision.work_item.detail.splitlines())
            print(f"   Detail: {one_line_detail}")
        print(f"   Confidence: {decision.confidence:.2f}")
        print(f"   Reason: {decision.reason}")


def _document_state(document: str, mode: str) -> WorkflowState:
    client = LarkClient(load_settings())
    content = client.read_docx(document)
    if mode == "ai":
        return dispatch_document_text_ai(content, source=document)
    if mode == "rules":
        return dispatch_document_text_rules(content, source=document)
    return dispatch_document_text(content, source=document)


def _enhance_state(state: WorkflowState, mode: str) -> WorkflowState:
    settings = load_settings()
    memory_store = AgentMemoryStore()
    if mode == "ai":
        return enhance_task_drafts_with_ai(state, settings=settings, memory_store=memory_store)
    if mode == "rules":
        return enhance_task_drafts_with_rules(state, memory_store=memory_store)
    return enhance_task_drafts_auto(state, settings=settings, memory_store=memory_store)


def dispatch_doc(document: str) -> None:
    _print_state(_document_state(document, "auto"), heading="Auto dispatch:")


def dispatch_doc_rules(document: str) -> None:
    _print_state(_document_state(document, "rules"), heading="Rules dispatch:")


def dispatch_doc_ai(document: str) -> None:
    _print_state(_document_state(document, "ai"), heading="AI dispatch:")


def draft_tasks(document: str, mode: str) -> None:
    state = _document_state(document, mode)
    print(render_task_drafts_markdown(state.task_drafts))


def _enhance_and_render(state: WorkflowState, mode: str) -> None:
    state = _enhance_state(state, mode)
    enhanced_count = sum(1 for d in state.task_drafts if d.enhanced)
    print(f"Enhanced {enhanced_count}/{len(state.task_drafts)} draft(s) via {mode} mode.")
    print(render_task_drafts_markdown(state.task_drafts))


def enhance_drafts(document: str, mode: str) -> None:
    state = _document_state(document, mode)
    state = attach_task_drafts(state)
    _enhance_and_render(state, mode)


def enhance_drafts_rules(document: str) -> None:
    state = _document_state(document, "rules")
    state = attach_task_drafts(state)
    _enhance_and_render(state, "rules")


def enhance_drafts_ai(document: str) -> None:
    state = _document_state(document, "ai")
    state = attach_task_drafts(state)
    _enhance_and_render(state, "ai")


def export_review(document: str, mode: str, output_dir: str | None = None) -> None:
    state = _document_state(document, mode)
    state = attach_task_drafts(state)
    state = _enhance_state(state, mode)
    bundle = build_review_bundle(state)
    export = export_review_bundle(
        bundle,
        output_dir=Path(output_dir) if output_dir else None,
    )
    print(f"Exported review bundle: {bundle.bundle_id}")
    print(f"JSON: {export.json_path}")
    print(f"Markdown: {export.markdown_path}")
    print("Human review required before writing back to Lark: yes")


def write_approved_tasks_dry_run(review_json: str) -> None:
    plan = build_writeback_plan(review_json)
    print(render_writeback_plan_markdown(plan))


def write_approved_tasks(review_json: str, *, confirm_writeback: bool) -> None:
    plan = build_writeback_plan(review_json)
    if not confirm_writeback:
        print(render_writeback_plan_markdown(plan))
        raise SystemExit("Refusing to write to Lark without --confirm-writeback.")

    client = LarkClient(load_settings())
    execution = execute_writeback_plan(plan, client=client, confirmed=True)
    print(render_writeback_execution_markdown(execution))


def main() -> None:
    _configure_utf8_output()

    parser = argparse.ArgumentParser(description="Multi-agent Lark operations CLI")
    parser.add_argument("--demo", action="store_true", help="Run the local routing demo")
    parser.add_argument("--fetch-doc", help="Fetch a Lark Docx/Wiki document through local lark-cli")
    parser.add_argument(
        "--dispatch-doc",
        help="Fetch a Lark document, extract work items, and route them using AI when configured",
    )
    parser.add_argument(
        "--dispatch-doc-rules",
        help="Fetch a Lark document, extract work items, and route them using rules only",
    )
    parser.add_argument(
        "--dispatch-doc-ai",
        help="Fetch a Lark document, extract work items, and route them using the model",
    )
    parser.add_argument("--draft-tasks", help="Generate review-only Lark task drafts from a document")
    parser.add_argument(
        "--draft-tasks-rules",
        help="Generate review-only Lark task drafts with rules-only analysis",
    )
    parser.add_argument(
        "--draft-tasks-ai",
        help="Generate review-only Lark task drafts with AI analysis",
    )
    parser.add_argument(
        "--enhance-drafts",
        help="Fetch a Lark doc, draft tasks, then enrich with department agent fields (auto mode)",
    )
    parser.add_argument(
        "--enhance-drafts-rules",
        help="Fetch a Lark doc, draft tasks, then enrich with rules-based department agent fields",
    )
    parser.add_argument(
        "--enhance-drafts-ai",
        help="Fetch a Lark doc, draft tasks, then enrich with AI-powered department agent fields",
    )
    parser.add_argument(
        "--export-review",
        help="Export enhanced task drafts as JSON and Markdown review files (auto mode)",
    )
    parser.add_argument(
        "--export-review-rules",
        help="Export enhanced task drafts as review files using rules-only analysis",
    )
    parser.add_argument(
        "--export-review-ai",
        help="Export enhanced task drafts as review files using AI analysis",
    )
    parser.add_argument(
        "--review-output-dir",
        help="Directory for review JSON/Markdown exports. Defaults to outputs/task_drafts/",
    )
    parser.add_argument(
        "--write-approved-tasks-dry-run",
        help="Read a reviewed JSON bundle and preview approved Lark task creation commands",
    )
    parser.add_argument(
        "--write-approved-tasks",
        help="Read a reviewed JSON bundle and write approved tasks to Lark",
    )
    parser.add_argument(
        "--confirm-writeback",
        action="store_true",
        help="Explicit confirmation gate required before real Lark writeback",
    )
    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    if args.fetch_doc:
        fetch_doc(args.fetch_doc)
        return

    if args.dispatch_doc:
        dispatch_doc(args.dispatch_doc)
        return

    if args.dispatch_doc_rules:
        dispatch_doc_rules(args.dispatch_doc_rules)
        return

    if args.dispatch_doc_ai:
        dispatch_doc_ai(args.dispatch_doc_ai)
        return

    if args.draft_tasks:
        draft_tasks(args.draft_tasks, "auto")
        return

    if args.draft_tasks_rules:
        draft_tasks(args.draft_tasks_rules, "rules")
        return

    if args.draft_tasks_ai:
        draft_tasks(args.draft_tasks_ai, "ai")
        return

    if args.enhance_drafts:
        enhance_drafts(args.enhance_drafts, "auto")
        return

    if args.enhance_drafts_rules:
        enhance_drafts_rules(args.enhance_drafts_rules)
        return

    if args.enhance_drafts_ai:
        enhance_drafts_ai(args.enhance_drafts_ai)
        return

    if args.export_review:
        export_review(args.export_review, "auto", args.review_output_dir)
        return

    if args.export_review_rules:
        export_review(args.export_review_rules, "rules", args.review_output_dir)
        return

    if args.export_review_ai:
        export_review(args.export_review_ai, "ai", args.review_output_dir)
        return

    if args.write_approved_tasks_dry_run:
        write_approved_tasks_dry_run(args.write_approved_tasks_dry_run)
        return

    if args.write_approved_tasks:
        write_approved_tasks(args.write_approved_tasks, confirm_writeback=args.confirm_writeback)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
