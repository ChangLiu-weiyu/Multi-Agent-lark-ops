# Test Notes

## Unit Tests

Run:

```powershell
$env:PYTHONPATH="src"
python -m pytest -q tests
```

Latest known result:

```text
9 passed
```

## Real Lark Read Test

Run:

```powershell
$env:PYTHONPATH="src"
python -m multi_agent_lark_ops.cli --fetch-doc "<Lark document URL>"
```

This calls local `lark-cli docs +fetch` with user identity.

## Rules Dispatch Test

Run:

```powershell
$env:PYTHONPATH="src"
python -m multi_agent_lark_ops.cli --dispatch-doc-rules "<Lark document URL>"
```

Expected behavior:

- Reads the Lark document.
- Extracts near-term work items.
- Routes them by deterministic rules.
- Prints human-review-required output.

## AI Dispatch Test

Run after setting model env vars:

```powershell
$env:PYTHONPATH="src"
$env:OPENAI_PROXY_BASE_URL="https://openai-proxy.miracleplus.com"
$env:DEEPSEEK_API_KEY="<your key>"
$env:DEEPSEEK_MODEL="deepseek-v4-flash"
python -m multi_agent_lark_ops.cli --dispatch-doc-ai "<Lark document URL>"
```

Expected behavior:

- Reads the Lark document.
- Sends the document to the configured AI model.
- Receives JSON work items.
- Routes results to role agents.
- Prints human-review-required output.
