# Compute Services

## EC2 (Elastic Compute Cloud)

```bash
# Launch EC2 instance
aws ec2 run-instances \
    --image-id resolve:ssm:/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
    --instance-type t3.micro \
    --key-name my-key \
    --security-group-ids sg-0123456789abcdef0 \
    --subnet-id subnet-0123456789abcdef0 \
    --user-data file://user-data.sh \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=WebServer}]'

# List instances
aws ec2 describe-instances \
    --filters "Name=tag:Environment,Values=production" \
    --query 'Reservations[*].Instances[*].[InstanceId,State.Name,PrivateIpAddress]' \
    --output table

# Start/Stop instances
aws ec2 start-instances --instance-ids i-1234567890abcdef0
aws ec2 stop-instances --instance-ids i-1234567890abcdef0

# Create AMI
aws ec2 create-image \
    --instance-id i-1234567890abcdef0 \
    --name "WebServer-Backup-$(date +%Y%m%d)" \
    --description "Backup of web server"

# User data script
#!/bin/bash
yum update -y
yum install -y docker
systemctl start docker
systemctl enable docker
docker run -d -p 80:80 nginx
```

## Lambda (Serverless Functions)

```python
# lambda_function.py
import json
import boto3

def lambda_handler(event, context):
    # Parse input
    body = json.loads(event.get('body', '{}'))
    name = body.get('name', 'World')

    # Process
    message = f"Hello, {name}!"

    # Return response
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'message': message})
    }
```

```bash
# Create Lambda function
aws lambda create-function \
    --function-name my-function \
    --runtime python3.12 \
    --role arn:aws:iam::123456789012:role/lambda-role \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://function.zip \
    --timeout 30 \
    --memory-size 256 \
    --environment Variables={ENV=production,DB_HOST=mydb.example.com}

# Invoke Lambda
aws lambda invoke \
    --function-name my-function \
    --payload '{"name": "Alice"}' \
    response.json

# Update function code
aws lambda update-function-code \
    --function-name my-function \
    --zip-file fileb://function.zip
```

## ECS (Elastic Container Service)

```json
// task-definition.json
{
  "family": "web-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "web",
      "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/web-app:latest",
      "portMappings": [
        {
          "containerPort": 80,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENV", "value": "production"},
        {"name": "PORT", "value": "80"}
      ],
      "secrets": [
        {
          "name": "DB_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:db-password"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/web-app",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

```bash
# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create ECS service
aws ecs create-service \
    --cluster my-cluster \
    --service-name web-app \
    --task-definition web-app:1 \
    --desired-count 3 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}" \
    --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=web,containerPort=80"

# Update service
aws ecs update-service \
    --cluster my-cluster \
    --service web-app \
    --desired-count 5
```
