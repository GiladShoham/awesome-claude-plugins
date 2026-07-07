# Validation Checks

## Hardcoded AWS Credentials

Severity: ERROR

AWS credentials must never be hardcoded.

Message: Hardcoded AWS access key detected. Use IAM roles or environment variables.

## AWS Secret Key in Source Code

Severity: ERROR

Secret keys should use Secrets Manager or environment variables.

Message: Hardcoded AWS secret key. Use IAM roles or Secrets Manager.

## Overly Permissive IAM Policy

Severity: WARNING

Avoid wildcard permissions in Lambda IAM roles.

Message: Overly permissive IAM policy. Use least privilege principle.

## Lambda Handler Without Error Handling

Severity: WARNING

Lambda handlers should have try/catch for graceful errors.

Message: Lambda handler without error handling. Add try/catch.

## Missing callbackWaitsForEmptyEventLoop

Severity: INFO

Node.js handlers should set callbackWaitsForEmptyEventLoop.

Message: Consider setting context.callbackWaitsForEmptyEventLoop = false

## Default Memory Configuration

Severity: INFO

Default 128MB may be too low for many workloads.

Message: Using default 128MB memory. Consider increasing for better performance.

## Low Timeout Configuration

Severity: WARNING

Very low timeout may cause unexpected failures.

Message: Timeout of 1-3 seconds may be too low. Increase if making external calls.

## No Dead Letter Queue Configuration

Severity: WARNING

Async functions should have DLQ for failed invocations.

Message: No DLQ configured. Add for async invocations.

## Importing Full AWS SDK v2

Severity: WARNING

Import specific clients from AWS SDK v3 for smaller packages.

Message: Importing full AWS SDK. Use modular SDK v3 imports for smaller packages.

## Hardcoded DynamoDB Table Name

Severity: WARNING

Table names should come from environment variables.

Message: Hardcoded table name. Use environment variable for portability.
