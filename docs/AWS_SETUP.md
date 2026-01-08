# AWS Prerequisites and Setup Guide

This guide walks you through setting up the required AWS resources and permissions to run the MySQL Upgrade Assessment Tool.

---

## Table of Contents
1. [Overview](#overview)
2. [IAM Setup](#iam-setup)
3. [Secrets Manager Setup](#secrets-manager-setup)
4. [Network Configuration](#network-configuration)
5. [Database Configuration](#database-configuration)
6. [Verification Steps](#verification-steps)

---

## Overview

The tool requires access to:
- **AWS RDS/Aurora API** - To discover and describe databases
- **AWS Secrets Manager** - To retrieve database credentials
- **Database Network Access** - To connect and run assessment queries

**Minimum AWS Services Required:**
- Amazon RDS MySQL 5.7 or Aurora MySQL 5.7
- AWS Secrets Manager
- AWS IAM (for permissions)

---

## IAM Setup

### Step 1: Create IAM Policy

Create a policy that grants the minimum required permissions:

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

**Save this as**: `mysql-upgrade-assessment-policy.json`

### Step 2: Create Policy in AWS

#### Using AWS Console:
1. Go to IAM Console → Policies → Create Policy
2. Click JSON tab
3. Paste the policy JSON above
4. Click Next
5. Name: `MySQLUpgradeAssessmentPolicy`
6. Description: `Permissions for MySQL 5.7 to 8.0 upgrade assessment tool`
7. Click Create Policy

#### Using AWS CLI:
```bash
aws iam create-policy \
  --policy-name MySQLUpgradeAssessmentPolicy \
  --policy-document file://mysql-upgrade-assessment-policy.json \
  --description "Permissions for MySQL 5.7 to 8.0 upgrade assessment tool"
```

**Note the Policy ARN from the output** - you'll need it in the next step.

### Step 3: Attach Policy to IAM Entity

Choose one of the following based on how you'll run the tool:

#### Option A: For IAM User (Local Execution)

**Using AWS Console:**
1. Go to IAM Console → Users → Select your user
2. Click "Add permissions" → "Attach policies directly"
3. Search for `MySQLUpgradeAssessmentPolicy`
4. Select and click "Add permissions"

**Using AWS CLI:**
```bash
aws iam attach-user-policy \
  --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/MySQLUpgradeAssessmentPolicy
```

#### Option B: For IAM Role (EC2/Lambda Execution)

**Using AWS Console:**
1. Go to IAM Console → Roles → Select your role
2. Click "Add permissions" → "Attach policies"
3. Search for `MySQLUpgradeAssessmentPolicy`
4. Select and click "Attach policies"

**Using AWS CLI:**
```bash
aws iam attach-role-policy \
  --role-name YOUR_ROLE_NAME \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/MySQLUpgradeAssessmentPolicy
```

### Step 4: Verify IAM Permissions

```bash
# Check attached policies
aws iam list-attached-user-policies --user-name YOUR_USERNAME

# Test RDS access
aws rds describe-db-instances --max-items 1

# Test Secrets Manager access
aws secretsmanager list-secrets --max-results 1
```

---

## Secrets Manager Setup

AWS RDS and Aurora can automatically manage secrets. If not already set up:

### Step 1: Find Your RDS Resource ID

#### For Aurora Cluster:
```bash
aws rds describe-db-clusters \
  --db-cluster-identifier your-cluster-name \
  --query 'DBClusters[0].DbClusterResourceId' \
  --output text
```

#### For RDS Instance:
```bash
aws rds describe-db-instances \
  --db-instance-identifier your-instance-name \
  --query 'DBInstances[0].DbiResourceId' \
  --output text
```

**Example Output:** `cluster-ABCDEFGHIJK123456` or `db-ABCDEFGHIJK123456`

### Step 2: Check if Secret Exists

```bash
# List all RDS secrets
aws secretsmanager list-secrets \
  --query 'SecretList[?starts_with(Name, `rds!`)].Name'

# Check specific secret (replace with your resource ID)
aws secretsmanager describe-secret \
  --secret-id rds!cluster-ABCDEFGHIJK123456
```

### Step 3: Create Secret (If Not Exists)

```bash
# Get your RDS resource ID first (see Step 1)
RESOURCE_ID="cluster-ABCDEFGHIJK123456"  # Replace with your actual ID

# Create secret
aws secretsmanager create-secret \
  --name rds!${RESOURCE_ID} \
  --description "Database credentials for MySQL upgrade assessment" \
  --secret-string '{"username":"admin","password":"YOUR_SECURE_PASSWORD"}' \
  --region us-east-2
```

**Important:**
- Secret name MUST follow pattern: `rds!cluster-XXXXX` or `rds!db-XXXXX`
- Use your actual RDS resource ID (not cluster/instance identifier)
- Replace `YOUR_SECURE_PASSWORD` with your actual database password
- Match the region to your database region

### Step 4: Verify Secret

```bash
# Retrieve secret value (be careful - exposes password)
aws secretsmanager get-secret-value \
  --secret-id rds!cluster-ABCDEFGHIJK123456 \
  --query 'SecretString' \
  --output text
```

Expected output:
```json
{"username":"admin","password":"YOUR_SECURE_PASSWORD"}
```

### Step 5: Enable Automatic Rotation (Optional)

```bash
aws secretsmanager rotate-secret \
  --secret-id rds!cluster-ABCDEFGHIJK123456 \
  --rotation-lambda-arn arn:aws:lambda:REGION:ACCOUNT:function:SecretsManagerRDSMySQLRotation \
  --rotation-rules AutomaticallyAfterDays=30
```

---

## Network Configuration

### Step 1: Identify Database Security Group

```bash
# For RDS instance
aws rds describe-db-instances \
  --db-instance-identifier your-instance \
  --query 'DBInstances[0].VpcSecurityGroups[*].[VpcSecurityGroupId,Status]'

# For Aurora cluster
aws rds describe-db-clusters \
  --db-cluster-identifier your-cluster \
  --query 'DBClusters[0].VpcSecurityGroups[*].[VpcSecurityGroupId,Status]'
```

**Note the Security Group ID** (e.g., `sg-0123456789abcdef0`)

### Step 2: Check Current Security Group Rules

```bash
aws ec2 describe-security-groups \
  --group-ids sg-0123456789abcdef0 \
  --query 'SecurityGroups[0].IpPermissions'
```

### Step 3: Add Inbound Rule for MySQL

Choose based on your deployment scenario:

#### Scenario A: Running Tool from Specific IP (Local Machine)

1. Get your public IP:
```bash
curl -s https://checkip.amazonaws.com
```

2. Add security group rule:
```bash
# Replace with your actual IP and security group ID
YOUR_IP=$(curl -s https://checkip.amazonaws.com)

aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789abcdef0 \
  --protocol tcp \
  --port 3306 \
  --cidr ${YOUR_IP}/32 \
  --description "MySQL access for upgrade assessment from my IP"
```

#### Scenario B: Running Tool from EC2 Instance

```bash
# Get EC2 security group ID
EC2_SG_ID="sg-0987654321fedcba"

# Allow MySQL access from EC2 security group
aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789abcdef0 \
  --protocol tcp \
  --port 3306 \
  --source-group ${EC2_SG_ID} \
  --description "MySQL access from assessment EC2 instance"
```

#### Scenario C: Running Tool via VPN

If your database is in a private subnet and you connect via VPN:
- Ensure VPN connection is established
- Security group should allow access from VPN CIDR range
- Verify VPN routing tables include database subnet

### Step 4: Verify Network Connectivity

```bash
# Get database endpoint
ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier your-instance \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

# Test connectivity
telnet $ENDPOINT 3306
# OR
nc -zv $ENDPOINT 3306
```

Expected output:
```
Connection to your-db-endpoint.rds.amazonaws.com 3306 port [tcp/mysql] succeeded!
```

---

## Database Configuration

### Step 1: Check Database Version

```bash
# For RDS instance
aws rds describe-db-instances \
  --db-instance-identifier your-instance \
  --query 'DBInstances[0].[Engine,EngineVersion]'

# For Aurora cluster
aws rds describe-db-clusters \
  --db-cluster-identifier your-cluster \
  --query 'DBClusters[0].[Engine,EngineVersion]'
```

**Supported versions:**
- MySQL 5.7.x
- Aurora MySQL 5.7.x (compatible with MySQL 5.7.12)

### Step 2: Verify Database User Permissions

The tool needs a database user with SELECT permissions. Connect to your database:

```bash
mysql -h your-endpoint.rds.amazonaws.com -u admin -p
```

Then verify permissions:

```sql
-- Check current user permissions
SHOW GRANTS FOR CURRENT_USER;

-- Recommended permissions for assessment user:
CREATE USER IF NOT EXISTS 'assessment_user'@'%' IDENTIFIED BY 'secure_password';
GRANT SELECT ON *.* TO 'assessment_user'@'%';
GRANT SELECT ON mysql.* TO 'assessment_user'@'%';
GRANT SELECT ON information_schema.* TO 'assessment_user'@'%';
GRANT SELECT ON performance_schema.* TO 'assessment_user'@'%';
FLUSH PRIVILEGES;
```

**Note:** The tool only performs SELECT queries - no data modifications.

### Step 3: Check Database Status

```bash
# Ensure database is available
aws rds describe-db-instances \
  --db-instance-identifier your-instance \
  --query 'DBInstances[0].DBInstanceStatus'
```

Expected output: `available`

---

## Verification Steps

### Complete Pre-Flight Checklist

```bash
#!/bin/bash
# pre-flight-check.sh

echo "=== MySQL Upgrade Assessment Tool - Pre-Flight Check ==="
echo

# 1. Check AWS CLI
echo "[1/7] Checking AWS CLI..."
if aws --version > /dev/null 2>&1; then
  echo "✓ AWS CLI installed"
else
  echo "✗ AWS CLI not found. Install from: https://aws.amazon.com/cli/"
  exit 1
fi

# 2. Check AWS credentials
echo "[2/7] Checking AWS credentials..."
if aws sts get-caller-identity > /dev/null 2>&1; then
  echo "✓ AWS credentials configured"
  aws sts get-caller-identity --query '[Account,UserId,Arn]' --output table
else
  echo "✗ AWS credentials not configured. Run: aws configure"
  exit 1
fi

# 3. Check RDS permissions
echo "[3/7] Checking RDS permissions..."
if aws rds describe-db-instances --max-items 1 > /dev/null 2>&1; then
  echo "✓ RDS permissions OK"
else
  echo "✗ Missing RDS permissions"
  exit 1
fi

# 4. Check Secrets Manager permissions
echo "[4/7] Checking Secrets Manager permissions..."
if aws secretsmanager list-secrets --max-results 1 > /dev/null 2>&1; then
  echo "✓ Secrets Manager permissions OK"
else
  echo "✗ Missing Secrets Manager permissions"
  exit 1
fi

# 5. List MySQL 5.7 databases
echo "[5/7] Listing MySQL 5.7 databases..."
DATABASES=$(aws rds describe-db-instances \
  --query 'DBInstances[?Engine==`mysql` && starts_with(EngineVersion, `5.7`)].DBInstanceIdentifier' \
  --output text)

if [ -n "$DATABASES" ]; then
  echo "✓ Found MySQL 5.7 databases:"
  echo "  $DATABASES"
else
  echo "⚠ No MySQL 5.7 databases found"
fi

# 6. Check Python version
echo "[6/7] Checking Python version..."
if python3 --version > /dev/null 2>&1; then
  PYTHON_VERSION=$(python3 --version)
  echo "✓ $PYTHON_VERSION installed"
else
  echo "✗ Python 3 not found"
  exit 1
fi

# 7. Test database connectivity (optional)
echo "[7/7] Testing database connectivity..."
read -p "Enter database endpoint to test (or press Enter to skip): " DB_ENDPOINT
if [ -n "$DB_ENDPOINT" ]; then
  if nc -zv -w 5 $DB_ENDPOINT 3306 2>&1 | grep -q succeeded; then
    echo "✓ Database reachable"
  else
    echo "✗ Cannot reach database. Check security groups and network."
  fi
else
  echo "⊘ Skipped database connectivity test"
fi

echo
echo "=== Pre-Flight Check Complete ==="
echo "✓ You're ready to run the assessment tool!"
```

Run the verification:
```bash
chmod +x pre-flight-check.sh
./pre-flight-check.sh
```

---

## AWS Deployment Scenarios

### Scenario 1: Running from Local Machine

**Requirements:**
- AWS CLI configured with credentials
- Database publicly accessible OR VPN connection
- Security group allows your IP

**Setup:**
```bash
aws configure
# Enter your Access Key ID, Secret Access Key, Region
```

### Scenario 2: Running from EC2 Instance

**Requirements:**
- EC2 instance with IAM role attached
- EC2 in same VPC as database (or VPC peering configured)
- Security group allows EC2 → Database communication

**Setup:**
```bash
# Launch EC2 with IAM role
aws ec2 run-instances \
  --image-id ami-xxxxx \
  --instance-type t3.micro \
  --iam-instance-profile Name=MySQLAssessmentRole \
  --security-group-ids sg-xxxxx \
  --subnet-id subnet-xxxxx

# No AWS credentials needed - uses IAM role
```

### Scenario 3: Running from Lambda

**Requirements:**
- Lambda function with IAM role
- Lambda in VPC with database access
- Execution timeout: 15 minutes (max)

**Limitations:**
- Not recommended for large databases (timeout)
- Better for scheduled assessments of small databases

---

## Region Considerations

The tool works across all AWS regions. Key points:

1. **Specify correct region** when running:
```bash
python run_assessment.py --cluster your-cluster --region us-west-2
```

2. **Secrets must be in same region** as database:
```bash
# Wrong: Secret in us-east-1, database in us-west-2
# Right: Both in us-west-2
```

3. **Cross-region access**:
- IAM permissions are global
- But you must specify region when accessing RDS/Secrets Manager

---

## Security Best Practices

1. **Use IAM Roles** when possible (instead of access keys)
2. **Enable MFA** on IAM users
3. **Rotate credentials** regularly
4. **Use least privilege** - only grant required permissions
5. **Enable VPC endpoints** for enhanced security:
```bash
# Create Secrets Manager VPC endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxxxx \
  --service-name com.amazonaws.us-east-2.secretsmanager \
  --route-table-ids rtb-xxxxx
```

6. **Encrypt secrets** at rest (enabled by default in Secrets Manager)
7. **Enable CloudTrail** for audit logging

---

## Cost Considerations

Running this tool incurs minimal AWS costs:

- **RDS API calls**: Free
- **Secrets Manager**:
  - $0.40 per secret per month
  - $0.05 per 10,000 API calls
- **Data transfer**:
  - In same region: Free
  - Cross-region: Standard data transfer rates

**Estimated monthly cost**: <$1 per database

---

## Support Resources

### AWS Documentation
- [RDS MySQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_MySQL.html)
- [Aurora MySQL](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.AuroraMySQL.html)
- [Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [IAM Policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html)

### AWS Support
- For AWS service issues, contact AWS Support
- Check AWS Service Health Dashboard
- Join AWS forums and communities

---

**Last Updated**: 2025-12-12
**Version**: 1.0.0
