# Security & IAM

Least-privilege IAM for migrated agents. The `agentcore` CLI generates working-but-permissive policies (`Resource: *` on most actions) to get you deploying; **replace them with scoped policies before production**. Templates live in `assets/iam-policies/`.

## Execution role (Runtime / Harness)

Every deployed runtime/harness assumes an execution role. Two documents:

- **Trust policy** (`assets/iam-policies/agentcore-runtime-execution-role-trust.json`) — principal `bedrock-agentcore.amazonaws.com`, **with `aws:SourceAccount` + `aws:SourceArn` conditions**. These are required: without them another caller can induce the service to assume your role (confused-deputy). Non-negotiable for production.
- **Permissions policy** (`assets/iam-policies/agentcore-runtime-execution-role-permissions.json`) — model invocation scoped to exact model ARNs, workload identity, and observability scoped to the `bedrock-agentcore` log group / metric namespace.

## Rules

- **Scope `bedrock:InvokeModel*` to exact model ARNs** — never `Resource: *`. A wildcard grants every model, including the priciest.
- **Global cross-region inference (`global.*` model IDs) needs all three ARNs** — the inference profile in the source region, the in-region foundation-model ARN, and the **region-less** global FM ARN. Missing any one → `AccessDeniedException`.
- **Confused-deputy conditions on every service trust policy** — `aws:SourceAccount` + `aws:SourceArn` on both `bedrock-agentcore.amazonaws.com` and (if used) `bedrock.amazonaws.com`.
- **Prefer JWT workload identity for end-user agents** — `GetWorkloadAccessTokenForJWT` validates issuer/signature/expiry. Explicitly **Deny** `GetWorkloadAccessTokenForUserId` / `InvokeAgentRuntimeForUser` unless you truly need the unauthenticated user-id path (it accepts any opaque string).
- **Secrets never in code or generated files** — API keys → AgentCore Identity credentials, or reference an existing Secrets Manager ARN. See `agentcore-mappings.md`.
- **`allowedTools` is not a security boundary — `InvokeAgentRuntimeCommand` bypasses it.** The harness `allowedTools` allow-list only scopes LLM tool selection during `InvokeHarness`. `bedrock-agentcore:InvokeAgentRuntimeCommand` is a separate IAM action that executes commands (e.g. `shell`) directly, without passing through the LLM or its allow-list. To actually prevent direct command execution, **do not grant `bedrock-agentcore:InvokeAgentRuntimeCommand`** in your policies.
- **Run IAM Access Analyzer** on the final policies before deploy.

## `iam:PassRole` gotcha

The managed `BedrockAgentCoreFullAccess` policy scopes `iam:PassRole` to role names matching `*BedrockAgentCore*`. If your execution role is named otherwise, deploy silently fails to pass it — either include `BedrockAgentCore` in the role name or write a custom `iam:PassRole` policy for the exact ARN.
