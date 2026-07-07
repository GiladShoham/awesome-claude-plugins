# Migration Modes Reference

The migration creates a **new CDK-managed AgentCore project**. Two target modes per agent (chosen in mapping — see `migration.md` Step 3):

| Mode | What gets generated | Deploys as |
|------|---------------------|-----------|
| **Harness** (default) | `app/<name>/harness.json` + `system-prompt.md` | Managed harness — no code, no build |
| **Code runtime** | `app/<name>/main.py` + `model/` + `pyproject.toml` | CodeZip (default) or Container |

## Build Types (code runtimes only)

| Build | When to use | Docker needed? |
|-------|-------------|----------------|
| **CodeZip** (default) | Pure Python agents with pip dependencies | No |
| **Container** | System packages, non-Python tools, custom OS deps | Yes |

## Generator CLI Flags

```
python3 scripts/generate_project.py \
  --inventory <path>          # migration-inventory.json (required)
  --output-dir <path>         # Output directory (default: ./agentcore-project)
  --region <region>           # AWS region (default: us-west-2)
```

## Deploy Workflow

Verified against CLI 0.22.0: `agentcore create` does NOT initialize in place — it creates a **nested `./<project-name>/` scaffold** (agentcore/, cdk/ with node_modules, .llm-context/, AGENTS.md). Copy the generated files into it.

```bash
cd agentcore-project

# 1. Create the scaffold (nested dir; installs CDK deps unless --skip-install)
agentcore create --project-name <project> --no-agent --skip-git

# 2. Copy generated config + apps into the scaffold
cp agentcore/agentcore.json <project>/agentcore/agentcore.json
cp agentcore/aws-targets.json <project>/agentcore/aws-targets.json
cp -R app <project>/
cd <project>

# 3. Skills, credentials, gateways (or run ../agentcore-commands.sh)
agentcore add skill --harness <n> --path app/<n>/skills/<skill>
agentcore add credential --type api-key --name <name> --api-key "$SECRET"
agentcore add gateway --name <gateway>
agentcore add gateway-target --name <target> --type mcp-server --endpoint <url> --gateway <gateway>

# 4. Validate & deploy
agentcore validate
agentcore deploy --yes

# 5. Test
agentcore invoke --harness <name> "test"   # or --runtime <name> for code agents
```

> If deploy fails with `tsc: not found`, CDK deps are missing: `cd agentcore/cdk && npm install`.

## What `agentcore deploy` Creates

CloudFormation stack `AgentCore-<projectname>-default`:

| Resource | Purpose |
|---|---|
| Harnesses | Managed harness resources |
| Agent Runtimes | CodeZip or Container runtimes |
| IAM Roles | Service roles for execution |
| ECR Repository + CodeBuild | Container builds only |

## aws-targets.json Format

**JSON array**, `account` (not `accountId`) is the 12-digit account ID string:

```json
[
  { "name": "default", "account": "123456789012", "region": "us-east-1" }
]
```

## Validation

| Check | Expected |
|---|---|
| `agentcore.json` | ≥1 entry across `harnesses[]` + `runtimes[]`; conforms to `.llm-context/` types |
| `harness.json` per harness | name, model, tools[], skills[], memory block |
| `aws-targets.json` | JSON **array** with `account` field |
| `agentcore/cdk/node_modules` | Exists |
| `agentcore validate` | Passes |
| Code-agent dirs | `main.py` + `pyproject.toml` each |

## Teardown

```bash
aws cloudformation delete-stack --stack-name AgentCore-<projectname>-default --region <region>
aws cloudformation wait stack-delete-complete --stack-name AgentCore-<projectname>-default --region <region>
```

## Error Handling

| Error | Cause | Fix |
|---|---|---|
| `tsc: not found` during deploy | CDK deps not installed | `cd agentcore/cdk && npm install` |
| `agentcore validate` fails | Config drift | Restore backed-up `agentcore.json`; check `.llm-context/` types |
| "already exists" from `add` | Resource already declared in config | Edit JSON directly |
| Stack already exists | Previous deployment | `aws cloudformation delete-stack ...` |
| IAM permission denied | Missing permissions | Need CloudFormation, ECR, IAM, Bedrock AgentCore permissions |
| `ThrottlingException: Too many tokens per day` | Bedrock daily token quota — **may be 0 by default** even after model access is granted | `aws service-quotas list-service-quotas --service-code bedrock --query "Quotas[?contains(QuotaName,'tokens per day')]"`; request an increase via Service Quotas (AWS-approved, not instant) |
| `ModelNotAccessibleException` / "use case details have not been submitted" | Model access not enabled | Enable via console Model access, or CLI: `aws bedrock put-use-case-for-model-access` (Anthropic form; `intendedUsers` is a numeric string, `industryOption` from a fixed enum e.g. "Technology") + `create-foundation-model-agreement`; propagation takes ~15 min. Or switch to `amazon.nova-lite-v1:0` |
| `agentcore create` outputs nothing | Invalid project name | Alphanumeric only, start with letter, max 23 chars |
| Docker Hub rate limits (Container) | CodeBuild pulls throttled | Use ECR Public Gallery base images |
| Harness invoke `fetch failed` (~10s) | Node fetch only tries the first DNS record of the data-plane host; that IP unreachable from your network | Check per-IP: `curl --resolve bedrock-agentcore.<region>.amazonaws.com:443:<ip> https://...`; fix DNS/egress, retry from another network, or invoke the harness's underlying runtime with `aws bedrock-agentcore invoke-agent-runtime` |

## Model Selection

| Model | Notes |
|-------|-------|
| `global.anthropic.claude-sonnet-4-6` | Harness default (CLI 0.22.0) |
| `global.anthropic.claude-sonnet-4-5-20250929-v1:0` | Code-agent template default |
| `amazon.nova-lite-v1:0` / `amazon.nova-pro-v1:0` | Fallback if Anthropic model access is not enabled; low default daily quotas |

More providers: harness `--model-provider open_ai | gemini | lite_llm` (LiteLLM/Bedrock Mantle expose OpenAI GPT models on Bedrock).
