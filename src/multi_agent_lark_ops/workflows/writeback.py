"""Approved review parsing and writeback helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from multi_agent_lark_ops.lark import LarkCliError, LarkClient
from multi_agent_lark_ops.memory import AgentMemoryStore
from multi_agent_lark_ops.roles import get_role
from multi_agent_lark_ops.workflows.review import VALID_REVIEW_STATUSES

APPROVED_WRITE_STATUSES = ("approved", "ready_to_write")
WRITTEN_STATUS = "written_to_lark"


@dataclass(frozen=True)
class WritebackCandidate:
    review_id: str
    summary: str
    description: str
    role_key: str
    source: str
    review_status: str
    idempotency_key: str
    assignee_open_id: str | None = None
    due: str | None = None
    tasklist_id: str | None = None
    suggested_owner: str = ""
    collaborators: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    risk_notes: tuple[str, ...] = ()

    def to_lark_cli_args(self, *, dry_run: bool) -> list[str]:
        args = [
            "task",
            "+create",
            "--summary",
            self.summary,
            "--description",
            self.description,
            "--idempotency-key",
            self.idempotency_key,
        ]
        if self.assignee_open_id:
            args.extend(["--assignee", self.assignee_open_id])
        if self.due:
            args.extend(["--due", self.due])
        if self.tasklist_id:
            args.extend(["--tasklist-id", self.tasklist_id])
        if dry_run:
            args.append("--dry-run")
        return args

    def to_lark_cli_argv(self) -> list[str]:
        return ["lark-cli", *self.to_lark_cli_args(dry_run=True)]


@dataclass(frozen=True)
class WritebackPlan:
    bundle_id: str
    source: str
    review_path: Path
    approved_candidates: tuple[WritebackCandidate, ...]
    skipped_count: int
    allowed_statuses: tuple[str, ...] = VALID_REVIEW_STATUSES


@dataclass(frozen=True)
class WritebackResult:
    review_id: str
    summary: str
    guid: str
    url: str | None
    envelope: dict[str, Any]


@dataclass(frozen=True)
class WritebackExecution:
    plan: WritebackPlan
    results: tuple[WritebackResult, ...]
    updated_review_path: Path | None = None
    memory_episode_count: int = 0
    memory_roles: tuple[str, ...] = ()


class WritebackNotConfirmedError(PermissionError):
    """Raised when a real writeback is attempted without explicit confirmation."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing required field: {key}")
    return value


def _optional_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    return value if isinstance(value, str) else ""


def _optional_tuple(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not value:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"Field '{key}' must be a list when present")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"Field '{key}' must contain strings only")
        if item.strip():
            items.append(item)
    return tuple(items)


def _compose_description(payload: dict[str, Any]) -> str:
    description = _optional_string(payload, "description").strip()
    parts: list[str] = []
    if description:
        parts.append(description)

    source = _optional_string(payload, "source").strip()
    if source:
        parts.extend(["", f"Source: {source}"])

    suggested_owner = _optional_string(payload, "suggested_owner").strip()
    if suggested_owner:
        parts.append(f"Suggested owner: {suggested_owner}")

    collaborators = _optional_tuple(payload, "collaborators")
    if collaborators:
        parts.append("Collaborators: " + ", ".join(collaborators))

    acceptance_criteria = _optional_tuple(payload, "acceptance_criteria")
    if acceptance_criteria:
        parts.append("Acceptance criteria:")
        parts.extend(f"- {item}" for item in acceptance_criteria)

    dependencies = _optional_tuple(payload, "dependencies")
    if dependencies:
        parts.append("Dependencies: " + ", ".join(dependencies))

    risk_notes = _optional_tuple(payload, "risk_notes")
    if risk_notes:
        parts.append("Risk notes:")
        parts.extend(f"- {item}" for item in risk_notes)

    return "\n".join(parts).strip()


def _candidate_from_task_payload(bundle_id: str, payload: dict[str, Any]) -> WritebackCandidate:
    review_id = _require_string(payload, "review_id")
    review_status = _require_string(payload, "review_status")
    if review_status not in APPROVED_WRITE_STATUSES:
        allowed = ", ".join(APPROVED_WRITE_STATUSES)
        raise ValueError(
            f"Task {review_id} has unsupported writeback status '{review_status}'. Allowed: {allowed}"
        )

    summary = _require_string(payload, "summary")
    description = _compose_description(payload)
    role_key = _require_string(payload, "role_key")
    source = _require_string(payload, "source")
    return WritebackCandidate(
        review_id=review_id,
        summary=summary,
        description=description,
        role_key=role_key,
        source=source,
        review_status=review_status,
        idempotency_key=f"{bundle_id}:{review_id}",
        assignee_open_id=_optional_string(payload, "assignee_open_id") or None,
        due=_optional_string(payload, "due") or None,
        tasklist_id=_optional_string(payload, "tasklist_id") or None,
        suggested_owner=_optional_string(payload, "suggested_owner"),
        collaborators=_optional_tuple(payload, "collaborators"),
        acceptance_criteria=_optional_tuple(payload, "acceptance_criteria"),
        dependencies=_optional_tuple(payload, "dependencies"),
        risk_notes=_optional_tuple(payload, "risk_notes"),
    )


def load_review_bundle(path: str | Path) -> dict[str, Any]:
    review_path = Path(path)
    payload = json.loads(review_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Review file must contain a JSON object")
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported review bundle schema version")
    return payload


def build_writeback_plan(review_path: str | Path) -> WritebackPlan:
    payload = load_review_bundle(review_path)
    bundle_id = _require_string(payload, "bundle_id")
    source = _require_string(payload, "source")
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("Review bundle must contain a task list")

    approved_candidates = tuple(
        _candidate_from_task_payload(bundle_id, task)
        for task in tasks
        if isinstance(task, dict) and task.get("review_status") in APPROVED_WRITE_STATUSES
    )
    skipped_count = len(tasks) - len(approved_candidates)
    return WritebackPlan(
        bundle_id=bundle_id,
        source=source,
        review_path=Path(review_path),
        approved_candidates=approved_candidates,
        skipped_count=skipped_count,
    )


def _quote_cli_arg(arg: str) -> str:
    safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._/:+=")
    if arg and all(char in safe_chars for char in arg):
        return arg
    return "'" + arg.replace("'", "''") + "'"


def _render_cli_command(argv: list[str]) -> str:
    return " ".join(_quote_cli_arg(arg) for arg in argv)


def render_writeback_plan_markdown(plan: WritebackPlan) -> str:
    lines = [
        "# Approved Review Dry-Run Writeback",
        "",
        f"- Review file: `{plan.review_path}`",
        f"- Bundle ID: `{plan.bundle_id}`",
        f"- Source: {plan.source}",
        f"- Approved candidates: `{len(plan.approved_candidates)}`",
        f"- Skipped tasks: `{plan.skipped_count}`",
        "",
    ]

    if not plan.approved_candidates:
        lines.extend(["No approved tasks were found for writeback.", ""])
        return "\n".join(lines)

    for index, candidate in enumerate(plan.approved_candidates, start=1):
        lines.extend(
            [
                f"## {index}. {candidate.summary}",
                "",
                f"- Review ID: `{candidate.review_id}`",
                f"- Review status: `{candidate.review_status}`",
                f"- Role: `{candidate.role_key}`",
                f"- Source: {candidate.source}",
                f"- Dry-run idempotency key: `{candidate.idempotency_key}`",
            ]
        )
        if candidate.assignee_open_id:
            lines.append(f"- Assignee: `{candidate.assignee_open_id}`")
        if candidate.due:
            lines.append(f"- Due: `{candidate.due}`")
        if candidate.tasklist_id:
            lines.append(f"- Task list: `{candidate.tasklist_id}`")
        if candidate.suggested_owner:
            lines.append(f"- Suggested owner: {candidate.suggested_owner}")
        if candidate.collaborators:
            lines.append("- Collaborators: " + ", ".join(f"`{item}`" for item in candidate.collaborators))
        if candidate.acceptance_criteria:
            lines.append("- Acceptance criteria:")
            for item in candidate.acceptance_criteria:
                lines.append(f"  - {item}")
        if candidate.dependencies:
            lines.append("- Dependencies:")
            for item in candidate.dependencies:
                lines.append(f"  - {item}")
        if candidate.risk_notes:
            lines.append("- Risk notes:")
            for item in candidate.risk_notes:
                lines.append(f"  - {item}")
        lines.extend(
            [
                "",
                "Dry-run command:",
                "",
                "```bash",
                _render_cli_command(candidate.to_lark_cli_argv()),
                "```",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def _parse_task_create_envelope(envelope: dict[str, Any], *, review_id: str, summary: str) -> WritebackResult:
    data = envelope.get("data")
    if not isinstance(data, dict):
        raise LarkCliError("lark-cli task +create response did not include task data.", envelope=envelope)
    guid = data.get("guid")
    if not isinstance(guid, str) or not guid.strip():
        raise LarkCliError("lark-cli task +create response did not include task guid.", envelope=envelope)
    url = data.get("url")
    return WritebackResult(
        review_id=review_id,
        summary=summary,
        guid=guid,
        url=url if isinstance(url, str) else None,
        envelope=envelope,
    )


def _write_review_bundle(path: Path, payload: dict[str, Any]) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def _persist_writeback_results(review_path: Path, results: Iterable[WritebackResult]) -> Path:
    payload = load_review_bundle(review_path)
    results_by_id = {result.review_id: result for result in results}
    changed = False
    for task in payload.get("tasks", []):
        if not isinstance(task, dict):
            continue
        review_id = task.get("review_id")
        result = results_by_id.get(review_id)
        if result is None:
            continue
        task["review_status"] = WRITTEN_STATUS
        task["written_to_lark_at"] = _utc_now()
        task["lark_guid"] = result.guid
        if result.url:
            task["lark_url"] = result.url
        changed = True
    if changed:
        payload["last_writeback_at"] = _utc_now()
        payload["written_to_lark_count"] = len(results_by_id)
        _write_review_bundle(review_path, payload)
    return review_path


def _memory_event_type(review_status: str) -> str:
    mapping = {
        WRITTEN_STATUS: "task_written_to_lark",
        "approved": "task_review_approved",
        "ready_to_write": "task_review_ready_to_write",
        "rejected": "task_review_rejected",
        "needs_revision": "task_review_needs_revision",
        "needs_human_review": "task_review_pending",
    }
    return mapping.get(review_status, "task_review_reconciled")


def reconcile_writeback_memory(
    review_path: str | Path,
    *,
    memory_store: AgentMemoryStore | None = None,
) -> tuple[int, tuple[str, ...]]:
    payload = load_review_bundle(review_path)
    bundle_id = _require_string(payload, "bundle_id")
    review_source = _require_string(payload, "source")
    store = memory_store or AgentMemoryStore()

    episode_count = 0
    touched_roles: list[str] = []
    for task in payload.get("tasks", []):
        if not isinstance(task, dict):
            continue
        review_status = _optional_string(task, "review_status")
        if not review_status or review_status == "needs_human_review":
            continue
        role_key = _require_string(task, "role_key")
        summary = _require_string(task, "summary")
        review_id = _require_string(task, "review_id")
        role_name = role_key
        try:
            role_name = get_role(role_key).name
        except KeyError:
            pass

        data: dict[str, Any] = {
            "bundle_id": bundle_id,
            "review_id": review_id,
            "review_status": review_status,
            "review_source": review_source,
            "role_name": role_name,
        }
        lark_guid = _optional_string(task, "lark_guid")
        if lark_guid:
            data["lark_guid"] = lark_guid
        lark_url = _optional_string(task, "lark_url")
        if lark_url:
            data["lark_url"] = lark_url
        written_at = _optional_string(task, "written_to_lark_at")
        if written_at:
            data["written_to_lark_at"] = written_at

        store.append_episode(
            role_key=role_key,
            event_type=_memory_event_type(review_status),
            summary=f"{summary} [{review_status}]",
            source=f"review:{bundle_id}",
            data=data,
        )
        episode_count += 1
        if role_key not in touched_roles:
            touched_roles.append(role_key)

    return episode_count, tuple(touched_roles)


def execute_writeback_plan(
    plan: WritebackPlan,
    *,
    client: LarkClient,
    confirmed: bool,
    memory_store: AgentMemoryStore | None = None,
) -> WritebackExecution:
    if not confirmed:
        raise WritebackNotConfirmedError(
            "Refusing to create Lark tasks without explicit confirmation. Re-run with --confirm-writeback."
        )

    results: list[WritebackResult] = []
    updated_review_path: Path | None = None
    for candidate in plan.approved_candidates:
        envelope = client.run_json(candidate.to_lark_cli_args(dry_run=False))
        result = _parse_task_create_envelope(envelope, review_id=candidate.review_id, summary=candidate.summary)
        results.append(result)
        updated_review_path = _persist_writeback_results(plan.review_path, results)

    memory_episode_count = 0
    memory_roles: tuple[str, ...] = ()
    if updated_review_path is not None:
        memory_episode_count, memory_roles = reconcile_writeback_memory(
            updated_review_path,
            memory_store=memory_store,
        )

    return WritebackExecution(
        plan=plan,
        results=tuple(results),
        updated_review_path=updated_review_path,
        memory_episode_count=memory_episode_count,
        memory_roles=memory_roles,
    )


def render_writeback_execution_markdown(execution: WritebackExecution) -> str:
    lines = [
        "# Approved Review Writeback",
        "",
        f"- Review file: `{execution.plan.review_path}`",
        f"- Bundle ID: `{execution.plan.bundle_id}`",
        f"- Created tasks: `{len(execution.results)}`",
    ]
    if execution.updated_review_path:
        lines.append(f"- Review file updated: `{execution.updated_review_path}`")
    if execution.memory_episode_count:
        lines.append(f"- Memory episodes written: `{execution.memory_episode_count}`")
    if execution.memory_roles:
        lines.append("- Memory roles: " + ", ".join(f"`{role}`" for role in execution.memory_roles))
    lines.append("")

    if not execution.results:
        lines.append("No approved tasks were written to Lark.")
        return "\n".join(lines)

    for index, result in enumerate(execution.results, start=1):
        lines.extend(
            [
                f"## {index}. {result.summary}",
                "",
                f"- Review ID: `{result.review_id}`",
                f"- Task GUID: `{result.guid}`",
            ]
        )
        if result.url:
            lines.append(f"- Task URL: {result.url}")
        lines.extend(["", ""])
    return "\n".join(lines).rstrip()
