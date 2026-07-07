# Storage Services

## S3 (Simple Storage Service)

```bash
# Create bucket
aws s3 mb s3://my-bucket --region us-east-1

# Upload file
aws s3 cp file.txt s3://my-bucket/
aws s3 cp folder/ s3://my-bucket/folder/ --recursive

# Download file
aws s3 cp s3://my-bucket/file.txt .
aws s3 sync s3://my-bucket/folder/ ./folder/

# List objects
aws s3 ls s3://my-bucket/
aws s3 ls s3://my-bucket/folder/ --recursive

# Delete objects
aws s3 rm s3://my-bucket/file.txt
aws s3 rm s3://my-bucket/folder/ --recursive

# Set bucket policy
aws s3api put-bucket-policy \
    --bucket my-bucket \
    --policy file://bucket-policy.json

# Enable versioning
aws s3api put-bucket-versioning \
    --bucket my-bucket \
    --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
    --bucket my-bucket \
    --server-side-encryption-configuration '{
      "Rules": [{
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        }
      }]
    }'

# Lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
    --bucket my-bucket \
    --lifecycle-configuration file://lifecycle.json
```

```json
// lifecycle.json
{
  "Rules": [
    {
      "Id": "Move to Glacier after 90 days",
      "Status": "Enabled",
      "Prefix": "logs/",
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 365
      }
    }
  ]
}
```

## EBS (Elastic Block Store)

```bash
# Create volume
aws ec2 create-volume \
    --volume-type gp3 \
    --size 100 \
    --availability-zone us-east-1a \
    --iops 3000 \
    --throughput 125

# Attach volume
aws ec2 attach-volume \
    --volume-id vol-1234567890abcdef0 \
    --instance-id i-1234567890abcdef0 \
    --device /dev/sdf

# Create snapshot
aws ec2 create-snapshot \
    --volume-id vol-1234567890abcdef0 \
    --description "Backup $(date +%Y%m%d)"

# Copy snapshot to another region
aws ec2 copy-snapshot \
    --source-region us-east-1 \
    --source-snapshot-id snap-1234567890abcdef0 \
    --region us-west-2
```
