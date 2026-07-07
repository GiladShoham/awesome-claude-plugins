# AWS Architecture Patterns for Startups

Reference guide for selecting the right AWS architecture pattern based on application requirements.

---

## Table of Contents

- [Pattern Selection Matrix](#pattern-selection-matrix)
- [Pattern 1: Serverless Web Application](#pattern-1-serverless-web-application)
- [Pattern 2: Event-Driven Microservices](#pattern-2-event-driven-microservices)
- [Pattern 3: Modern Three-Tier Application](#pattern-3-modern-three-tier-application)
- [Pattern 4: Real-Time Data Processing](#pattern-4-real-time-data-processing)
- [Pattern 5: GraphQL API Backend](#pattern-5-graphql-api-backend)
- [Pattern 6: Multi-Region High Availability](#pattern-6-multi-region-high-availability)

---

## Pattern Selection Matrix

| Pattern | Best For | Users | Monthly Cost | Complexity |
|---------|----------|-------|--------------|------------|
| Serverless Web | MVP, SaaS, mobile backend | <50K | $50-500 | Low |
| Event-Driven Microservices | Complex workflows, async processing | Any | $100-1000 | Medium |
| Three-Tier | Traditional web, e-commerce | 10K-500K | $300-2000 | Medium |
| Real-Time Data | Analytics, IoT, streaming | Any | $200-1500 | High |
| GraphQL Backend | Mobile apps, SPAs | <100K | $50-400 | Medium |
| Multi-Region HA | Global apps, DR requirements | >100K | 1.5-2x single | High |

---

## Pattern 1: Serverless Web Application

### Use Case
SaaS platforms, mobile backends, low-traffic websites, MVPs

### Architecture Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  CloudFront │────▶│     S3      │     │   Cognito   │
│    (CDN)    │     │  (Static)   │     │   (Auth)    │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
┌─────────────┐     ┌─────────────┐     ┌──────▼──────┐
│   Route 53  │────▶│ API Gateway │────▶│   Lambda    │
│    (DNS)    │     │   (REST)    │     │ (Functions) │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                        ┌──────▼──────┐
                                        │  DynamoDB   │
                                        │ (Database)  │
                                        └─────────────┘
```

### Service Stack

| Layer | Service | Configuration |
|-------|---------|---------------|
| Frontend | S3 + CloudFront | Static hosting with HTTPS |
| API | API Gateway + Lambda | REST endpoints with throttling |
| Database | DynamoDB | Pay-per-request billing |
| Auth | Cognito | User pools with MFA support |
| CI/CD | Amplify or CodePipeline | Automated deployments |

### CloudFormation Template

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  # API Function
  ApiFunction:
    Type: AWS::Serverless::Function
    Properties:
      Runtime: nodejs22.x
      Handler: index.handler
      MemorySize: 512
      Timeout: 10
      Events:
        Api:
          Type: Api
          Properties:
            Path: /{proxy+}
            Method: ANY

  # DynamoDB Table
  DataTable:
    Type: AWS::DynamoDB::Table
    Properties:
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: PK
          AttributeType: S
        - AttributeName: SK
          AttributeType: S
      KeySchema:
        - AttributeName: PK
          KeyType: HASH
        - AttributeName: SK
          KeyType: RANGE
```

### Cost Breakdown (10K users)

| Service | Monthly Cost |
|---------|-------------|
| Lambda | $5-20 |
| API Gateway | $10-30 |
| DynamoDB | $10-50 |
| CloudFront | $5-15 |
| S3 | $1-5 |
| Cognito | $0-50 |
| **Total** | **$31-170** |

### Pros and Cons

**Pros:**
- Zero server management
- Pay only for what you use
- Auto-scaling built-in
- Low operational overhead

**Cons:**
- Cold start latency (100-500ms)
- 15-minute Lambda execution limit
- Vendor lock-in

---

## Pattern 2: Event-Driven Microservices

### Use Case
Complex business workflows, asynchronous processing, decoupled systems

### Architecture Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Service   │────▶│ EventBridge │────▶│   Service   │
│      A      │     │  (Event Bus)│     │      B      │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │     SQS     │
                    │   (Queue)   │
                    └──────┬──────┘
                           │
┌─────────────┐     ┌──────▼──────┐     ┌─────────────┐
│    Step     │◀────│   Lambda    │────▶│  DynamoDB   │
│  Functions  │     │ (Processor) │     │  (Storage)  │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Service Stack

| Layer | Service | Purpose |
|-------|---------|---------|
| Events | EventBridge | Central event bus |
| Processing | Lambda or ECS Fargate | Event handlers |
| Queue | SQS | Dead letter queue for failures |
| Orchestration | Step Functions | Complex workflow state |
| Storage | DynamoDB, S3 | Persistent data |

### Event Schema Example

```json
{
  "source": "orders.service",
  "detail-type": "OrderCreated",
  "detail": {
    "orderId": "ord-12345",
    "customerId": "cust-67890",
    "items": [...],
    "total": 99.99,
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Cost Breakdown

| Service | Monthly Cost |
|---------|-------------|
| EventBridge | $1-10 |
| Lambda | $20-100 |
| SQS | $5-20 |
| Step Functions | $25-100 |
| DynamoDB | $20-100 |
| **Total** | **$71-330** |

### Pros and Cons

**Pros:**
- Loose coupling between services
- Independent scaling per service
- Failure isolation
- Easy to test individually

**Cons:**
- Distributed system complexity
- Eventual consistency
- Harder to debug

---

## Pattern 3: Modern Three-Tier Application

### Use Case
Traditional web apps, e-commerce, CMS, applications with complex queries

### Architecture Diagram

```
┌─────────────┐     ┌─────────────┐
│  CloudFront │────▶│     ALB     │
│    (CDN)    │     │ (Load Bal.) │
└─────────────┘     └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ ECS Fargate │
                    │ (Auto-scale)│
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
 ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
 │   Aurora    │    │ ElastiCache │    │     S3      │
 │ (Database)  │    │   (Redis)   │    │  (Storage)  │
 └─────────────┘    └─────────────┘    └─────────────┘
```

### Service Stack

| Layer | Service | Configuration |
|-------|---------|---------------|
| CDN | CloudFront | Edge caching, HTTPS |
| Load Balancer | ALB | Path-based routing, health checks |
| Compute | ECS Fargate | Container auto-scaling |
| Database | Aurora MySQL/PostgreSQL | Multi-AZ, auto-scaling |
| Cache | ElastiCache Redis | Session, query caching |
| Storage | S3 | Static assets, uploads |

### Terraform Example

```hcl
# ECS Service with Auto-scaling
resource "aws_ecs_service" "app" {
  name            = "app-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 2

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 100
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = 3000
  }
}

# Auto-scaling Policy
resource "aws_appautoscaling_target" "app" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}
```

### Cost Breakdown (50K users)

| Service | Monthly Cost |
|---------|-------------|
| ECS Fargate (2 tasks) | $100-200 |
| ALB | $25-50 |
| Aurora | $100-300 |
| ElastiCache | $50-100 |
| CloudFront | $20-50 |
| **Total** | **$295-700** |

---

## Pattern 4: Real-Time Data Processing

### Use Case
Analytics, IoT data ingestion, log processing, streaming data

### Architecture Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  IoT Core   │────▶│   Kinesis   │────▶│   Lambda    │
│  (Devices)  │     │  (Stream)   │     │ (Process)   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
┌─────────────┐     ┌─────────────┐     ┌──────▼──────┐
│  QuickSight │◀────│   Athena    │◀────│     S3      │
│   (Viz)     │     │  (Query)    │     │ (Data Lake) │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                        ┌──────▼──────┐
                                        │  CloudWatch │
                                        │  (Alerts)   │
                                        └─────────────┘
```

### Service Stack

| Layer | Service | Purpose |
|-------|---------|---------|
| Ingestion | Kinesis Data Streams | Real-time data capture |
| Processing | Lambda or Kinesis Analytics | Transform and analyze |
| Storage | S3 (data lake) | Long-term storage |
| Query | Athena | SQL queries on S3 |
| Visualization | QuickSight | Dashboards and reports |
| Alerting | CloudWatch + SNS | Threshold-based alerts |

### Kinesis Producer Example

```python
import boto3
import json

kinesis = boto3.client('kinesis')

def send_event(stream_name, data, partition_key):
    response = kinesis.put_record(
        StreamName=stream_name,
        Data=json.dumps(data),
        PartitionKey=partition_key
    )
    return response['SequenceNumber']

# Send sensor reading
send_event(
    'sensor-stream',
    {'sensor_id': 'temp-01', 'value': 23.5, 'unit': 'celsius'},
    'sensor-01'
)
```

### Cost Breakdown

| Service | Monthly Cost |
|---------|-------------|
| Kinesis (1 shard) | $15-30 |
| Lambda | $10-50 |
| S3 | $5-50 |
| Athena | $5-25 |
| QuickSight | $24+ |
| **Total** | **$59-179** |

---

## Pattern 5: GraphQL API Backend

### Use Case
Mobile apps, single-page applications, flexible data queries

### Architecture Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Mobile App │────▶│   AppSync   │────▶│   Lambda    │
│   or SPA    │     │  (GraphQL)  │     │ (Resolvers) │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │  DynamoDB   │
                    │  (Direct)   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Cognito   │
                    │   (Auth)    │
                    └─────────────┘
```

### AppSync Schema Example

```graphql
type Query {
  getUser(id: ID!): User
  listPosts(limit: Int, nextToken: String): PostConnection
}

type Mutation {
  createPost(input: CreatePostInput!): Post
  updatePost(input: UpdatePostInput!): Post
}

type Subscription {
  onCreatePost: Post @aws_subscribe(mutations: ["createPost"])
}

type User {
  id: ID!
  email: String!
  posts: [Post]
}

type Post {
  id: ID!
  title: String!
  content: String!
  author: User!
  createdAt: AWSDateTime!
}
```

### Cost Breakdown

| Service | Monthly Cost |
|---------|-------------|
| AppSync | $4-40 |
| Lambda | $5-30 |
| DynamoDB | $10-50 |
| Cognito | $0-50 |
| **Total** | **$19-170** |

---

## Pattern 6: Multi-Region High Availability

### Use Case
Global applications, disaster recovery, data sovereignty compliance

### Architecture Diagram

```
                    ┌─────────────┐
                    │  Route 53   │
                    │(Geo routing)│
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                                 │
   ┌──────▼──────┐                   ┌──────▼──────┐
   │ us-east-1   │                   │ eu-west-1   │
   │ CloudFront  │                   │ CloudFront  │
   └──────┬──────┘                   └──────┬──────┘
          │                                 │
   ┌──────▼──────┐                   ┌──────▼──────┐
   │ ECS/Lambda  │                   │ ECS/Lambda  │
   └──────┬──────┘                   └──────┬──────┘
          │                                 │
   ┌──────▼──────┐◀── Replication ──▶┌──────▼──────┐
   │  DynamoDB   │                   │  DynamoDB   │
   │Global Table │                   │Global Table │
   └─────────────┘                   └─────────────┘
```

### Service Stack

| Component | Service | Configuration |
|-----------|---------|---------------|
| DNS | Route 53 | Geolocation or latency routing |
| CDN | CloudFront | Multiple origins per region |
| Compute | Lambda or ECS | Deployed in each region |
| Database | DynamoDB Global Tables | Automatic replication |
| Storage | S3 CRR | Cross-region replication |

### Route 53 Failover Policy

```yaml
# Primary record
HealthCheck:
  Type: AWS::Route53::HealthCheck
  Properties:
    HealthCheckConfig:
      Port: 443
      Type: HTTPS
      ResourcePath: /health
      FullyQualifiedDomainName: api-us-east-1.example.com

RecordSetPrimary:
  Type: AWS::Route53::RecordSet
  Properties:
    Name: api.example.com
    Type: A
    SetIdentifier: primary
    Failover: PRIMARY
    HealthCheckId: !Ref HealthCheck
    AliasTarget:
      DNSName: !GetAtt USEast1ALB.DNSName
      HostedZoneId: !GetAtt USEast1ALB.CanonicalHostedZoneID
```

### Cost Considerations

| Factor | Impact |
|--------|--------|
| Compute | 2x (each region) |
| Database | 25% premium for global tables |
| Data Transfer | Cross-region replication costs |
| Route 53 | Health checks + geo queries |
| **Total** | **1.5-2x single region** |

---

## Pattern Comparison Summary

### Latency

| Pattern | Typical Latency |
|---------|-----------------|
| Serverless | 50-200ms (cold: 500ms+) |
| Three-Tier | 20-100ms |
| GraphQL | 30-150ms |
| Multi-Region | <50ms (regional) |

### Scaling Characteristics

| Pattern | Scale Limit | Scale Speed |
|---------|-------------|-------------|
| Serverless | 1000 concurrent/function | Instant |
| Three-Tier | Instance limits | Minutes |
| Event-Driven | Unlimited | Instant |
| Multi-Region | Regional limits | Instant |

### Operational Complexity

| Pattern | Setup | Maintenance | Debugging |
|---------|-------|-------------|-----------|
| Serverless | Low | Low | Medium |
| Three-Tier | Medium | Medium | Low |
| Event-Driven | High | Medium | High |
| Multi-Region | High | High | High |
