# Architecture Notes

## Layers

1. CLI layer: `src/multi_agent_lark_ops/cli.py`
2. Configuration layer: `src/multi_agent_lark_ops/config.py`
3. Lark adapter: `src/multi_agent_lark_ops/lark/client.py`
4. Role model: `src/multi_agent_lark_ops/roles.py`
5. Shared state: `src/multi_agent_lark_ops/state.py`
6. Rules workflow: `src/multi_agent_lark_ops/workflows/document_rules.py`
7. AI workflow: `src/multi_agent_lark_ops/workflows/ai.py`
8. Workflow selector: `src/multi_agent_lark_ops/workflows/document.py`

## Routing Modes

- `--dispatch-doc-rules`: deterministic extraction and keyword/context routing.
- `--dispatch-doc-ai`: AI extraction and routing through a model endpoint.
- `--dispatch-doc`: auto mode. Uses AI if model credentials exist, otherwise uses rules.

## Model Configuration

The current model target is `deepseek-v4-flash`.

Supported environment variables:

```text
OPENAI_PROXY_BASE_URL=https://openai-proxy.miracleplus.com
DEEPSEEK_API_KEY=
GPT_API_KEY=
DEEPSEEK_MODEL=deepseek-v4-flash
```

`DEEPSEEK_API_KEY` is preferred. `GPT_API_KEY` is accepted as a fallback when the same key is used.

## Why Rules Still Exist

Rules are kept as a fallback and regression baseline. They are not the primary intelligence layer.

The multi-agent reasoning path is the AI workflow in `workflows/ai.py`.
