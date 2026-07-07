# Best Practices & Well-Architected Framework

## Best Practices

### 1. Use IAM Roles (Not Access Keys)
```bash
# For EC2 instances
aws ec2 run-instances \
    --iam-instance-profile Name=my-role \
    ...

# For Lambda
aws lambda create-function \
    --role arn:aws:iam::123456789012:role/lambda-role \
    ...
```

### 2. Enable MFA
```json
# Require MFA for sensitive operations
{
  "Effect": "Deny",
  "Action": "*",
  "Resource": "*",
  "Condition": {
    "BoolIfExists": {"aws:MultiFactorAuthPresent": "false"}
  }
}
```

### 3. Use VPC and Security Groups
```bash
# Launch resources in private subnets
# Use NAT Gateway for outbound internet access
# Implement least-privilege security groups
```

### 4. Enable Encryption
```bash
# S3 encryption
--server-side-encryption AES256

# EBS encryption
--encrypted

# RDS encryption
--storage-encrypted
```

### 5. Implement Backup Strategy
```bash
# S3 versioning
# RDS automated backups
# EBS snapshots
# Cross-region replication
```

### 6. Cost Optimization
```bash
# Use Reserved Instances for predictable workloads
# Use Spot Instances for flexible workloads
# Right-size instances
# Use S3 lifecycle policies
# Enable S3 Intelligent-Tiering
# Delete unused resources
```

### 7. Tag Resources
```bash
# Consistent tagging strategy
--tags Key=Environment,Value=production \
       Key=Project,Value=webapp \
       Key=CostCenter,Value=engineering
```

## Well-Architected Framework

### 1. Operational Excellence
- Infrastructure as Code (CloudFormation, Terraform)
- Automated deployments (CodePipeline)
- Monitoring and logging (CloudWatch)

### 2. Security
- Least privilege IAM policies
- Encryption at rest and in transit
- Network isolation (VPC, Security Groups)
- Regular security audits

### 3. Reliability
- Multi-AZ deployments
- Auto Scaling
- Health checks and monitoring
- Automated backups

### 4. Performance Efficiency
- Right-size resources
- Use caching (ElastiCache, CloudFront)
- Database read replicas
- Async processing (SQS, Lambda)

### 5. Cost Optimization
- Reserved Instances for steady state
- Spot Instances for batch jobs
- S3 lifecycle policies
- Regular cost reviews

### 6. Sustainability
- Use managed services
- Optimize workload efficiency
- Right-size resources
- Use renewable energy regions

## Approach

When working with AWS:

1. **Plan Architecture**: Multi-AZ, fault-tolerant design
2. **Security First**: IAM roles, encryption, least privilege
3. **Cost Awareness**: Right-size, use Reserved/Spot instances
4. **Monitor Everything**: CloudWatch metrics, logs, alarms
5. **Automate**: Infrastructure as Code, CI/CD pipelines
6. **High Availability**: Multi-AZ, Auto Scaling, backups
7. **Test Disaster Recovery**: Regular backup testing
8. **Follow Well-Architected**: Use AWS best practices

Always design AWS infrastructure that is secure, reliable, performant, and cost-effective.
