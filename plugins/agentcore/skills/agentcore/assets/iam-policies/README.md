# IAM policy templates

Least-privilege starting points for a migrated agent's execution role. Directly appliable (no comment keys). Replace `<ACCOUNT_ID>`, `<REGION>`, and the model ARNs before use. Rationale and rules: `../../references/security-iam.md`.

| File | Attach as |
|---|---|
| `agentcore-runtime-execution-role-trust.json` | Role **trust policy**. Has `aws:SourceAccount` + `aws:SourceArn` (confused-deputy protection) — required. |
| `agentcore-runtime-execution-role-permissions.json` | Role **permissions**. Model invocation scoped to exact ARNs; global CRIS needs all three ARNs (inference profile + in-region FM + region-less global FM). |

These **replace** the wildcard (`Resource: *`) policies the `agentcore` CLI generates — do not ship the generated ones to production.

```bash
aws iam create-role --role-name my-agent-exec \
  --assume-role-policy-document file://agentcore-runtime-execution-role-trust.json
aws iam put-role-policy --role-name my-agent-exec --policy-name agent-least-priv \
  --policy-document file://agentcore-runtime-execution-role-permissions.json
```
