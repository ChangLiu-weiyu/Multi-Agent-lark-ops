"""Role definitions for the first Yubing multi-agent team."""

from __future__ import annotations

from dataclasses import dataclass

from multi_agent_lark_ops.agent_config import load_agents_config


@dataclass(frozen=True)
class AgentRole:
    key: str
    name: str
    mission: str
    responsibilities: tuple[str, ...]
    keywords: tuple[str, ...]
    default_collaborators: tuple[str, ...] = ()
    draft_fields: tuple[str, ...] = ()


COORDINATOR = AgentRole(
    key="coordinator",
    name="Coordinator Agent",
    mission="Route work, resolve conflicts, and keep cross-department progress visible.",
    responsibilities=(
        "Break ambiguous requests into work items.",
        "Assign work items to department agents.",
        "Request human confirmation before external write actions.",
    ),
    keywords=("统筹", "协调", "分工", "复盘", "进度", "任务"),
    draft_fields=("summary", "description", "role_key", "confidence", "review_status"),
)


DEFAULT_ROLES: tuple[AgentRole, ...] = (
    COORDINATOR,
    AgentRole(
        key="education",
        name="Education Agent",
        mission="Support AI/STEM course design, training, trial teaching, and teaching material delivery.",
        responsibilities=(
            "Draft lesson plans, slides, and teaching scripts.",
            "Track teacher and assistant training readiness.",
            "Summarize equipment and classroom requirements.",
        ),
        keywords=("课程", "课件", "教案", "试讲", "主讲", "助教", "教学", "设备", "培训"),
        default_collaborators=("operations", "outreach"),
        draft_fields=("teaching_materials", "trial_teaching_plan", "equipment_needs", "acceptance_criteria"),
    ),
    AgentRole(
        key="operations",
        name="Operations Agent",
        mission="Keep routine operations, meeting follow-ups, and practice-team execution on track.",
        responsibilities=(
            "Extract action items from documents and meetings.",
            "Track owners, deadlines, and blockers.",
            "Prepare progress summaries for weekly reviews.",
        ),
        keywords=("运营", "会议", "日程", "实践队", "行前", "行中", "行后", "留痕", "机制"),
        default_collaborators=("education", "pr"),
        draft_fields=("owner_hint", "timeline", "progress_tracking", "dependencies"),
    ),
    AgentRole(
        key="outreach",
        name="Outreach Agent",
        mission="Manage partner discovery, relationship follow-up, and cooperation handoff.",
        responsibilities=(
            "Prepare outreach scripts and partner profiles.",
            "Track schools, enterprises, institutions, and NGOs.",
            "Hand partner requirements to education and operations agents.",
        ),
        keywords=("外联", "合作", "学校", "幼儿园", "企业", "公益组织", "渠道", "转化"),
        default_collaborators=("education", "operations"),
        draft_fields=("partner", "contact_action", "handoff_target", "follow_up_plan"),
    ),
    AgentRole(
        key="pr",
        name="PR Agent",
        mission="Coordinate brand content, media assets, publishing plans, and public reports.",
        responsibilities=(
            "Collect photos, videos, scripts, and captions.",
            "Draft posts, posters, reports, and video outlines.",
            "Track publishing status across channels.",
        ),
        keywords=("推文", "视频", "海报", "公众号", "小红书", "素材", "纪录片", "vlog", "品牌", "宣传"),
        default_collaborators=("operations", "outreach"),
        draft_fields=("content_type", "materials_needed", "channel", "acceptance_criteria"),
    ),
    AgentRole(
        key="academic",
        name="Academic Output Agent",
        mission="Support papers, software copyrights, patents, research plans, and innovation projects.",
        responsibilities=(
            "Organize literature review tasks.",
            "Track software copyright and patent materials.",
            "Prepare research and competition evidence packs.",
        ),
        keywords=("论文", "专利", "软著", "大创", "大挑", "文献", "调研", "学术"),
        default_collaborators=("competition",),
        draft_fields=("research_output", "evidence_needed", "method_plan", "acceptance_criteria"),
    ),
    AgentRole(
        key="competition",
        name="Competition Planning Agent",
        mission="Discover competitions, match projects, form teams, and preserve competition knowledge.",
        responsibilities=(
            "Maintain competition pools and deadlines.",
            "Match projects with suitable competitions.",
            "Create preparation plans and post-competition reviews.",
        ),
        keywords=("竞赛", "比赛", "创青春", "商赛", "计设", "组队", "备赛", "报名"),
        default_collaborators=("academic", "pr"),
        draft_fields=("competition_name", "deadline", "team_roles", "materials_needed", "review_plan"),
    ),
)


def _role_from_config(raw: dict[str, object]) -> AgentRole:
    return AgentRole(
        key=str(raw["key"]),
        name=str(raw["name"]),
        mission=str(raw["mission"]),
        responsibilities=tuple(str(item) for item in raw.get("responsibilities", ())),
        keywords=tuple(str(item) for item in raw.get("keywords", ())),
        default_collaborators=tuple(str(item) for item in raw.get("default_collaborators", ())),
        draft_fields=tuple(str(item) for item in raw.get("draft_fields", ())),
    )


def load_roles() -> tuple[AgentRole, ...]:
    try:
        return tuple(_role_from_config(raw) for raw in load_agents_config())
    except Exception:
        return DEFAULT_ROLES


CONFIGURED_ROLES: tuple[AgentRole, ...] = load_roles()


def get_role(role_key: str) -> AgentRole:
    for role in CONFIGURED_ROLES:
        if role.key == role_key:
            return role
    raise KeyError(f"Unknown role: {role_key}")
