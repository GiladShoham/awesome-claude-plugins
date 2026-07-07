# Security and Identity

## IAM (Identity and Access Management)

```json
// policy.json - S3 read-only policy
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-bucket",
        "arn:aws:s3:::my-bucket/*"
      ]
    }
  ]
}
```

```bash
# Create IAM user
aws iam create-user --user-name alice

# Create access key
aws iam create-access-key --user-name alice

# Create policy
aws iam create-policy \
    --policy-name S3ReadOnlyPolicy \
    --policy-document file://policy.json

# Attach policy to user
aws iam attach-user-policy \
    --user-name alice \
    --policy-arn arn:aws:iam::123456789012:policy/S3ReadOnlyPolicy

# Create role
aws iam create-role \
    --role-name lambda-role \
    --assume-role-policy-document file://trust-policy.json

# Attach policy to role
aws iam attach-role-policy \
    --role-name lambda-role \
    --policy-arn arn:aws:iam::aws:policy/AWSLambdaBasicExecutionRole
```

## Secrets Manager

```bash
# Store secret
aws secretsmanager create-secret \
    --name db-password \
    --description "Database password" \
    --secret-string '{"username":"admin","password":"MySecurePassword123"}'

# Retrieve secret
aws secretsmanager get-secret-value --secret-id db-password

# Rotate secret
aws secretsmanager rotate-secret \
    --secret-id db-password \
    --rotation-lambda-arn arn:aws:lambda:...
```
