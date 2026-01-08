# Deployment Guide - MySQL Upgrade Assessment Tool

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [AWS Setup](#aws-setup)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [First Run](#first-run)
6. [Advanced Deployment](#advanced-deployment)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required
- ✅ AWS Account with RDS MySQL 5.7 or Aurora MySQL 5.7 instances
- ✅ Python 3.8 or higher
- ✅ AWS CLI installed and configured
- ✅ Network access to your databases

### Optional
- ✅ IAM role (for EC2/Lambda deployment)
- ✅ VPN access (for private VPC databases)

---

## AWS Setup

### Step 1: Create IAM Policy

Create an IAM policy with the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RDSMetadataAccess",
      "Effect": "Allow",
      "Action": [
        "rds:DescribeDBClusters",
        "rds:DescribeDBInstances",
        "rds:DescribeDBClusterEndpoints"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SecretsManagerAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:ListSecrets",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:rds!*"
    }
  ]
}
```

Save as: `mysql-upgrade-assessment-policy.json`

### Step 2: Attach Policy to User/Role

**For IAM User:**
```bash
aws iam create-policy --policy-name MySQLUpgradeAssessment --policy-document file://mysql-upgrade-assessment-policy.json

aws iam attach-user-policy --user-name YOUR_USERNAME --policy-arn arn:aws:iam::ACCOUNT_ID:policy/MySQLUpgradeAssessment
```

**For IAM Role (EC2/Lambda):**
```bash
aws iam attach-role-policy --role-name YOUR_ROLE --policy-arn arn:aws:iam::ACCOUNT_ID:policy/MySQLUpgradeAssessment
```

### Step 3: Store Database Credentials in Secrets Manager

AWS RDS/Aurora automatically creates secrets when you enable rotation. If not already done:

```bash
aws secretsmanager create-secret \
    --name rds!cluster-YOUR-CLUSTER-ID \
    --description "Credentials for MySQL cluster" \
    --secret-string '{
        "username":"admin",
        "password":"YOUR_SECURE_PASSWORD"
    }' \
    --region us-east-2
```

### Step 4: Verify Network Access

**Security Group Configuration:**
- Allow inbound MySQL (port 3306) from your IP or security group
- For private VPC: Ensure VPN/bastion host connectivity

**Test connectivity:**
```bash
telnet your-database-endpoint.rds.amazonaws.com 3306
```

---

## Installation

### Method 1: Automated Setup (Recommended)

```bash
# Clone repository
git clone https://github.com/your-org/mysql-upgrade-assessment-tool.git
cd mysql-upgrade-assessment-tool

# Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# Activate virtual environment
source venv/bin/activate
```

### Method 2: Manual Setup

```bash
# Clone repository
git clone https://github.com/your-org/mysql-upgrade-assessment-tool.git
cd mysql-upgrade-assessment-tool

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
python -c "import mysql.connector, boto3; print('OK')"
```

---

## Configuration

### AWS Credentials

**Option 1: AWS CLI (Recommended)**
```bash
aws configure
# Enter: Access Key ID, Secret Access Key, Region, Output format
```

**Option 2: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-2"
```

**Option 3: IAM Role (EC2/Lambda)**
No configuration needed - automatically uses instance role

### Optional: Custom Configuration

Create `config/config.yaml`:

```yaml
aws:
  region: us-east-2
  profile: default  # Or your custom profile

database:
  connect_timeout: 30
  read_timeout: 300

report:
  output_dir: reports
  format: html
  include_summary: true

logging:
  level: INFO
  file: logs/assessment.log
```

---

## First Run

### Step 1: Discover Your Databases

```bash
./scripts/discover_clusters.sh
```

This will list all MySQL 5.7 instances in your account.

### Step 2: Run Assessment

```bash
source venv/bin/activate

# For Aurora cluster
python run_assessment.py --cluster my-aurora-cluster --region us-east-2

# For RDS instance
python run_assessment.py --cluster my-rds-instance --region us-east-1
```

### Step 3: View Report

```bash
# Open HTML report
open reports/upgrade_assessment.html  # macOS
xdg-open reports/upgrade_assessment.html  # Linux
start reports/upgrade_assessment.html  # Windows

# View text summary
cat reports/executive_summary.md
```

---

## Advanced Deployment

### EC2 Deployment

**1. Launch EC2 Instance**
- AMI: Amazon Linux 2 or Ubuntu 20.04+
- Instance Type: t3.micro or larger
- IAM Role: Attach policy from AWS Setup
- Security Group: Allow outbound HTTPS (443) and MySQL (3306)

**2. Install on EC2**
```bash
# SSH into instance
ssh -i your-key.pem ec2-user@your-instance-ip

# Install Python and Git
sudo yum update -y
sudo yum install python3 python3-pip git -y

# Clone and setup
git clone https://github.com/your-org/mysql-upgrade-assessment-tool.git
cd mysql-upgrade-assessment-tool
./scripts/setup.sh
source venv/bin/activate

# Run assessment
python run_assessment.py --cluster your-cluster --region us-east-2
```

### Lambda Deployment (Advanced)

**1. Package Code**
```bash
# Create deployment package
pip install -r requirements.txt -t package/
cp -r aurora_upgrade_checker.py run_assessment.py templates/ package/
cd package && zip -r ../lambda-deployment.zip . && cd ..
```

**2. Create Lambda Function**
```bash
aws lambda create-function \
    --function-name mysql-upgrade-assessment \
    --runtime python3.9 \
    --role arn:aws:iam::ACCOUNT_ID:role/YOUR_LAMBDA_ROLE \
    --handler run_assessment.lambda_handler \
    --zip-file fileb://lambda-deployment.zip \
    --timeout 900 \
    --memory-size 512
```

### Docker Deployment

**Dockerfile:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "run_assessment.py"]
```

**Build and Run:**
```bash
docker build -t mysql-upgrade-assessment .

docker run \
    -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
    -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
    -e AWS_DEFAULT_REGION=us-east-2 \
    -v $(pwd)/reports:/app/reports \
    mysql-upgrade-assessment \
    --cluster my-cluster --region us-east-2
```

### Scheduled Assessments (cron)

```bash
# Edit crontab
crontab -e

# Add daily assessment at 2 AM
0 2 * * * cd /path/to/mysql-upgrade-assessment-tool && source venv/bin/activate && python run_assessment.py --cluster my-cluster --region us-east-2 >> logs/cron.log 2>&1
```

---

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to database
```bash
# Check network connectivity
telnet your-db-endpoint.rds.amazonaws.com 3306

# Check security groups
aws rds describe-db-instances --db-instance-identifier your-instance \
    --query 'DBInstances[0].VpcSecurityGroups'

# Test from EC2 in same VPC
mysql -h your-db-endpoint.rds.amazonaws.com -u admin -p
```

**Solution**:
- Verify security group allows inbound 3306
- Ensure database is publicly accessible (if running locally)
- Check VPN connection for private VPCs

### Credential Issues

**Problem**: Credentials not found
```bash
# List secrets in Secrets Manager
aws secretsmanager list-secrets --region us-east-2

# Get specific secret
aws secretsmanager get-secret-value --secret-id rds!cluster-YOUR-ID --region us-east-2
```

**Solution**:
- Verify secret exists for your RDS resource ID
- Check IAM permissions for Secrets Manager
- Ensure region matches your database

### Permission Issues

**Problem**: Access denied errors
```bash
# Check current IAM user/role
aws sts get-caller-identity

# Check attached policies
aws iam list-attached-user-policies --user-name YOUR_USER
```

**Solution**:
- Attach required IAM policy
- Verify policy has correct permissions
- Check resource-level restrictions

### Python/Dependency Issues

**Problem**: Module import errors
```bash
# Reinstall dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

**Problem**: Python version mismatch
```bash
# Check Python version
python --version  # Should be 3.8+

# Create venv with specific version
python3.9 -m venv venv
```

---

## Best Practices

### Security
✅ Use IAM roles instead of access keys (when possible)
✅ Rotate AWS credentials regularly
✅ Store credentials in AWS Secrets Manager
✅ Enable MFA on AWS account
✅ Use VPC endpoints for enhanced security

### Performance
✅ Run during low-traffic periods
✅ Assess one database at a time for large instances
✅ Use EC2 in same region as database
✅ Monitor network bandwidth

### Operational
✅ Schedule regular assessments (monthly)
✅ Keep tool updated to latest version
✅ Archive assessment reports
✅ Track remediation progress
✅ Re-assess after fixes

---

## Support

For issues or questions:
- 📖 Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- 🐛 Report issues on GitHub
- 💬 Contact AWS support for database-specific questions

---

**Version**: 1.0.0
**Last Updated**: 2025-12-12
