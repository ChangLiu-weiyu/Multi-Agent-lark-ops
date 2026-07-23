from multi_agent_lark_ops.config import Settings
from multi_agent_lark_ops.workflows.ai import analyze_document_with_ai


SAMPLE_AI_OUTPUT = """
{
  "work_items": [
    {
      "title": "整理暑期实践队行前会议待办",
      "detail": "部门/上下文：教务、运营两部门",
      "role_key": "operations",
      "confidence": 0.91,
      "reason": "This is an operations coordination task."
    },
    {
      "title": "跟进湖北省创青春数字经济赛道，进行项目挑选、成员招募。",
      "detail": "部门/上下文：竞赛",
      "role_key": "competition",
      "confidence": 0.95,
      "reason": "Competition planning task."
    }
  ]
}
""".strip()


def settings() -> Settings:
    return Settings(
        model_api_key="secret",
        model_base_url="https://example.com",
        model_name="deepseek-v4-flash",
        deepseek_api_key="secret",
        deepseek_model="deepseek-v4-flash",
        semantic_scholar_api_key=None,
        openalex_api_key=None,
        lark_cli_path="lark-cli",
        lark_cli_profile=None,
    )


def test_ai_workflow_uses_model_payload(monkeypatch) -> None:
    calls = []

    def fake_request_model(settings, messages):
        calls.append((settings.model_name, messages))
        return SAMPLE_AI_OUTPUT

    monkeypatch.setattr("multi_agent_lark_ops.workflows.ai._request_model", fake_request_model)

    state = analyze_document_with_ai("doc text", settings=settings(), source="doc-url")

    assert calls[0][0] == "deepseek-v4-flash"
    assert state.analysis_mode == "ai"
    assert state.analysis_model == "deepseek-v4-flash"
    assert [decision.role_key for decision in state.routing_decisions] == ["operations", "competition"]
    assert state.work_items[0].source == "doc-url"
