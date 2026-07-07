# Pre-Deploy Checklist

Gate before `agentcore deploy`. `[BLOCKER]` items cause deploy failures, silent misconfiguration, or an agent that deploys but can't produce output. Every item maps to a gotcha verified against CLI 0.22.0 (some the hard way — see `assets/poc-cve-verify/VERIFIED.md`).

## Model & access

- [ ] **[BLOCKER]** Model access enabled for the target model in this account/region. Anthropic models need the use-case form: `aws bedrock put-use-case-for-model-access` (**`intendedUsers` is a numeric string** e.g. `"0"`; `industryOption` is a fixed enum e.g. `"Technology"`) + `create-foundation-model-agreement`. Propagation to the inference plane takes **~15 min**. Without it: `ResourceNotFoundException: use case details have not been submitted`.
- [ ] **[BLOCKER]** Daily token quota is **> 0**. New/restricted accounts often default to **0 tokens/day** even after access is granted → every invoke throttles with `Too many tokens per day`. Check: `aws service-quotas list-service-quotas --service-code bedrock --query "Quotas[?contains(QuotaName,'tokens per day')]"`. The newest Claude quotas are **not self-service adjustable** — raising them needs an AWS Support case.
- [ ] Model ID matches the access form / region: `global.anthropic.claude-sonnet-4-5-20250929-v1:0` (global CRIS), `us.anthropic...` (geographic), or plain `anthropic...` (in-region). If unsure of the current CLI default, run `agentcore create --dry-run` rather than trusting a hard-coded value.

## IAM & security

- [ ] **[BLOCKER]** Execution-role trust policy has `aws:SourceAccount` + `aws:SourceArn` conditions (confused-deputy). See `security-iam.md`.
- [ ] **[BLOCKER]** `bedrock:InvokeModel*` scoped to exact model ARN(s), not `Resource: *`. Global CRIS needs all three ARNs.
- [ ] Replaced the CLI-generated wildcard policies with the scoped versions in `assets/iam-policies/`.
- [ ] Execution-role name contains `BedrockAgentCore`, or a custom `iam:PassRole` policy exists (managed policy scopes PassRole to `*BedrockAgentCore*`).

## Project & config

- [ ] `agentcore validate` passes.
- [ ] `agentcore.json` conforms to `agentcore/.llm-context/` types; harnesses in `harnesses[]`, code agents in `runtimes[]`.
- [ ] `aws-targets.json` is a JSON **array** with `account` (12-digit string) — not `accountId`.
- [ ] Names within limits: harness/agent alphanumeric+underscore ≤48, project alphanumeric ≤23, gateway alphanumeric+hyphen.
- [ ] `agentcore create` scaffold populated: it creates a **nested `./<project>/`** dir — generated `agentcore.json`/`aws-targets.json`/`app/` copied in; `agentcore/cdk/node_modules` present (`npm install` if `tsc: not found`).
- [ ] Secrets → Identity credentials (or Secrets Manager ARN reference), not generated files. Non-secrets → `envVars`.
- [ ] Stdio MCP servers resolved (published as remote endpoints) or explicitly flagged MANUAL in the report.

## After deploy

- [ ] Stack `AgentCore-<project>-default` reached CREATE/UPDATE_COMPLETE.
- [ ] Test invoke with a simple prompt. If `agentcore invoke --harness` returns `fetch failed` (~10s), it's the Node-fetch DNS quirk — use `scripts/invoke_harness.py` (boto3, falls back across DNS records). See `harness.md`.
- [ ] Teardown known: `aws cloudformation delete-stack --stack-name AgentCore-<project>-default`.
