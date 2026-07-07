# Migration Workflow

Migrate AI assistant configurations (agents, skills, MCP servers, hooks, memory, prompts) from coding assistants to AgentCore. Scans 15 source formats, maps artifacts to AgentCore equivalents, and generates a deployable CDK-managed project.

**Harness-first principle:** an agent that is persona + skills + standard tools becomes a **harness** (declarative config — no code to maintain, skills swappable without redeploy). Generate a **code runtime** (Strands) only when the agent needs custom logic: bundled scripts, lifecycle hooks, custom tool implementations. If a harness later outgrows its config, `agentcore export harness` converts it to code.

## Preflight

```bash
python3 scripts/preflight_check.py
```

Fix all failures before Step 1 (each failure prints its install command). Requires `agentcore` CLI ≥ 0.22 and `uv`.

## Step 0 — Confirm Target

The migration always creates a **new CDK-managed AgentCore project**. Confirm:
- Target AWS region (`aws-targets.json` region must be an AgentCore region)
- `aws sts get-caller-identity` succeeds
- No conflicting CloudFormation stack (pattern: `AgentCore-<projectname>-default`)

Existing Console-created harnesses are not a blocker: leave them running, or pull one into this project with `agentcore export harness --arn <arn>`.

## Step 1 — Discover

```bash
python3 scripts/scan_configs.py --repo-root <path> --format json
```

Checks 15 source formats (see `source-formats.md`): GitHub Copilot, Claude Code, Cursor, Cline, Codex, Windsurf, Antigravity, Gemini CLI, Deep Agents, Dexto, Firebender, Kimi Code CLI, OpenCode, Warp, agentic-core.

Print a discovery summary:

```
╔═══════════════════════════════════════════════════╗
║          AgentCore Migration — Discovery           ║
╠═══════════════════════════════════════════════════╣
║  Agents found:      {N}                           ║
║  Skills found:      {M}                           ║
║  MCP servers:       {K}                           ║
║  Hooks:             {H}                           ║
║  Prompts:           {P}                           ║
║  Sources detected:  {list of tool names}          ║
╚═══════════════════════════════════════════════════╝
```

## Step 2 — Parse

Output `migration-inventory.json` with all parsed artifacts:

| Artifact type | Fields extracted |
|---|---|
| **Agent** | name, description, persona, system prompt, tools, handoffs, activation |
| **Skill** | name, description, body, scripts (paths), references (paths) |
| **MCP server** | name, URL/command, transport, env vars, auth config |
| **Hook** | event name, script path, backend type |
| **Memory** | type, path, content summary |
| **Prompt** | name, path, content |

## Step 3 — Map & Classify

Apply the rules in `agentcore-mappings.md`. First decision per agent — harness or code:

| Signal | Target |
|---|---|
| Persona/instructions + declared skills + builtin tools (read/search/execute/browser) | **Harness** |
| Remote MCP dependencies | **Harness** (`remote_mcp` tool or gateway) |
| Agent body references an existing bundled script (`.github/scripts/*.{sh,py}`) | **Code runtime** (the implemented classifier keys on this signal) |
| Handoffs to other agents | Each target is its own harness/runtime; note the relationship in the report |

> The automated classifier only routes to a code runtime on the bundled-script signal. Lifecycle hooks and custom tool code are manual-review considerations — noted for the human, not auto-detected.

Then map each artifact:

- **Agents → harness** — persona flattened into `system-prompt.md`; tools list → `--allowed-tools` + harness `tools[]`; env vars → `--env`
- **Agents → code runtime** (custom-logic cases) — flattened `SYSTEM_PROMPT` in `main.py` + `runtime-metadata.json` for review
- **Skills →** harness `skills[]` entries (`--path`, `--s3`, `--git`) or baked into the code agent's `skills/` dir
- **MCP servers →** harness `remote_mcp` tools, or gateway targets for shared/multi-agent use; stdio MCP see `agentcore-mappings.md`
- **Hooks →** exec scripts + `agentcore exec`; error hooks → Observability (automatic OTEL)
- **HITL gates →** gateway elicitation (form mode) or Step Functions approval step — no longer MANUAL-only
- **Memory →** harness `--memory-mode managed --memory-strategies ...` or a memory resource
- **Secrets →** Identity credentials (`agentcore add credential`) or existing Secrets Manager ARN references; non-secrets → `envVars`

Classify each mapping: `AUTO` (no review needed), `MANUAL` (needs human review), `SKIP` (no equivalent).

## Step 4 — Generate

```bash
python3 scripts/generate_project.py \
  --inventory migration-inventory.json \
  --output-dir ./agentcore-project \
  --region us-east-1
```

Output structure:

```
agentcore-project/
├── agentcore/
│   ├── agentcore.json        # harnesses[] + runtimes[] + credentials[] + gateways[]
│   ├── aws-targets.json      # [{"name","account","region"}]
│   └── cdk/                  # provided by the `agentcore create` scaffold (Step 6)
├── app/
│   ├── <harness-agent>/      # harness.json + system-prompt.md
│   └── <code-agent>/         # main.py, model/load.py, pyproject.toml, skills/, scripts/
├── registry/                 # Registry record manifests per agent
├── agentcore-commands.sh     # credential + skill + gateway + deploy commands
└── migration-report.md       # Summary + manual action items
```

Rules:
- Templates from `templates/`; conform to the schema in the project's `agentcore/.llm-context/` types
- Runtimes and harnesses are pre-populated in config — the commands script must NOT contain `add agent`/`add harness` for them (fails with "already exists"). `add skill` targeting a generated harness is fine (skills append).
- Only skills declared in an agent's `skills:` frontmatter are attached to that agent; agents without declarations get none — flag in the report
- Idempotent: output dir is cleaned before writing

## Step 5 — Report

Generate `migration-report.md`: summary table (counts by artifact type and status), per-agent detail (target: harness or runtime; what mapped, what skipped), manual action items (secrets values, gateway endpoints, custom deps), copy-paste deployment commands.

## Step 6 — Deploy

**Run `deployment-checklist.md` first** — the `[BLOCKER]` items (model access + form propagation, daily token quota, IAM confused-deputy, nested `create` scaffold) catch the failures that otherwise surface only after deploy. Then follow `migration-modes.md`. Short form (or just run `agentcore-commands.sh`, which contains exactly this):

```bash
cd <output-dir>
# create makes a NESTED ./<name>/ scaffold (with CDK deps installed) — copy generated files in
agentcore create --project-name <name> --no-agent --skip-git
cp agentcore/agentcore.json <name>/agentcore/agentcore.json
cp agentcore/aws-targets.json <name>/agentcore/aws-targets.json
cp -R app <name>/
cd <name>
agentcore add skill --harness <h> --path app/<h>/skills/<skill>   # per generated skill
agentcore validate
agentcore deploy --yes
agentcore invoke --harness <name> "test"   # or --runtime <name> for code agents
```

## Validation Checkpoints

| After Step | Validation | On failure |
|---|---|---|
| 1 — Discover | `migration-inventory.json` has >0 artifacts | Re-check repo paths / detection table |
| 2 — Parse | All artifacts have name + type | Skip malformed entries with warning |
| 3 — Map | No AUTO mapping references undefined targets | Reclassify as MANUAL |
| 4 — Generate | `agentcore.json`, `harness.json`, `runtime-metadata.json` valid JSON; `aws-targets.json` array with `account` | Compare against `templates/`, regenerate |
| 5 — Report | All MANUAL items listed; no secrets in generated files | Scan for secret patterns, move to Identity |
| 6 — Deploy | `agentcore validate` passes; cdk `node_modules` exists; stack creates | See error table in `migration-modes.md` |

## Error Handling

| Error | Action |
|---|---|
| No configs found | Print paths checked, halt |
| Unsupported format | Log as SKIP, continue |
| Script deps missing (code agents) | Add to pyproject/Dockerfile |
| Stdio MCP | Flag MANUAL — needs remote endpoint (see mappings) |
| Secret env vars | Flag for Identity |
| CLI not installed / < 0.22 | Print install/upgrade command, halt |
