# Troubleshooting Guide

This guide provides solutions to common issues you may encounter when using the MySQL Upgrade Assessment Tool.

---

## Table of Contents
1. [Connection Issues](#connection-issues)
2. [Credential Issues](#credential-issues)
3. [Permission Issues](#permission-issues)
4. [Installation Issues](#installation-issues)
5. [Assessment Issues](#assessment-issues)
6. [Report Generation Issues](#report-generation-issues)
7. [AWS-Specific Issues](#aws-specific-issues)

---

## Connection Issues

### Problem: Cannot connect to database

**Error Message:**
```
Error: Can't connect to MySQL server on 'database-endpoint.rds.amazonaws.com' (110)
Error: Connection timed out
```

**Possible Causes & Solutions:**

#### 1. Security Group Not Configured
```bash
# Check security groups
aws rds describe-db-instances \
  --db-instance-identifier your-instance \
  --query 'DBInstances[0].VpcSecurityGroups'

# Verify inbound rules allow port 3306 from your IP
aws ec2 describe-security-groups \
  --group-ids sg-xxxxx \
  --query 'SecurityGroups[0].IpPermissions'
```

**Solution:** Add inbound rule for port 3306 from your IP:
```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 3306 \
  --cidr your-ip-address/32
```

#### 2. Database Not Publicly Accessible
```bash
# Check if database is publicly accessible
aws rds describe-db-instances \
  --db-instance-identifier your-instance \
  --query 'DBInstances[0].PubliclyAccessible'
```

**Solution:** If running locally, enable public accessibility:
```bash
aws rds modify-db-instance \
  --db-instance-identifier your-instance \
  --publicly-accessible \
  --apply-immediately
```

#### 3. VPN Not Connected (Private VPC)
**Solution:** Verify VPN connection:
```bash
# Test connectivity
telnet database-endpoint.rds.amazonaws.com 3306
# OR
nc -zv database-endpoint.rds.amazonaws.com 3306
```

#### 4. Wrong Database Endpoint
**Solution:** Verify endpoint:
```bash
# For RDS instance
aws rds describe-db-instances \
  --db-instance-identifier your-instance \
  --query 'DBInstances[0].Endpoint.Address'

# For Aurora cluster
aws rds describe-db-clusters \
  --db-cluster-identifier your-cluster \
  --query 'DBClusters[0].Endpoint'
```

---

### Problem: Connection refused immediately

**Error Message:**
```
Error: Can't connect to MySQL server on 'database-endpoint.rds.amazonaws.com' (111)
```

**Solution:**
1. Verify database is running:
```bash
aws rds describe-db-instances \
  --db-instance-identifier your-instance \
  --query 'DBInstances[0].DBInstanceStatus'
```

2. Check if using correct port (default: 3306)

3. Verify endpoint spelling and region

---

## Credential Issues

### Problem: Credentials not found

**Error Message:**
```
Error: Unable to retrieve credentials from Secrets Manager
Secret not found: rds!cluster-xxxxx
```

**Solutions:**

#### 1. List Available Secrets
```bash
# List all RDS secrets in your region
aws secretsmanager list-secrets \
  --region us-east-2 \
  --query 'SecretList[?starts_with(Name, `rds!`)].Name'
```

#### 2. Get RDS Resource ID
```bash
# For Aurora cluster
aws rds describe-db-clusters \
  --db-cluster-identifier your-cluster \
  --query 'DBClusters[0].DbClusterResourceId'

# For RDS instance
aws rds describe-db-instances \
  --db-instance-identifier your-instance \
  --query 'DBInstances[0].DbiResourceId'
```

The secret name should be: `rds!cluster-{ResourceId}` or `rds!db-{ResourceId}`

#### 3. Verify Secret Exists
```bash
aws secretsmanager get-secret-value \
  --secret-id rds!cluster-xxxxx \
  --region us-east-2
```

#### 4. Create Secret if Missing
```bash
aws secretsmanager create-secret \
  --name rds!cluster-xxxxx \
  --description "Credentials for MySQL cluster" \
  --secret-string '{"username":"admin","password":"YOUR_PASSWORD"}' \
  --region us-east-2
```

---

### Problem: Invalid credentials

**Error Message:**
```
Error: Access denied for user 'admin'@'x.x.x.x' (using password: YES)
```

**Solutions:**

1. Verify credentials in secret:
```bash
aws secretsmanager get-secret-value \
  --secret-id rds!cluster-xxxxx \
  --query 'SecretString' \
  --output text | jq .
```

2. Test credentials manually:
```bash
mysql -h database-endpoint.rds.amazonaws.com \
  -u admin \
  -p
```

3. Reset password if needed:
```bash
aws rds modify-db-instance \
  --db-instance-identifier your-instance \
  --master-user-password NEW_PASSWORD \
  --apply-immediately
```

4. Update secret with new password:
```bash
aws secretsmanager update-secret \
  --secret-id rds!cluster-xxxxx \
  --secret-string '{"username":"admin","password":"NEW_PASSWORD"}'
```

---

## Permission Issues

### Problem: AWS access denied

**Error Message:**
```
botocore.exceptions.ClientError: An error occurred (AccessDenied) when calling the DescribeDBClusters operation
```

**Solutions:**

#### 1. Check Current IAM Identity
```bash
aws sts get-caller-identity
```

#### 2. Verify IAM Permissions
```bash
# Check attached policies
aws iam list-attached-user-policies --user-name YOUR_USER

# Check policy document
aws iam get-policy-version \
  --policy-arn arn:aws:iam::ACCOUNT:policy/PolicyName \
  --version-id v1
```

#### 3. Attach Required Policy
```bash
# Create policy file: mysql-assessment-policy.json
cat > mysql-assessment-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:DescribeDBClusters",
        "rds:DescribeDBInstances",
        "secretsmanager:GetSecretValue",
        "secretsmanager:ListSecrets"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create and attach policy
aws iam create-policy \
  --policy-name MySQLAssessmentPolicy \
  --policy-document file://mysql-assessment-policy.json

aws iam attach-user-policy \
  --user-name YOUR_USER \
  --policy-arn arn:aws:iam::ACCOUNT:policy/MySQLAssessmentPolicy
```

---

### Problem: Database user permissions

**Error Message:**
```
Error: SELECT command denied to user 'readonly'@'x.x.x.x' for table 'XXX'
```

**Solution:** Ensure database user has required permissions:
```sql
-- Grant necessary permissions
GRANT SELECT ON *.* TO 'assessment_user'@'%';
GRANT SELECT ON mysql.* TO 'assessment_user'@'%';
GRANT SELECT ON information_schema.* TO 'assessment_user'@'%';
GRANT SELECT ON performance_schema.* TO 'assessment_user'@'%';
FLUSH PRIVILEGES;
```

---

## Installation Issues

### Problem: Python version mismatch

**Error Message:**
```
ERROR: This package requires Python >=3.8
```

**Solution:**
```bash
# Check Python version
python3 --version

# Create virtual environment with specific version
python3.9 -m venv venv
source venv/bin/activate

# Verify
python --version
```

---

### Problem: Module import errors

**Error Message:**
```
ModuleNotFoundError: No module named 'mysql.connector'
ImportError: No module named 'boto3'
```

**Solutions:**

1. Activate virtual environment:
```bash
source venv/bin/activate
```

2. Reinstall dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

3. Verify installation:
```bash
python -c "import mysql.connector, boto3; print('OK')"
```

---

### Problem: pip install fails

**Error Message:**
```
ERROR: Could not build wheels for mysql-connector-python
```

**Solutions:**

1. Install system dependencies (macOS):
```bash
brew install mysql-client
```

2. Install system dependencies (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install -y \
  python3-dev \
  default-libmysqlclient-dev \
  build-essential
```

3. Install system dependencies (RHEL/Amazon Linux):
```bash
sudo yum install -y \
  python3-devel \
  mysql-devel \
  gcc
```

---

## Assessment Issues

### Problem: No databases found

**Error Message:**
```
No MySQL 5.7 databases found in region us-east-1
```

**Solutions:**

1. Verify AWS credentials are configured:
```bash
aws sts get-caller-identity
```

2. Check correct region:
```bash
aws rds describe-db-instances --region us-east-2
aws rds describe-db-clusters --region us-east-2
```

3. Verify database version:
```bash
aws rds describe-db-instances \
  --db-instance-identifier your-instance \
  --query 'DBInstances[0].EngineVersion'
```

---

### Problem: Assessment hangs or takes too long

**Symptoms:**
- Assessment runs for >30 minutes
- No progress updates
- Process appears frozen

**Solutions:**

1. Check database load:
```bash
# Monitor CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=your-instance \
  --start-time 2025-12-12T00:00:00Z \
  --end-time 2025-12-12T23:59:59Z \
  --period 300 \
  --statistics Average
```

2. Run with verbose logging:
```bash
python run_assessment.py \
  --cluster your-cluster \
  --region us-east-2 \
  --verbose
```

3. Check network latency:
```bash
ping database-endpoint.rds.amazonaws.com
```

4. Run during low-traffic period

---

### Problem: Incomplete assessment results

**Symptoms:**
- Some checks show "0 issues" when you expect issues
- Missing data in report

**Solutions:**

1. Check database user permissions (see above)

2. Verify all schemas are accessible:
```sql
SHOW DATABASES;
```

3. Check for connection timeouts in logs:
```bash
cat logs/assessment.log | grep -i timeout
```

---

## Report Generation Issues

### Problem: Report not generated

**Error Message:**
```
Error: Unable to write report to reports/upgrade_assessment.html
Permission denied
```

**Solutions:**

1. Check directory permissions:
```bash
ls -la reports/
```

2. Create directory if missing:
```bash
mkdir -p reports
chmod 755 reports
```

3. Check disk space:
```bash
df -h
```

---

### Problem: Report opens but looks broken

**Symptoms:**
- No styling
- JavaScript errors
- Missing sections

**Solutions:**

1. Open report in different browser

2. Check browser console for errors (F12)

3. Verify report file is complete:
```bash
# Check file size (should be >100 KB)
ls -lh reports/upgrade_assessment.html

# Check for HTML closing tags
tail reports/upgrade_assessment.html
```

4. Regenerate report:
```bash
python run_assessment.py \
  --cluster your-cluster \
  --region us-east-2
```

---

## AWS-Specific Issues

### Problem: Region mismatch

**Error Message:**
```
Error: Database not found in region us-east-1
```

**Solution:**
```bash
# List databases in all regions
for region in us-east-1 us-east-2 us-west-1 us-west-2; do
  echo "=== $region ==="
  aws rds describe-db-instances \
    --region $region \
    --query 'DBInstances[].DBInstanceIdentifier'
done
```

---

### Problem: AWS CLI not configured

**Error Message:**
```
Unable to locate credentials. You can configure credentials by running "aws configure"
```

**Solution:**
```bash
aws configure
# Enter:
# AWS Access Key ID
# AWS Secret Access Key
# Default region name (e.g., us-east-2)
# Default output format (e.g., json)

# Verify
aws sts get-caller-identity
```

---

### Problem: Session token expired

**Error Message:**
```
The security token included in the request is expired
```

**Solution:**
```bash
# Refresh AWS SSO session
aws sso login --profile your-profile

# Or refresh temporary credentials
# (Re-authenticate through your identity provider)
```

---

## Advanced Troubleshooting

### Enable Debug Logging

1. Edit `run_assessment.py` and set logging level:
```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

2. Check logs:
```bash
tail -f logs/assessment.log
```

---

### Test Database Connectivity

```python
# test_connection.py
import mysql.connector
import sys

config = {
    'host': 'database-endpoint.rds.amazonaws.com',
    'user': 'admin',
    'password': 'YOUR_PASSWORD',
    'database': 'information_schema',
    'connect_timeout': 30
}

try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    cursor.execute("SELECT VERSION()")
    version = cursor.fetchone()[0]
    print(f"✓ Connected successfully. MySQL version: {version}")
    cursor.close()
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f"✗ Connection failed: {e}")
    sys.exit(1)
```

Run:
```bash
python test_connection.py
```

---

### Verify AWS Secrets Manager Access

```bash
# Test Secrets Manager access
python3 << EOF
import boto3
import json

client = boto3.client('secretsmanager', region_name='us-east-2')

try:
    response = client.list_secrets()
    rds_secrets = [s['Name'] for s in response['SecretList'] if s['Name'].startswith('rds!')]
    print(f"✓ Found {len(rds_secrets)} RDS secrets:")
    for secret in rds_secrets:
        print(f"  - {secret}")
except Exception as e:
    print(f"✗ Error: {e}")
EOF
```

---

## Getting Help

If you've tried the solutions above and still have issues:

1. **Check the FAQ**: See `docs/FAQ.md` for common questions

2. **Review logs**: Look for specific error messages in:
   - `logs/assessment.log`
   - Terminal output with `--verbose` flag

3. **GitHub Issues**: Report bugs at:
   - AWS Support team, STAM NAMER
   - Include: error message, logs, environment details

4. **AWS Support**: For AWS-specific issues:
   - Database connectivity
   - IAM permissions
   - Secrets Manager
   - RDS/Aurora configuration

---

## Common Error Codes

| Error Code | Meaning | Solution |
|------------|---------|----------|
| 1045 | Access denied | Check credentials |
| 1130 | Host not allowed | Check security group |
| 2003 | Can't connect | Network/firewall issue |
| 2006 | Server gone away | Timeout or network issue |
| 2013 | Lost connection | Network instability |

---

**Last Updated**: 2025-12-12
**Version**: 1.0.0
