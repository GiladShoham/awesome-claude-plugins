---
name: aws-expert
description: Use when working with core AWS services outside the serverless and IaC specialist skills — EC2, S3, VPC/networking, IAM policies, RDS, ECS, CloudWatch, Secrets Manager — via the AWS CLI/console/boto3. Triggers - "launch an EC2 instance", "S3 bucket policy", "create a VPC", "IAM role/policy", "RDS setup", "ECS service", "CloudWatch alarm". For CloudFormation templates use aws-cloudformation; for Lambda/API-Gateway serverless code use aws-serverless; for architecture design + cost optimization use aws-solution-architect.
author: PCL Team
license: Apache-2.0
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(aws:*)
  - Glob
  - Grep
metadata:
  version: 1.0.0
  category: cloud
  tags:
    - aws
    - cloud
    - infrastructure
    - devops
  requirements:
    aws-cli: ">=2.0"
---

# AWS Expert

Expert-level operation of core AWS services via the AWS CLI, console, and boto3: compute, storage, databases, networking, security/identity, and monitoring. Design and manage scalable, reliable, and cost-effective infrastructure following AWS Well-Architected Framework principles.

## When to use / decision

Use this skill as the **non-serverless, non-IaC fallback** for hands-on work with core AWS services. Route elsewhere when a specialist fits better:

| If the task is about… | Use |
| --- | --- |
| CloudFormation templates / IaC | `aws-cloudformation` |
| Lambda / API Gateway serverless code | `aws-serverless` |
| Architecture design + cost optimization | `aws-solution-architect` |
| EC2, S3, VPC, IAM, RDS, ECS, CloudWatch, Secrets Manager (CLI/console/boto3) | **this skill** |

## Reference index

Load the reference for the service you're working with:

| Reference | Covers |
| --- | --- |
| [references/compute.md](references/compute.md) | EC2, Lambda, ECS |
| [references/storage.md](references/storage.md) | S3, EBS |
| [references/database.md](references/database.md) | RDS, DynamoDB |
| [references/networking.md](references/networking.md) | VPC, subnets, route tables, security groups, ELB |
| [references/security.md](references/security.md) | IAM users/roles/policies, Secrets Manager |
| [references/monitoring.md](references/monitoring.md) | CloudWatch metrics, alarms, logs |
| [references/best-practices.md](references/best-practices.md) | Best practices, Well-Architected Framework, general approach |

Always design AWS infrastructure that is secure, reliable, performant, and cost-effective.
