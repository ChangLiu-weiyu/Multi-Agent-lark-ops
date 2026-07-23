import json
import subprocess

import pytest

from multi_agent_lark_ops.config import Settings
from multi_agent_lark_ops.lark.client import LarkCliError, LarkClient


def settings() -> Settings:
    return Settings(
        model_api_key=None,
        model_base_url=None,
        model_name="deepseek-v4-flash",
        deepseek_api_key=None,
        deepseek_model="deepseek-v4-flash",
        semantic_scholar_api_key=None,
        openalex_api_key=None,
        lark_cli_path="lark-cli.CMD",
        lark_cli_profile=None,
    )


def test_read_docx_uses_lark_cli_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(*args, **kwargs):
        calls.append(args[0])
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "identity": "user",
                    "data": {"document": {"content": "# Demo"}},
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    content = LarkClient(settings()).read_docx("https://example.feishu.cn/docx/token")

    assert content == "# Demo"
    assert "docs" in calls[0]
    assert "+fetch" in calls[0]
    assert "--doc" in calls[0]
    assert "--json" in calls[0]


def test_lark_cli_error_uses_error_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=1,
            stdout="",
            stderr=json.dumps(
                {
                    "ok": False,
                    "error": {"type": "authorization", "message": "missing scope"},
                }
            ),
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(LarkCliError, match="missing scope"):
        LarkClient(settings()).read_docx("doc-token")
