# Deployment Patterns

## SAM Local Development Pattern

Local testing and debugging with SAM CLI.

**When to use**: Local development and testing, debugging Lambda functions, testing API Gateway locally

```bash
# Install SAM CLI
pip install aws-sam-cli

# Initialize new project
sam init --runtime nodejs22.x --name my-api

# Build the project
sam build

# Run locally
sam local start-api

# Invoke single function
sam local invoke GetItemFunction --event events/get.json

# Local debugging (Node.js with VS Code)
sam local invoke --debug-port 5858 GetItemFunction

# Deploy
sam deploy --guided
```

```json
// events/get.json (test event)
{
  "pathParameters": {
    "id": "123"
  },
  "httpMethod": "GET",
  "path": "/items/123"
}
```

```json
// .vscode/launch.json (for debugging)
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Attach to SAM CLI",
      "type": "node",
      "request": "attach",
      "address": "localhost",
      "port": 5858,
      "localRoot": "${workspaceRoot}/src",
      "remoteRoot": "/var/task/src",
      "protocol": "inspector"
    }
  ]
}
```

### Commands

- `sam build`: Build Lambda deployment packages
- `sam local start-api`: Start local API Gateway
- `sam local invoke`: Invoke single function
- `sam deploy`: Deploy to AWS
- `sam logs`: Tail CloudWatch logs

## CDK Serverless Pattern

Infrastructure as code with AWS CDK.

**When to use**: Complex infrastructure beyond Lambda, prefer programming languages over YAML, need reusable constructs

```typescript
// lib/api-stack.ts
import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export class ApiStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // DynamoDB Table
    const table = new dynamodb.Table(this, 'ItemsTable', {
      partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For dev only
    });

    // Lambda Function
    const getItemFn = new lambda.Function(this, 'GetItemFunction', {
      runtime: lambda.Runtime.NODEJS_22_X,
      handler: 'get.handler',
      code: lambda.Code.fromAsset('src/handlers'),
      environment: {
        TABLE_NAME: table.tableName,
      },
      memorySize: 256,
      timeout: cdk.Duration.seconds(30),
    });

    // Grant permissions
    table.grantReadData(getItemFn);

    // API Gateway
    const api = new apigateway.RestApi(this, 'ItemsApi', {
      restApiName: 'Items Service',
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
      },
    });

    const items = api.root.addResource('items');
    const item = items.addResource('{id}');

    item.addMethod('GET', new apigateway.LambdaIntegration(getItemFn));

    // Output API URL
    new cdk.CfnOutput(this, 'ApiUrl', {
      value: api.url,
    });
  }
}
```

```bash
# CDK commands
npm install -g aws-cdk
cdk init app --language typescript
cdk synth    # Generate CloudFormation
cdk diff     # Show changes
cdk deploy   # Deploy to AWS
```
