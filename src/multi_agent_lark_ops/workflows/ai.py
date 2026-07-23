"""AI-backed document extraction and routing."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from pydantic import BaseModel, Field, ValidationError

from multi_agent_lark_ops.config import Settings
from multi_agent_lark_ops.roles import DEFAULT_ROLES, get_role
from multi_agent_lark_ops.state import RoutingDecision, WorkItem, WorkflowState

_ALLOWED_ROLE_KEYS = {role.key for role in DEFAULT_ROLES}


class RoutedWorkItem(BaseModel):
    title: str
    detail: str = ""
    role_key: str = Field(default="coordinator")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reason: str = ""


class DocumentRoutePlan(BaseModel):
    work_items: list[RoutedWorkItem] = Field(default_factory=list)


def _chat_completions_endpoint(base_url: str | None) -> str:
    base = (base_url or "https://api.openai.com").rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return f"{base}/chat/completions"


def _request_model(settings: Settings, messages: list[dict[str, str]]) -> str:
    if not settings.model_api_key:
        raise RuntimeError("Missing model API key")

    payload = {
        "model": settings.model_name,
        "messages": messages,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        _chat_completions_endpoint(settings.model_base_url),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.model_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Model API returned HTTP {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Model API request failed: {exc.reason}") from exc

    data = json.loads(response_body)
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Model API returned no choices")
    content = choices[0].get("message", {}).get("content")
    if not content:
        raise RuntimeError("Model returned no content")
    return content


def _normalize_role_key(role_key: str) -> str:
    return role_key if role_key in _ALLOWED_ROLE_KEYS else "coordinator"


def _prompt(document_text: str) -> list[dict[str, str]]:
    role_list = ", ".join(sorted(_ALLOWED_ROLE_KEYS))
    system = (
        "You are the reasoning layer of a multi-agent operations system. "
        "Extract near-term work items from Chinese organizational documents and route each item "
        f"to exactly one role key from: {role_list}. Return JSON only."
    )
    user = f"""
Read the document and return a JSON object with this shape:
{{
  "work_items": [
    {{
      "title": "short task title",
      "detail": "optional detail and context",
      "role_key": "one of the allowed role keys",
      "confidence": 0.0,
      "reason": "short routing reason"
    }}
  ]
}}

Role key meanings:
- coordinator: cross-department coordination, unclear ownership, review, scheduling
- education: curriculum, teaching, trial lectures, teaching assistants, equipment training
- operations: practice team operations, meeting follow-up, records, progress tracking
- outreach: partner/school/company contact, cooperation, conversion SOP
- pr: promotion, videos, posts, posters, materials, publishing
- academic: papers, software copyright, patents, research, 大挑
- competition: competitions other than 大挑, recruiting teams, preparation, knowledge base

Rules:
- Only extract actionable near-term tasks, especially from sections like 近期待办, 近期重点, 待办, 近期落地重点.
- Ignore role descriptions, background paragraphs, strategy notes, and section titles.
- If a task includes department context like 教务、运营两部门 or PR部门, preserve it in detail.
- Do not invent tasks that are not explicitly actionable.
- Use the best matching role key for each item.
- Output valid JSON only.

Document:
{document_text}
""".strip()
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _to_routing_decision(item: RoutedWorkItem, *, source: str) -> RoutingDecision:
    role_key = _normalize_role_key(item.role_key)
    work_item = WorkItem(title=item.title, detail=item.detail, source=source, assigned_role=role_key)
    return RoutingDecision(
        work_item=work_item,
        role_key=role_key,
        confidence=item.confidence,
        reason=item.reason or f"Model routed to {get_role(role_key).name}.",
    )


def analyze_document_with_ai(document_text: str, *, settings: Settings, source: str = "lark-doc") -> WorkflowState:
    content = _request_model(settings, _prompt(document_text))

    try:
        plan = DocumentRoutePlan.model_validate_json(content)
    except ValidationError:
        try:
            plan_data = json.loads(content)
        except json.JSONDecodeError as json_exc:
            raise RuntimeError("Model output was not valid JSON") from json_exc
        plan = DocumentRoutePlan.model_validate(plan_data)

    work_items: list[WorkItem] = []
    routing_decisions: list[RoutingDecision] = []
    for item in plan.work_items:
        decision = _to_routing_decision(item, source=source)
        work_items.append(decision.work_item)
        routing_decisions.append(decision)
    return WorkflowState(
        source_text=document_text,
        work_items=work_items,
        routing_decisions=routing_decisions,
        analysis_mode="ai",
        analysis_model=settings.model_name,
        needs_human_review=True,
    )


def analyze_document_with_ai_or_fallback(document_text: str, *, settings: Settings, source: str = "lark-doc") -> WorkflowState:
    try:
        return analyze_document_with_ai(document_text, settings=settings, source=source)
    except Exception:
        from multi_agent_lark_ops.workflows.document_rules import analyze_document_with_rules

        return analyze_document_with_rules(document_text, source=source)
