# Database Services

## RDS (Relational Database Service)

```bash
# Create DB instance
aws rds create-db-instance \
    --db-instance-identifier mydb \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 16 \
    --master-username admin \
    --master-user-password MySecurePassword123 \
    --allocated-storage 20 \
    --storage-type gp3 \
    --vpc-security-group-ids sg-0123456789abcdef0 \
    --db-subnet-group-name my-subnet-group \
    --backup-retention-period 7 \
    --preferred-backup-window "03:00-04:00" \
    --preferred-maintenance-window "mon:04:00-mon:05:00" \
    --multi-az \
    --storage-encrypted \
    --enable-cloudwatch-logs-exports '["postgresql"]'

# Create read replica
aws rds create-db-instance-read-replica \
    --db-instance-identifier mydb-replica \
    --source-db-instance-identifier mydb \
    --db-instance-class db.t3.micro

# Create snapshot
aws rds create-db-snapshot \
    --db-instance-identifier mydb \
    --db-snapshot-identifier mydb-snapshot-$(date +%Y%m%d)

# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier mydb-restored \
    --db-snapshot-identifier mydb-snapshot-20240119
```

## DynamoDB

```python
import boto3

dynamodb = boto3.resource('dynamodb')

# Create table
table = dynamodb.create_table(
    TableName='Users',
    KeySchema=[
        {'AttributeName': 'userId', 'KeyType': 'HASH'},  # Partition key
        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}  # Sort key
    ],
    AttributeDefinitions=[
        {'AttributeName': 'userId', 'AttributeType': 'S'},
        {'AttributeName': 'timestamp', 'AttributeType': 'N'},
        {'AttributeName': 'email', 'AttributeType': 'S'}
    ],
    GlobalSecondaryIndexes=[
        {
            'IndexName': 'EmailIndex',
            'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
            'Projection': {'ProjectionType': 'ALL'}
            # On-demand GSIs inherit the table's billing mode; do NOT set
            # ProvisionedThroughput here when BillingMode='PAY_PER_REQUEST'
            # (mixing them raises ValidationException).
        }
    ],
    BillingMode='PAY_PER_REQUEST'  # Or PROVISIONED
)

# Put item
table = dynamodb.Table('Users')
table.put_item(
    Item={
        'userId': 'user123',
        'timestamp': 1234567890,
        'name': 'Alice',
        'email': 'alice@example.com'
    }
)

# Get item
response = table.get_item(Key={'userId': 'user123', 'timestamp': 1234567890})
item = response.get('Item')

# Query
response = table.query(
    KeyConditionExpression='userId = :uid',
    ExpressionAttributeValues={':uid': 'user123'}
)

# Scan (avoid in production - use query instead)
response = table.scan(
    FilterExpression='email = :email',
    ExpressionAttributeValues={':email': 'alice@example.com'}
)
```
