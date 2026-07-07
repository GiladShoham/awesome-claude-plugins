# Event-Driven Patterns

## Event-Driven SQS Pattern

Lambda triggered by SQS for reliable async processing.

**When to use**: Decoupled, asynchronous processing; need retry logic and DLQ; processing messages in batches

```yaml
# template.yaml
Resources:
  ProcessorFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: src/handlers/processor.handler
      Events:
        SQSEvent:
          Type: SQS
          Properties:
            Queue: !GetAtt ProcessingQueue.Arn
            BatchSize: 10
            FunctionResponseTypes:
              - ReportBatchItemFailures  # Partial batch failure handling

  ProcessingQueue:
    Type: AWS::SQS::Queue
    Properties:
      VisibilityTimeout: 180  # 6x Lambda timeout
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt DeadLetterQueue.Arn
        maxReceiveCount: 3

  DeadLetterQueue:
    Type: AWS::SQS::Queue
    Properties:
      MessageRetentionPeriod: 1209600  # 14 days
```

```javascript
// src/handlers/processor.js
exports.handler = async (event) => {
  const batchItemFailures = [];

  for (const record of event.Records) {
    try {
      const body = JSON.parse(record.body);
      await processMessage(body);
    } catch (error) {
      console.error(`Failed to process message ${record.messageId}:`, error);
      // Report this item as failed (will be retried)
      batchItemFailures.push({
        itemIdentifier: record.messageId
      });
    }
  }

  // Return failed items for retry
  return { batchItemFailures };
};

async function processMessage(message) {
  // Your processing logic
  console.log('Processing:', message);

  // Simulate work
  await saveToDatabase(message);
}
```

```python
# Python version
import json
import logging

logger = logging.getLogger()

def handler(event, context):
    batch_item_failures = []

    for record in event['Records']:
        try:
            body = json.loads(record['body'])
            process_message(body)
        except Exception as e:
            logger.error(f"Failed to process {record['messageId']}: {e}")
            batch_item_failures.append({
                'itemIdentifier': record['messageId']
            })

    return {'batchItemFailures': batch_item_failures}
```

### Best practices

- Set VisibilityTimeout to 6x Lambda timeout (the example above uses `180 = 6x30`). Also account for `MaximumBatchingWindowInSeconds` if you configure a batching window — the effective time a message is in flight is `(function timeout x retries within batch) + batching window`, so size VisibilityTimeout above that total.
- Use ReportBatchItemFailures for partial batch failure
- Always configure a DLQ for poison messages; `maxReceiveCount` around 5 is a common starting point (3 above is conservative) — too low sends transient failures to the DLQ prematurely
- Process messages idempotently

## DynamoDB Streams Pattern

React to DynamoDB table changes with Lambda.

**When to use**: Real-time reactions to data changes; cross-region replication; audit logging, notifications

```yaml
# template.yaml
Resources:
  ItemsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: items
      AttributeDefinitions:
        - AttributeName: id
          AttributeType: S
      KeySchema:
        - AttributeName: id
          KeyType: HASH
      BillingMode: PAY_PER_REQUEST
      StreamSpecification:
        StreamViewType: NEW_AND_OLD_IMAGES

  StreamProcessorFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: src/handlers/stream.handler
      Events:
        Stream:
          Type: DynamoDB
          Properties:
            Stream: !GetAtt ItemsTable.StreamArn
            StartingPosition: TRIM_HORIZON
            BatchSize: 100
            MaximumRetryAttempts: 3
            DestinationConfig:
              OnFailure:
                Destination: !GetAtt StreamDLQ.Arn

  StreamDLQ:
    Type: AWS::SQS::Queue
```

```javascript
// src/handlers/stream.js
exports.handler = async (event) => {
  for (const record of event.Records) {
    const eventName = record.eventName;  // INSERT, MODIFY, REMOVE

    // Unmarshall DynamoDB format to plain JS objects
    const newImage = record.dynamodb.NewImage
      ? unmarshall(record.dynamodb.NewImage)
      : null;
    const oldImage = record.dynamodb.OldImage
      ? unmarshall(record.dynamodb.OldImage)
      : null;

    console.log(`${eventName}: `, { newImage, oldImage });

    switch (eventName) {
      case 'INSERT':
        await handleInsert(newImage);
        break;
      case 'MODIFY':
        await handleModify(oldImage, newImage);
        break;
      case 'REMOVE':
        await handleRemove(oldImage);
        break;
    }
  }
};

// Use AWS SDK v3 unmarshall
const { unmarshall } = require('@aws-sdk/util-dynamodb');
```

### Stream view types

- KEYS_ONLY: Only key attributes
- NEW_IMAGE: After modification
- OLD_IMAGE: Before modification
- NEW_AND_OLD_IMAGES: Both before and after
