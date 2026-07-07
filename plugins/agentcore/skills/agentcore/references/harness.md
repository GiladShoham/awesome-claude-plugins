# Harness Reference

A harness is a fully managed AgentCore agent defined by configuration — model + tools + skills + memory + execution limits. No agent code, no container build. GA since June 2026 (`CreateHarness`/`UpdateHarness`/`InvokeHarness`). All commands below verified against CLI 0.22.0.

## Files

In a CLI project, each harness is:

```
agentcore/agentcore.json    →  "harnesses": [{ "name": "<n>", "path": "app/<n>" }]
app/<n>/harness.json        →  full harness spec
app/<n>/system-prompt.md    →  system prompt text
```

`harness.json` (ground truth, CLI 0.22.0):

```json
{
  "name": "myharness",
  "model": {
    "provider": "bedrock",
    "modelId": "global.anthropic.claude-sonnet-4-6"
  },
  "tools": [
    {
      "type": "remote_mcp",
      "name": "my_mcp",
      "config": { "remoteMcp": { "url": "https://mcp.example.com/mcp" } }
    }
  ],
  "skills": [
    { "path": "/abs/or/relative/skill-dir" }
  ],
  "memory": { "mode": "disabled" }
}
```

## Create / add

```bash
# New project whose default resource is a harness
agentcore create --name <harness> --project-name <proj> --defaults

# Add a harness to an existing project
agentcore add harness --name <n> \
  --system-prompt "You are ..." \
  --model-provider bedrock --model-id global.anthropic.claude-sonnet-4-6 \
  --allowed-tools "*" \
  --env KEY=VALUE \
  --max-iterations 50 --max-tokens 200000 --timeout 900
```

Selected flags (full list: `agentcore add harness --help`):

| Flag | Purpose |
|---|---|
| `--model-provider` | `bedrock`, `open_ai`, `gemini`, `lite_llm` (lite_llm: `--api-base`, `--additional-params`) |
| `--api-key-arn` | Secrets Manager ARN for non-Bedrock providers |
| `--tools` | Comma-separated: `agentcore_browser`, `agentcore_code_interpreter`, `remote_mcp`, `agentcore_gateway` |
| `--mcp-name` / `--mcp-url` / `--mcp-headers` | Required when `--tools` includes `remote_mcp` |
| `--gateway-arn` + `--gateway-outbound-auth` | Required when `--tools` includes `agentcore_gateway` |
| `--allowed-tools` | Allow-list of tool names, or `"*"` |
| `--memory-mode` | `disabled` (default), `managed`, `existing` (`--memory-name`/`--memory-arn`) |
| `--memory-strategies` | `SEMANTIC,SUMMARIZATION,USER_PREFERENCE,EPISODIC` (managed mode) |
| `--session-storage <path>` | Persistent session filesystem mount |
| `--efs-access-point` / `--s3-access-point` | BYO filesystem mounts `<arn>:<mountPath>` (VPC mode, max 2 each) |
| `--env KEY=VALUE` | Environment variables (repeatable) |
| `--truncation-strategy` | `sliding_window`, `summarization`, `none` |
| `--authorizer-type` | `AWS_IAM` or `CUSTOM_JWT` (+ `--discovery-url`, `--allowed-clients`, …) |
| `--container <uri-or-Dockerfile>` | Custom container image for the harness |
| `--with-invoke-script` | Generate a standalone Python invoke script |

## Skills

Skills are standard skill directories (SKILL.md with YAML frontmatter + scripts/references). Four sources:

```bash
agentcore add skill --harness <n> --path <local-skill-dir>
agentcore add skill --harness <n> --s3 s3://bucket/path
agentcore add skill --harness <n> --git https://github.com/org/repo [--git-path sub/dir] [--credential <name>] [--username <u>]
agentcore add skill --harness <n> --aws-skills [paths]   # AWS-curated catalog; omit paths for all
```

Skills mounted on a harness load at invocation time — update a skill without redeploying the agent. Code agents get the same sources via `skills/fetcher.py` in the generated app (s3/git skills download to a temp cache at runtime; the runtime working dir is read-only).

## Tools

```bash
agentcore add tool --harness <n> --type remote_mcp --name <t> --url <mcp-url>
agentcore add tool --harness <n> --type agentcore_browser|agentcore_code_interpreter --name <t>
agentcore add tool --harness <n> --type agentcore_gateway --gateway <project-gateway-name> [--outbound-auth awsIam|none|oauth]
agentcore add tool --harness <n> --type inline_function --name <t> --description "<shown to model>" --input-schema @schema.json
```

Built-in `shell` (bash) and `file_operations` (view/create/edit) are available in every session unless restricted by `allowedTools`.

**Secure MCP headers** — reference a Token Vault credential provider instead of a plain secret; the `${arn:...}` resolves to the key at invoke time (better than a raw token in `--mcp-headers`):

```bash
agentcore add tool --harness <n> --type remote_mcp --name exa --url https://mcp.exa.ai/mcp \
  --header 'x-api-key=${arn:aws:bedrock-agentcore:<region>:<acct>:token-vault/default/apikeycredentialprovider/<key>}'
```

**Gateway OAuth** — `--outbound-auth oauth` maps to `config.agentCoreGateway.outboundAuth.oauth` in `harness.json`, which needs `credentialProviderName` + `scopes`.

### allowedTools patterns

`allowedTools` scopes which tools the LLM may select during `InvokeHarness` (omit = all allowed). Patterns:

| Pattern | Matches |
|---|---|
| `*` | all tools |
| `shell` | builtin by name |
| `file_*` | builtin glob (`file_operations`, `file_read`) |
| `@builtin` / `@builtin/<name>` | all / one builtin |
| `@server` / `@server/tool` | all / one tool from an MCP server |
| `@server/glob` / `@*/tool` | glob within / across servers |

**Does not restrict `InvokeAgentRuntimeCommand`** — see `security-iam.md`.

## Export to code

When the config ceases to be enough (custom tool logic, middleware, custom loop):

```bash
agentcore export harness --name <n>                    # in-project harness
agentcore export harness --arn <arn>                   # harness created elsewhere (e.g., AWS Console)
  [--target-agent-name <name>] [--build CodeZip|Container]
```

Generates a Strands Python runtime agent under `app/<name>Agent/` mirroring the harness's model, tools, skills, memory, limits, and mounts. **Always read `app/<agent>/EXPORT_NOTES.md` before deploying** — it lists what the exporter could not automate. Then `agentcore deploy`; the exported agent deploys as a normal runtime. Exported code can also self-host anywhere with Python 3.12+ (Lambda, ECS, EKS, on-prem).

This is the supported path for Console-created harnesses — the pre-GA "harness-managed runtimes cannot be updated" dead end no longer applies.

## HITL / approvals

Human-in-the-loop no longer requires custom infrastructure:

- **Inline functions** (`inline_function` tool) — the primary HITL pattern. The tool schema executes client-side, not on the harness VM: when the agent calls it, the invocation pauses and returns the call to your code. In CLI mode the stream ends with `stopReason: "tool_use"`; you compute the result and resume with a follow-up invoke that sends **both** the assistant `toolUse` message and your `toolResult` (the harness does not persist a partial turn). Use for approvals or calling internal APIs.
- **Gateway elicitation pass-through** — an MCP tool behind a gateway can request user input mid-execution (form mode: structured confirm; URL mode: e.g. OAuth consent). Requires gateway MCP sessions.
- **Step Functions integration** — wrap `InvokeHarness` in a workflow with human-approval, error-handling, or conditional steps.

## Invoke

```bash
agentcore invoke --harness <name> "prompt"                    # deployed harness
agentcore invoke --harness-arn <arn> --region <r> "prompt"    # any harness by ARN, no project needed
agentcore invoke --runtime <name> "prompt"                    # deployed code runtime
agentcore dev "prompt"                                        # local run (code agents)
```

Harness invocations accept per-call overrides (`--model-id`, `--system-prompt`, `--skills`, `--allowed-tools`, …) — useful for testing config changes before deploying them.

**If `agentcore invoke --harness` fails with `fetch failed`** (Node fetch only tries the first DNS record of the data-plane host; unreachable from some networks), use the boto3 fallback — it falls back across all records:

```bash
uv run --with 'boto3>=1.43' scripts/invoke_harness.py --arn <harness-arn> --prompt "test"
```

`invoke_harness` (boto3 `bedrock-agentcore`) takes `harnessArn`, `runtimeSessionId`, `messages`, and returns a Converse-style event `stream`.
