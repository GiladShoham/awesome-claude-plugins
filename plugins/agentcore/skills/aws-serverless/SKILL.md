---
name: aws-serverless
description: "Use when implementing production serverless workloads on AWS —
  writing Lambda handler code, wiring API Gateway / DynamoDB Streams / SQS / SNS
  event-driven flows, SAM or CDK deployment, or fixing cold starts. Triggers:
  'write a Lambda function', 'SAM template', 'API Gateway + Lambda', 'SQS
  consumer', 'DynamoDB stream processor', 'cold start optimization'. For
  standalone CloudFormation authoring use aws-cloudformation; for architecture
  selection + cost design use aws-solution-architect."
source: vibeship-spawner-skills (Apache 2.0)
---

# AWS Serverless

Specialized skill for building production-ready serverless applications on AWS.
Covers Lambda functions, API Gateway, DynamoDB, SQS/SNS event-driven patterns,
SAM/CDK deployment, and cold start optimization.

## Principles

- Right-size memory and timeout (measure before optimizing)
- Minimize cold starts for latency-sensitive workloads
- Use SnapStart for Java 11+, Python 3.12+, .NET 8+ functions
- Prefer HTTP API over REST API for simple use cases
- Design for failure with DLQs and retries
- Keep deployment packages small
- Use environment variables for configuration
- Implement structured logging with correlation IDs

## When to use / pattern index

Match the task to a pattern, then open its reference file for full code.

| Task | Pattern | Reference |
|------|---------|-----------|
| Any Lambda function, API handler, event processor, scheduled task | Lambda Handler (Node + Python, error handling) | [references/lambda-handler.md](references/lambda-handler.md) |
| REST/HTTP API backed by Lambda; choosing HTTP vs REST API | API Gateway Integration (SAM template + handler, API comparison) | [references/api-gateway.md](references/api-gateway.md) |
| Decoupled async processing, batch consumers, DynamoDB change reactions | Event-Driven (SQS with partial-batch failure + DLQ, DynamoDB Streams) | [references/event-driven.md](references/event-driven.md) |
| Latency-sensitive / user-facing / high-traffic functions | Cold Start Optimization (package size, SnapStart, memory, provisioned concurrency, lazy init) | [references/cold-start.md](references/cold-start.md) |
| Local dev/testing; IaC with SAM or CDK | Deployment (SAM local + CDK stack) | [references/deployment.md](references/deployment.md) |
| Debugging production issues (INIT billing, timeouts, OOM, VPC cold start, event-loop hangs, payload limits, recursive invocation) | Sharp Edges | [references/sharp-edges.md](references/sharp-edges.md) |
| Reviewing serverless code for anti-patterns | Validation Checks (credentials, IAM, error handling, memory/timeout, DLQ, SDK imports) | [references/validation-checks.md](references/validation-checks.md) |

## Collaboration

### Delegation Triggers

- user needs GCP serverless -> gcp-cloud-run (Cloud Run for containers, Cloud Functions for events)
- user needs Azure serverless -> azure-functions (Azure Functions, Logic Apps)
- user needs database design -> postgres-wizard (RDS design, or use DynamoDB patterns)
- user needs authentication -> auth-specialist (Cognito, API Gateway authorizers)
- user needs complex workflows -> workflow-automation (Step Functions, EventBridge)
- user needs AI integration -> llm-architect (Lambda calling Bedrock or external LLMs)

## Limitations

- Use this skill only when the task clearly matches the scope described above.
- Do not treat the output as a substitute for environment-specific validation, testing, or expert review.
- Stop and ask for clarification if required inputs, permissions, safety boundaries, or success criteria are missing.
