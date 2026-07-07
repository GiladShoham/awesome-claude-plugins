# Networking

## VPC (Virtual Private Cloud)

```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16

# Create subnets
aws ec2 create-subnet \
    --vpc-id vpc-1234567890abcdef0 \
    --cidr-block 10.0.1.0/24 \
    --availability-zone us-east-1a

aws ec2 create-subnet \
    --vpc-id vpc-1234567890abcdef0 \
    --cidr-block 10.0.2.0/24 \
    --availability-zone us-east-1b

# Create internet gateway
aws ec2 create-internet-gateway
aws ec2 attach-internet-gateway \
    --vpc-id vpc-1234567890abcdef0 \
    --internet-gateway-id igw-1234567890abcdef0

# Create route table
aws ec2 create-route-table --vpc-id vpc-1234567890abcdef0
aws ec2 create-route \
    --route-table-id rtb-1234567890abcdef0 \
    --destination-cidr-block 0.0.0.0/0 \
    --gateway-id igw-1234567890abcdef0

# Associate route table with subnet
aws ec2 associate-route-table \
    --subnet-id subnet-1234567890abcdef0 \
    --route-table-id rtb-1234567890abcdef0

# Create security group
aws ec2 create-security-group \
    --group-name web-sg \
    --description "Web server security group" \
    --vpc-id vpc-1234567890abcdef0

# Add inbound rules
aws ec2 authorize-security-group-ingress \
    --group-id sg-1234567890abcdef0 \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-id sg-1234567890abcdef0 \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0
```

## ELB (Elastic Load Balancing)

```bash
# Create Application Load Balancer
aws elbv2 create-load-balancer \
    --name my-alb \
    --subnets subnet-12345 subnet-67890 \
    --security-groups sg-12345 \
    --scheme internet-facing \
    --type application \
    --ip-address-type ipv4

# Create target group
aws elbv2 create-target-group \
    --name my-targets \
    --protocol HTTP \
    --port 80 \
    --vpc-id vpc-12345 \
    --health-check-protocol HTTP \
    --health-check-path /health \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3

# Register targets
aws elbv2 register-targets \
    --target-group-arn arn:aws:elasticloadbalancing:... \
    --targets Id=i-12345 Id=i-67890

# Create listener
aws elbv2 create-listener \
    --load-balancer-arn arn:aws:elasticloadbalancing:... \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...
```
