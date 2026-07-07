# AgentCore Skill

General skill for Amazon Bedrock AgentCore: deploy and operate harnesses and runtime agents, and migrate AI assistant configurations from 15 coding assistants (GitHub Copilot, Claude Code, Cursor, Cline, Codex, Windsurf, Antigravity, Gemini CLI, Deep Agents, Dexto, Firebender, Kimi Code CLI, OpenCode, Warp, agentic-core).

**Harness-first:** agents that are persona + skills + standard tools deploy as declarative harnesses (no code). Only agents with custom logic get generated Strands code. Verified against `agentcore` CLI 0.22.0 (July 2026).

The plugin also bundles companion AWS skills — `aws-cloudformation`, `aws-expert`, `aws-serverless`, `aws-solution-architect` — so a coding agent has broader AWS context when building or migrating agents.

## Quick Start

### Prerequisites

```bash
python3 scripts/preflight_check.py
```

Needs: Python ≥3.10, Node ≥20, uv, AWS CLI + credentials, `agentcore` CLI ≥0.22.

### Migration

```bash
# 1. Scan a repository for AI assistant configs
python3 scripts/scan_configs.py --repo-root <path> --format json

# 2. Generate the AgentCore project (harnesses + code runtimes)
python3 scripts/generate_project.py \
  --inventory migration-inventory.json \
  --output-dir ./agentcore-project \
  --region us-east-1

# 3. Deploy (or run the generated agentcore-commands.sh)
cd agentcore-project
./agentcore-commands.sh
```

## Structure

This repo is a Claude Code **plugin** that bundles the `agentcore` skill plus a set of companion AWS skills (all auto-discovered from `skills/`).

```
├── .claude-plugin/
│   ├── plugin.json              # Plugin manifest
│   └── marketplace.json         # Marketplace manifest (installable via /plugin)
├── .mcp.json                    # Bundled MCP server (Bedrock AgentCore) — auto-connects when the plugin is enabled
├── skills/
│   ├── aws-cloudformation/      # CloudFormation authoring
│   ├── aws-expert/              # General AWS guidance
│   ├── aws-serverless/          # Serverless (Lambda/API GW) patterns
│   ├── aws-solution-architect/  # Architecture guidance
│   └── agentcore/               # The AgentCore migration skill
│       ├── SKILL.md             # Entry point
│       ├── scripts/             # preflight_check, scan_configs, generate_project, invoke_harness
│       ├── references/          # harness.md, migration.md, security-iam.md, deployment-checklist.md, ...
│       ├── evals/evals.json     # Regression scenarios (self-test)
│       └── assets/              # poc-cve-verify/ (+ VERIFIED.md), iam-policies/
└── LICENSE                      # MIT
```

## Installing

**As a plugin (Claude Code marketplace):**

```
/plugin marketplace add LeonMelamud/agentcore-toolkit
/plugin install agentcore@agentcore-skills
```

Hosted (public) at `github.com/LeonMelamud/agentcore-toolkit`. Also installable via the skills.sh CLI: `npx skills add LeonMelamud/agentcore-toolkit`.

**As a personal or project skill (copy the bundle):**

```bash
cp -r skills/agentcore ~/.claude/skills/agentcore        # personal
cp -r skills/agentcore .claude/skills/agentcore          # project (or .github/skills/ for Copilot)
```

## Connecting to AWS (required)

Nothing here works without AWS credentials. Every skill drives the AWS CLI / boto3 / the `agentcore` CLI, and the bundled MCP server (below) makes real Bedrock AgentCore API calls — all of them fail with no configured AWS identity. Installing the plugin does **not** connect you to AWS; do this once after install:

**1. Configure credentials** (any one):

```bash
aws configure sso                 # recommended for orgs / SSO
aws configure                     # static access keys
export AWS_ACCESS_KEY_ID=...  AWS_SECRET_ACCESS_KEY=...  AWS_REGION=us-east-1
# …or run on an EC2/ECS/Lambda role — the SDK picks it up automatically
```

**2. Verify** the whole toolchain is reachable:

```bash
python3 skills/agentcore/scripts/preflight_check.py
```

Checks Python ≥3.10, Node ≥20, `uv`, AWS CLI + **live credentials** (prints your account id), the `agentcore` CLI ≥0.22, and Bedrock AgentCore access. Fix anything it flags before running a workflow.

**3. Enable Bedrock model access** in the target account/region (Bedrock console → Model access). Without it, invokes fail with `ModelNotAccessibleException`; a 0 daily-token quota surfaces as `ThrottlingException` (see the skill's error table).

### Bundled MCP server

The plugin ships `.mcp.json` declaring the official [Amazon Bedrock AgentCore MCP server](https://awslabs.github.io/mcp/servers/amazon-bedrock-agentcore-mcp-server) (`awslabs.amazon-bedrock-agentcore-mcp-server`). When the plugin is enabled, Claude Code launches it via `uvx` and it shows up as `bedrock-agentcore-mcp MCP · connected`, giving the agent direct AgentCore runtime / memory / gateway / identity API tools alongside the skills.

- **Requires `uv`** (the server runs through `uvx`; no manual install) and the **AWS credentials from step 1** — it is boto3-backed, so it connects but every tool call fails until AWS is configured.
- After installing/enabling, run `/reload-plugins` (or restart Claude Code) to load it, then approve it at the per-server trust prompt.
- Region resolves from your AWS config; override with `AWS_REGION` in the `env` block of `.mcp.json` if needed.

## License

The plugin and the `agentcore`, `aws-cloudformation`, and `aws-solution-architect` skills are MIT — see [LICENSE](LICENSE). The `aws-expert` and `aws-serverless` companion skills are third-party components licensed under Apache-2.0 — see [LICENSE-APACHE](LICENSE-APACHE) and [NOTICE](NOTICE).
