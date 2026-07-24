"""Tests for approved-review dry-run and real writeback."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from multi_agent_lark_ops.lark import LarkCliError
from multi_agent_lark_ops.memory import AgentMemoryStore
from multi_agent_lark_ops.workflows.writeback import (
    APPROVED_WRITE_STATUSES,
    WritebackNotConfirmedError,
    build_writeback_plan,
    execute_writeback_plan,
    reconcile_writeback_memory,
    render_writeback_execution_markdown,
    render_writeback_plan_markdown,
)


class FakeLarkClient:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = responses
        self.calls: list[list[str]] = []

    def run_json(self, args: list[str]) -> dict:
        self.calls.append(args)
        if not self.responses:
            raise AssertionError("No fake response configured")
        return self.responses.pop(0)


def _memory_store(tmp_path) -> AgentMemoryStore:
    return AgentMemoryStore(root=tmp_path / "memory")


def _review_payload() -> dict:
    return {
        "schema_version": 1,
        "bundle_id": "review-test",
        "source": "doc-url",
        "tasks": [
            {
                "review_id": "001-education",
                "summary": "设计 AI 课程试讲课件",
                "description": "教务组需要完成试讲课件。",
                "role_key": "education",
                "source": "doc-url",
                "confidence": 0.91,
                "routing_reason": "Education task.",
                "review_status": "approved",
                "assignee_open_id": "ou_test",
                "due": "2026-08-01",
                "tasklist_id": "tasklist-guid",
                "suggested_owner": "教务组负责人",
                "collaborators": ["operations"],
                "acceptance_criteria": ["试讲通过审核"],
                "dependencies": ["设备到位"],
                "risk_notes": ["确认截止时间"],
                "enhanced": True,
                "enhanced_by": "education",
            },
            {
                "review_id": "002-pr",
                "summary": "制作宣传视频",
                "description": "PR 组制作宣传视频。",
                "role_key": "pr",
                "source": "doc-url",
                "confidence": 0.88,
                "routing_reason": "PR task.",
                "review_status": "needs_human_review",
            },
            {
                "review_id": "003-ops",
                "summary": "整理会议待办",
                "description": "运营组整理会议待办。",
                "role_key": "operations",
                "source": "doc-url",
                "confidence": 0.8,
                "routing_reason": "Operations task.",
                "review_status": "ready_to_write",
            },
        ],
    }


def _write_review_file(tmp_path, payload: dict) -> str:
    path = tmp_path / "review.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return str(path)


def _lark_success(guid: str) -> dict:
    return {
        "ok": True,
        "identity": "user",
        "data": {
            "guid": guid,
            "url": f"https://applink.larkoffice.com/client/todo/detail?guid={guid}",
        },
    }


def test_approved_statuses_are_explicit() -> None:
    assert APPROVED_WRITE_STATUSES == ("approved", "ready_to_write")


def test_build_writeback_plan_filters_approved_tasks(tmp_path) -> None:
    path = _write_review_file(tmp_path, _review_payload())
    plan = build_writeback_plan(path)

    assert plan.bundle_id == "review-test"
    assert len(plan.approved_candidates) == 2
    assert plan.skipped_count == 1
    assert [c.review_id for c in plan.approved_candidates] == ["001-education", "003-ops"]


def test_writeback_candidate_maps_lark_cli_arguments(tmp_path) -> None:
    path = _write_review_file(tmp_path, _review_payload())
    candidate = build_writeback_plan(path).approved_candidates[0]
    argv = candidate.to_lark_cli_argv()

    assert argv[:5] == ["lark-cli", "task", "+create", "--summary", "设计 AI 课程试讲课件"]
    assert "--idempotency-key" in argv
    assert "review-test:001-education" in argv
    assert "--assignee" in argv and "ou_test" in argv
    assert "--due" in argv and "2026-08-01" in argv
    assert "--dry-run" in argv


def test_candidate_description_includes_enhanced_context(tmp_path) -> None:
    path = _write_review_file(tmp_path, _review_payload())
    candidate = build_writeback_plan(path).approved_candidates[0]

    assert "教务组需要完成试讲课件" in candidate.description
    assert "Suggested owner: 教务组负责人" in candidate.description
    assert "Acceptance criteria:" in candidate.description


def test_render_writeback_plan_markdown(tmp_path) -> None:
    path = _write_review_file(tmp_path, _review_payload())
    rendered = render_writeback_plan_markdown(build_writeback_plan(path))

    assert "Approved Review Dry-Run Writeback" in rendered
    assert "Approved candidates: `2`" in rendered
    assert "lark-cli task +create" in rendered


def test_no_approved_tasks_is_valid_empty_plan(tmp_path) -> None:
    payload = _review_payload()
    for task in payload["tasks"]:
        task["review_status"] = "needs_human_review"
    path = _write_review_file(tmp_path, payload)

    plan = build_writeback_plan(path)
    assert len(plan.approved_candidates) == 0
    assert plan.skipped_count == 3
    assert "No approved tasks were found" in render_writeback_plan_markdown(plan)


def test_execute_writeback_requires_confirmation(tmp_path) -> None:
    path = _write_review_file(tmp_path, _review_payload())
    plan = build_writeback_plan(path)

    with pytest.raises(WritebackNotConfirmedError, match="confirm-writeback"):
        execute_writeback_plan(plan, client=FakeLarkClient([]), confirmed=False)


def test_execute_writeback_calls_lark_client_and_parses_results(tmp_path) -> None:
    path = _write_review_file(tmp_path, _review_payload())
    plan = build_writeback_plan(path)
    client = FakeLarkClient([_lark_success("guid-1"), _lark_success("guid-2")])

    execution = execute_writeback_plan(
        plan, client=client, confirmed=True, memory_store=_memory_store(tmp_path)
    )

    assert len(client.calls) == 2
    assert "--dry-run" not in client.calls[0]
    assert execution.results[0].guid == "guid-1"
    assert execution.results[1].summary == "整理会议待办"


def test_render_writeback_execution_markdown(tmp_path) -> None:
    path = _write_review_file(tmp_path, _review_payload())
    plan = build_writeback_plan(path)
    client = FakeLarkClient([_lark_success("guid-1"), _lark_success("guid-2")])

    execution = execute_writeback_plan(
        plan, client=client, confirmed=True, memory_store=_memory_store(tmp_path)
    )
    rendered = render_writeback_execution_markdown(execution)

    assert "Approved Review Writeback" in rendered
    assert "Created tasks: `2`" in rendered
    assert "guid-1" in rendered


def test_execute_writeback_updates_review_json(tmp_path) -> None:
    path = _write_review_file(tmp_path, _review_payload())
    plan = build_writeback_plan(path)
    client = FakeLarkClient([_lark_success("guid-1"), _lark_success("guid-2")])

    execution = execute_writeback_plan(
        plan, client=client, confirmed=True, memory_store=_memory_store(tmp_path)
    )
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    tasks_by_id = {task["review_id"]: task for task in payload["tasks"]}

    assert tasks_by_id["001-education"]["review_status"] == "written_to_lark"
    assert tasks_by_id["001-education"]["lark_guid"] == "guid-1"
    assert tasks_by_id["003-ops"]["review_status"] == "written_to_lark"
    assert tasks_by_id["002-pr"]["review_status"] == "needs_human_review"


def test_reconcile_writeback_memory_records_episodes(tmp_path) -> None:
    path = _write_review_file(tmp_path, _review_payload())
    plan = build_writeback_plan(path)
    client = FakeLarkClient([_lark_success("guid-1"), _lark_success("guid-2")])
    store = _memory_store(tmp_path)

    execution = execute_writeback_plan(plan, client=client, confirmed=True, memory_store=store)

    assert execution.memory_episode_count == 2
    assert "education" in execution.memory_roles
    assert "operations" in execution.memory_roles

    edu_episodes = store.read_recent_episodes("education")
    ops_episodes = store.read_recent_episodes("operations")

    assert len(edu_episodes) == 1
    assert edu_episodes[0].event_type == "task_written_to_lark"
    assert "设计 AI 课程试讲课件" in edu_episodes[0].summary
    assert edu_episodes[0].data["lark_guid"] == "guid-1"

    assert len(ops_episodes) == 1
    assert ops_episodes[0].event_type == "task_written_to_lark"
    assert ops_episodes[0].data["lark_guid"] == "guid-2"


def test_reconcile_writeback_memory_skips_unreviewed(tmp_path) -> None:
    path = _write_review_file(tmp_path, _review_payload())
    store = _memory_store(tmp_path)

    episode_count, roles = reconcile_writeback_memory(path, memory_store=store)

    assert episode_count == 2
    assert "pr" not in roles


def test_reconcile_standalone_without_writeback(tmp_path) -> None:
    payload = _review_payload()
    payload["tasks"][0]["review_status"] = "rejected"
    path = _write_review_file(tmp_path, payload)
    store = _memory_store(tmp_path)

    episode_count, roles = reconcile_writeback_memory(path, memory_store=store)

    assert episode_count == 2
    episodes = store.read_recent_episodes("education")
    assert episodes[0].event_type == "task_review_rejected"


def test_rejects_unsupported_schema_version(tmp_path) -> None:
    payload = _review_payload()
    payload["schema_version"] = 999
    path = _write_review_file(tmp_path, payload)

    with pytest.raises(ValueError, match="schema version"):
        build_writeback_plan(path)


def test_rejects_missing_required_field_on_approved_task(tmp_path) -> None:
    payload = _review_payload()
    del payload["tasks"][0]["summary"]
    path = _write_review_file(tmp_path, payload)

    with pytest.raises(ValueError, match="summary"):
        build_writeback_plan(path)


def test_rejects_bad_list_field_on_approved_task(tmp_path) -> None:
    payload = _review_payload()
    payload["tasks"][0]["collaborators"] = "operations"
    path = _write_review_file(tmp_path, payload)

    with pytest.raises(ValueError, match="collaborators"):
        build_writeback_plan(path)


def test_execute_writeback_raises_if_task_create_missing_guid(tmp_path) -> None:
    payload = _review_payload()
    path = _write_review_file(tmp_path, payload)
    plan = build_writeback_plan(path)
    bad_response = {"ok": True, "identity": "user", "data": {"url": "https://example.com"}}
    client = FakeLarkClient([bad_response, _lark_success("guid-2")])

    with pytest.raises(LarkCliError, match="task guid"):
        execute_writeback_plan(plan, client=client, confirmed=True, memory_store=_memory_store(tmp_path))
