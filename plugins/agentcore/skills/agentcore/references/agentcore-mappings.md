# AgentCore Mapping Rules

Translate AI assistant artifacts into AgentCore resources. Verified against `agentcore` CLI 0.22.0.

## Core Concepts

A **harness** is a fully managed, declaratively configured agent (see `harness.md`). A **runtime** is a deployed code agent (Strands-based Python by default). Harness-first: prefer harnesses; generate code only for custom logic.

| Source artifact | AgentCore target | Location |
|---|---|---|
| `.agent.md` (persona + body), simple | Harness | `agentcore.json → harnesses[]` + `app/<name>/harness.json` + `system-prompt.md` |
| `.agent.md` whose body references an existing bundled script (`.github/scripts/*.{sh,py}`) | Runtime agent | `agentcore.json → runtimes[]` + `app/<name>/main.py` |
| Repo-level instruction/rule file (`copilot-instructions.md`, `.cursorrules`, `.cursor/rules`, `CLAUDE.md`, ...) | Harness (content → system prompt) | `harnesses[]` + `app/<name>/harness.json` + `system-prompt.md` — promoted so ambient instructions aren't dropped; prune if redundant with a real agent |
| Skill (SKILL.md dir) | Harness `skills[]` (path/s3/git) or code agent `skills/` dir | `harness.json → skills[]` |
| MCP server config | Harness `remote_mcp` tool, or Gateway target | `harness.json → tools[]` / `agentCoreGateways[]` |
| Secret env vars | Identity credential (or Secrets Manager ARN reference) | `credentials[]` |
| Memory/learnings | Managed memory | harness `memory` block / `memories[]` |

## Project creation

```bash
agentcore create --project-name <name> --no-agent --skip-git
```

> **Important — `agentcore create` makes a nested `./<project-name>/` scaffold** (verified 0.22.0); it does not initialize in place. Copy the pre-generated `agentcore.json`, `aws-targets.json`, and `app/` into the scaffold after creating it.

Console-created harnesses are no longer a dead end: `agentcore export harness --arn <arn>` converts one into a CLI-managed Strands runtime (see `harness.md`).

## Runtime entrypoint pattern (Strands)

Code agents follow the CLI 0.22.0 template: session-cached `Agent` (LRU-bounded per `session_id`), streaming entrypoint:

```python
from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model

app = BedrockAgentCoreApp()

SYSTEM_PROMPT = "..."  # Flattened from persona + body

@app.entrypoint
async def invoke(payload, context):
    agent = get_or_create_agent(getattr(context, "session_id", "default-session"))
    async for event in agent.stream_async(payload.get("prompt", "")):
        yield event

if __name__ == "__main__":
    app.run()
```

Streaming (`yield`) is the default and works with `agentcore invoke`/`dev` — the old non-streaming workaround is obsolete.

Dependencies (`pyproject.toml`): `strands-agents >= 1.15.0`, `bedrock-agentcore >= 1.9.1`, `botocore[crt] >= 1.35.0`, `mcp >= 1.19.0`, `aws-opentelemetry-distro`.

Model default: `global.anthropic.claude-sonnet-4-5-20250929-v1:0` (code agents) / `global.anthropic.claude-sonnet-4-6` (harnesses). Fallback if Anthropic access is not enabled: `amazon.nova-lite-v1:0`.

## Command validation baseline

| Purpose | Command |
|---|---|
| Create project | `agentcore create --project-name <name> --no-agent --skip-git` |
| Add harness | `agentcore add harness --name <n> --system-prompt "<text>" [--tools ...] [--env K=V]` |
| Add skill to harness | `agentcore add skill --harness <n> --path <dir>` (or `--s3`/`--git`/`--aws-skills`) |
| Add tool to harness | `agentcore add tool --harness <n> --type remote_mcp --name <t> --url <url>` |
| Add code agent | `agentcore add agent --name <n> --language Python --framework Strands --model-provider Bedrock --build CodeZip --memory none` |
| Add API-key credential | `agentcore add credential --type api-key --name <name> --api-key "$VALUE"` |
| Add Gateway | `agentcore add gateway --name <gateway>` |
| Add MCP Gateway target | `agentcore add gateway-target --name <target> --type mcp-server --endpoint <mcp-url> --gateway <gateway>` |
| Export harness to code | `agentcore export harness --name <n> \| --arn <arn>` |
| Validate / deploy / invoke | `agentcore validate` / `agentcore deploy` / `agentcore invoke --harness <n> "test"` (code agents: `--runtime <n>`) |

**Important:** resources pre-populated in `agentcore.json` must not also be `add`-ed — "already exists". Edit the JSON (schema authority: `agentcore/.llm-context/` types) or use `add` for new resources only.

**Naming constraints** (CLI-enforced):
- Harness/agent/runtime names: alphanumeric + underscores, start with a letter, max 48 chars. Convert dots/hyphens to underscores.
- Gateway names: alphanumeric + hyphens, max 100 chars. No underscores.
- Project names: alphanumeric only, start with a letter, max 23 chars.
- Runtime `envVars` in `agentcore.json`: array of `{"name","value"}` objects, not a dict. Harness env vars: object map in `harness.json`.

Raw AWS CLI fallback (validated namespaces):

| Purpose | AWS CLI operation |
|---|---|
| Create/update/get/list/delete runtime | `aws bedrock-agentcore-control {create,update,get,list,delete}-agent-runtime(s)` |
| Invoke runtime | `aws bedrock-agentcore invoke-agent-runtime` |
| Memory / gateway / credential providers | `aws bedrock-agentcore-control create-memory`, `create-gateway`, `create-oauth2-credential-provider`, `create-api-key-credential-provider` |
| Registry | `create-registry-record`, `submit-registry-record-for-approval`, `update-registry-record-status` |

## Agent mapping

### Persona and instructions → system prompt

Flatten persona (role, identity, communication style, principles) + body into one coherent prompt:
- Harness target → `app/<name>/system-prompt.md`
- Code target → `SYSTEM_PROMPT` in `main.py`, mirrored in `runtime-metadata.json` for review

```text
Input (.agent.md)                          Output
  ## Persona                                 system-prompt.md /
  - role: CVE verification tool       →      SYSTEM_PROMPT =
  - principles: [...]                        "You are a CVE verification tool..."
  ## Instructions (workflow)                 + numbered principles + workflow
```

### Tools → harness tools / runtime requirements

| Source tool | Harness target | Code-runtime target |
|---|---|---|
| `read` / `search` / `file` | built-in `file_operations` (allowed-tools) | record `file_operations` in metadata |
| `execute` / `shell` / `bash` | built-in `shell` (allowed-tools) | record `shell` in metadata |
| `browser` / `web` | `--tools agentcore_browser` | AgentCore Browser SDK |
| `code_interpreter` | `--tools agentcore_code_interpreter` | Code Interpreter SDK |
| MCP tool reference | `remote_mcp` tool or `agentcore_gateway` | gateway-wired MCP client |
| `*` / all | `--allowed-tools "*"` — flag MANUAL for review | MANUAL |

### Handoffs → multi-agent project

Each handoff target becomes its own harness (or runtime) in the same project. Include handoff instructions in the primary agent's system prompt and list the relationship in `migration-report.md`.

## Skill mapping

Skills keep their standard layout (`SKILL.md` + scripts/references/assets).

- **Harness target (preferred):** `agentcore add skill --harness <n> --path <skill-dir>` → `harness.json → skills[]`. Also `--s3`/`--git --git-path`/`--aws-skills`. Updating a mounted skill does not require redeploying the agent.
- **Code target:** copy declared skills into `app/<agent>/skills/<name>/`; the generated app loads them (s3/git sources resolve through `skills/fetcher.py` at runtime).

Only skills declared in the agent's `skills:` frontmatter are attached. No declaration → no skills; flag in the report.

## MCP server mapping

### Remote MCP (HTTP/SSE/streamable)

- Single-agent use → harness tool: `agentcore add tool --harness <n> --type remote_mcp --name <t> --url <url>`
- Shared across agents, or needs auth/policy/observability → Gateway:

```bash
agentcore add gateway --name <server>-gateway
agentcore add gateway-target --name <server> --type mcp-server --endpoint <mcp-url> --gateway <server>-gateway
```

Gateways also support: HTTP passthrough targets (front any HTTP endpoint / external MCP / A2A), web-search connector (`--type connector --connector web-search`), inference targets, Lambda, OpenAPI, Smithy, API Gateway. Gateway MCP sessions add elicitation, sampling, progress/logging notifications, and SSE streaming.

### Stdio MCP → manual conversion

Stdio configs (`command` + `args`) still cannot be attached directly. Mark `MANUAL` with these options:

1. Deploy the server as a remote streamable-HTTP endpoint (e.g., host it on AgentCore Runtime with `--protocol MCP`), then attach as `remote_mcp` or a gateway target.
2. Replace with an equivalent built-in tool or gateway connector (e.g., web-search).

Preserve original command/args in `runtime-metadata.json` for review.

### MCP auth → Identity

Env vars matching `KEY`, `SECRET`, `TOKEN`, `PASSWORD`, `PASSCODE`, `CREDENTIAL`, `AUTH`, `USERCODE` are secrets:

```bash
agentcore add credential --type api-key --name <credential-name> --api-key "$SECRET_VALUE"
```

If the secret already lives in AWS Secrets Manager, reference its ARN in the credential provider instead of copying the value. Non-secret env vars → runtime `envVars` / harness `--env`.

Automatic secret-vs-config routing applies only to MCP-server `env` blocks (that is what the scan inventories); agent-level env is not auto-inventoried and must be routed manually.

## Hook mapping

| Source hook | AgentCore equivalent | Implementation |
|---|---|---|
| `sessionStart` / `sessionEnd` | Exec scripts | Generate `exec-scripts/{pre,post}-invoke.sh`; run with `agentcore exec` around the invocation |
| `errorOccurred` / `PostToolUseFailure` | Observability | CloudWatch/OTEL traces + logs; `agentcore logs`, `traces` |
| HITL gate ("Continue?") | Gateway elicitation (form mode) or Step Functions approval step | Route the gating tool through a gateway with MCP sessions, or wrap `InvokeHarness` in Step Functions; mark MANUAL only if neither fits |

## Memory mapping

| Source memory | AgentCore target | Config |
|---|---|---|
| Conversation history | Harness managed memory / short-term | `--memory-mode managed` or `add agent --memory shortTerm` |
| Agent learnings | Long-term strategies | `--memory-strategies SEMANTIC,SUMMARIZATION,USER_PREFERENCE,EPISODIC` |
| Feature state (tasks, progress) | Session storage / BYO mounts | `--session-storage /mnt/data/`, EFS/S3 access points |
| Constitution / governance | System prompt | Bake into system prompt |

Standalone memory resource: `agentcore add memory --name <n> --strategies ... --expiry 30`.

## Project file mapping

`agentcore.json` (CLI 0.22.0 — flat resource arrays):

```json
{
  "$schema": "https://schema.agentcore.aws.dev/v1/agentcore.json",
  "name": "migratedagents",
  "version": 1,
  "managedBy": "CDK",
  "tags": { "agentcore:created-by": "agentcore-migration-skill" },
  "runtimes": [
    {
      "name": "cve_verify",
      "build": "CodeZip",
      "codeLocation": "app/cve_verify/",
      "entrypoint": "main.py",
      "runtimeVersion": "PYTHON_3_12",
      "networkMode": "PUBLIC",
      "protocol": "HTTP",
      "envVars": [ { "name": "NEXUS_IQ_URL", "value": "https://iq.example.com" } ]
    }
  ],
  "harnesses": [ { "name": "helper_agent", "path": "app/helper_agent" } ],
  "memories": [],
  "knowledgeBases": [],
  "credentials": [],
  "evaluators": [],
  "onlineEvalConfigs": [],
  "agentCoreGateways": [],
  "policyEngines": [],
  "configBundles": [],
  "abTests": [],
  "datasets": [],
  "payments": []
}
```

Deployment targets (`aws-targets.json`) — array; `account` is the 12-digit ID string:

```json
[
  { "name": "default", "account": "<AWS_ACCOUNT_ID>", "region": "us-west-2" }
]
```

## Registry record mapping

Each migrated agent produces a Registry record manifest:

```json
{
  "name": "<agent-name>",
  "type": "AGENT",
  "description": "<from agent description>",
  "metadata": {
    "source_file": "<original path>",
    "migrated_from": "<source tool>",
    "migration_date": "<ISO timestamp>"
  }
}
```
