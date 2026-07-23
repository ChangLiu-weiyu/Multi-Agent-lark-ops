from multi_agent_lark_ops.roles import CONFIGURED_ROLES, DEFAULT_ROLES, get_role


def test_default_roles_include_six_departments_and_coordinator() -> None:
    role_keys = {role.key for role in DEFAULT_ROLES}

    assert {
        "coordinator",
        "education",
        "operations",
        "outreach",
        "pr",
        "academic",
        "competition",
    } <= role_keys


def test_get_role_returns_matching_role() -> None:
    assert get_role("operations").name == "Operations Agent"


def test_configured_roles_include_tunable_fields() -> None:
    education = next(role for role in CONFIGURED_ROLES if role.key == "education")

    assert "operations" in education.default_collaborators
    assert "acceptance_criteria" in education.draft_fields
