from multi_agent_lark_ops.config import Settings
from multi_agent_lark_ops.workflows.document import dispatch_document_text_rules
from multi_agent_lark_ops.workflows.extractor import extract_work_items


SAMPLE_DOC = """
# 各部门职责

- 这是职责描述，不应该被抽为待办

# 近期待办

教务、运营两部门：

1.安排7.5开始的第二批主讲与助教培训，马赫、朱君宝协助。
地点：徐东销品茂，时间7.4下午2点

竞赛：

1.跟进湖北省创青春数字经济赛道，进行项目挑选、成员招募。

PR部门：

1.根据各实践队主题和方案，与各队宣传组同学直接对接，推进纪录片和日常切片视频选题策划。
"""


def rules_settings() -> Settings:
    return Settings(
        model_api_key=None,
        model_base_url=None,
        model_name="deepseek-v4-flash",
        deepseek_api_key=None,
        deepseek_model="deepseek-v4-flash",
        semantic_scholar_api_key=None,
        openalex_api_key=None,
        lark_cli_path="lark-cli",
        lark_cli_profile=None,
    )


def test_extract_work_items_from_near_term_todos() -> None:
    items = extract_work_items(SAMPLE_DOC, source="doc-url")

    assert [item.title for item in items] == [
        "安排7.5开始的第二批主讲与助教培训，马赫、朱君宝协助。",
        "跟进湖北省创青春数字经济赛道，进行项目挑选、成员招募。",
        "根据各实践队主题和方案，与各队宣传组同学直接对接，推进纪录片和日常切片视频选题策划。",
    ]
    assert items[0].source == "doc-url"
    assert "教务、运营两部门" in items[0].detail
    assert "徐东销品茂" in items[0].detail


def test_dispatch_document_text_routes_extracted_items() -> None:
    state = dispatch_document_text_rules(SAMPLE_DOC, source="doc-url")

    assert len(state.work_items) == 3
    assert [decision.role_key for decision in state.routing_decisions] == [
        "education",
        "competition",
        "pr",
    ]
    assert state.needs_human_review is True
    assert state.analysis_mode == "rules"
