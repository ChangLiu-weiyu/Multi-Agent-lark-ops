"""Thin Lark/Feishu client boundary backed by the local lark-cli."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

from multi_agent_lark_ops.config import Settings


class LarkCliError(RuntimeError):
    """Raised when lark-cli returns an error envelope or invalid output."""

    def __init__(
        self,
        message: str,
        *,
        returncode: int | None = None,
        envelope: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.envelope = envelope or {}


class LarkConfirmationRequiredError(LarkCliError):
    """Raised when lark-cli asks for explicit high-risk write confirmation."""


@dataclass
class LarkClient:
    settings: Settings

    def _base_args(self) -> list[str]:
        args = [self.settings.lark_cli_path]
        if self.settings.lark_cli_profile:
            args.extend(["--profile", self.settings.lark_cli_profile])
        return args

    def _command_args(self, args: list[str]) -> list[str]:
        command = [*self._base_args(), *args]
        executable = self.settings.lark_cli_path.lower()
        if sys.platform.startswith("win") and executable.endswith((".cmd", ".bat", ".ps1")):
            return ["cmd.exe", "/d", "/s", "/c", *command]
        return command

    def run_json(self, args: list[str]) -> dict[str, Any]:
        env = os.environ.copy()
        env["LARKSUITE_CLI_NO_UPDATE_NOTIFIER"] = "1"
        env["LARKSUITE_CLI_NO_SKILLS_NOTIFIER"] = "1"

        completed = subprocess.run(
            self._command_args(args),
            capture_output=True,
            check=False,
            encoding="utf-8",
            env=env,
        )
        output = completed.stdout if completed.returncode == 0 else completed.stderr

        try:
            envelope = json.loads(output)
        except json.JSONDecodeError as exc:
            raise LarkCliError(
                "lark-cli did not return valid JSON.",
                returncode=completed.returncode,
                envelope={"stdout": completed.stdout, "stderr": completed.stderr},
            ) from exc

        error = envelope.get("error", {})
        if completed.returncode == 10 and error.get("type") == "confirmation":
            raise LarkConfirmationRequiredError(
                error.get("message", "lark-cli requires confirmation."),
                returncode=completed.returncode,
                envelope=envelope,
            )

        if completed.returncode != 0 or envelope.get("ok") is not True:
            raise LarkCliError(
                error.get("message", "lark-cli command failed."),
                returncode=completed.returncode,
                envelope=envelope,
            )

        return envelope

    def read_docx(self, document: str, *, doc_format: str = "markdown") -> str:
        envelope = self.run_json(
            [
                "docs",
                "+fetch",
                "--as",
                "user",
                "--doc",
                document,
                "--doc-format",
                doc_format,
                "--detail",
                "simple",
                "--json",
            ]
        )
        content = envelope.get("data", {}).get("document", {}).get("content")
        if not isinstance(content, str):
            raise LarkCliError(
                "lark-cli docs +fetch response did not include document content.",
                envelope=envelope,
            )
        return content

    def create_task(self, title: str, description: str, assignee_open_id: str | None = None) -> str:
        raise NotImplementedError(
            "create_task is intentionally not wired yet. Add a human review step before CLI writes."
        )

    def send_message(self, receive_id: str, text: str) -> str:
        raise NotImplementedError(
            "send_message is intentionally not wired yet. Add a human review step before CLI writes."
        )
