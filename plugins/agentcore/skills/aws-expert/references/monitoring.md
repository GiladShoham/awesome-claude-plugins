# Monitoring and Logging

## CloudWatch

```bash
# Put metric data
aws cloudwatch put-metric-data \
    --namespace MyApp \
    --metric-name RequestCount \
    --value 100 \
    --timestamp $(date -u +"%Y-%m-%dT%H:%M:%S.000Z")

# Create alarm
aws cloudwatch put-metric-alarm \
    --alarm-name high-cpu \
    --alarm-description "Alert when CPU exceeds 80%" \
    --metric-name CPUUtilization \
    --namespace AWS/EC2 \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:my-topic \
    --dimensions Name=InstanceId,Value=i-12345

# Query logs
aws logs filter-log-events \
    --log-group-name /aws/lambda/my-function \
    --start-time $(date -d '1 hour ago' +%s)000 \
    --filter-pattern "ERROR"

# Create log group
aws logs create-log-group --log-group-name /aws/my-app

# Set retention
aws logs put-retention-policy \
    --log-group-name /aws/my-app \
    --retention-in-days 30
```
