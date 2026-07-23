"""Deterministic dispatcher used before model-backed agents are connected."""

from __future__ import annotations

from collections.abc import Iterable

from multi_agent_lark_ops.roles import DEFAULT_ROLES, COORDINATOR, AgentRole
from multi_agent_lark_ops.state import RoutingDecision, WorkItem

_ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    "education": ("教务", "主讲", "助教", "课程", "教学"),
    "operations": ("运营", "统筹", "实践队", "会议"),
    "outreach": ("外联", "合作", "渠道"),
    "pr": ("pr", "宣传", "品牌", "素材", "视频"),
    "academic": ("学术", "软著", "论文", "专利", "大挑"),
    "competition": ("竞赛", "比赛", "商赛", "创青春", "计设"),
}


def _context_boost(role: AgentRole, text: str) -> int:
    aliases = _ROLE_ALIASES.get(role.key, ())
    return 3 if any(alias.lower() in text for alias in aliases) else 0


def route_work_item(work_item: WorkItem, roles: Iterable[AgentRole] = DEFAULT_ROLES) -> RoutingDecision:
    text = f"{work_item.title}\n{work_item.detail}".lower()
    best_role = COORDINATOR
    best_score = 0

    for role in roles:
        keyword_score = sum(1 for keyword in role.keywords if keyword.lower() in text)
        score = keyword_score + _context_boost(role, text)
        if score > best_score:
            best_role = role
            best_score = score

    confidence = min(0.95, 0.35 + best_score * 0.2) if best_score else 0.25
    reason = (
        f"Matched {best_score} routing signal(s) for {best_role.name}."
        if best_score
        else "No strong department keyword matched; send to coordinator for triage."
    )
    routed_item = WorkItem(
        title=work_item.title,
        detail=work_item.detail,
        source=work_item.source,
        assigned_role=best_role.key,
    )
    return RoutingDecision(
        work_item=routed_item,
        role_key=best_role.key,
        confidence=confidence,
        reason=reason,
    )


def dispatch_work_items(work_items: Iterable[WorkItem]) -> list[RoutingDecision]:
    return [route_work_item(item) for item in work_items]
