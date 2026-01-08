# Aurora Upgrade Checker - Quick Start Guide

## Overview

This guide will help you run your first upgrade assessment in 5 minutes.

## Prerequisites

- Python 3.8 or higher
- AWS CLI configured with credentials
- Access to Aurora MySQL 5.7.x or RDS MySQL 5.7.x clusters
- Network connectivity to your database endpoints

## Step 1: Set Up Environment

Run the automated setup script:

```bash
cd /Users/Mallik.Mudigonda/malliks-codebase/AUC-tooling

# Make setup script executable
chmod +x scripts/setup.sh

# Run setup
./scripts/setup.sh
```

This will:
- Check Python version
- Create virtual environment
- Install dependencies
- Verify AWS CLI

## Step 2: Configure AWS Credentials

Make sure your AWS credentials are configured:

```bash
# Check if AWS CLI is configured
aws sts get-caller-identity

# If not configured, run:
aws configure
```

Enter:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., us-east-1)
- Output format (json)

## Step 3: Configure the Tool

Edit the configuration file with your settings:

```bash
vi config/config.yaml
```

### Configuration Options

Choose ONE of three authentication methods:

#### Option 1: AWS Secrets Manager (Recommended for Production)

```yaml
aws:
  region: us-east-1  # Your AWS region

authentication:
  method: secrets_manager

  secrets:
    # Map your cluster IDs to secret ARNs
    my-aurora-cluster: arn:aws:secretsmanager:us-east-1:123456789012:secret:db/aurora-credentials
    my-rds-instance: db/rds/credentials
```

**Secret Format** (in Secrets Manager):
```json
{
  "username": "admin",
  "password": "YourPassword123!",
  "host": "cluster.endpoint.rds.amazonaws.com",
  "port": 3306
}
```

#### Option 2: IAM Database Authentication

```yaml
aws:
  region: us-east-1

authentication:
  method: iam

  iam:
    username: iam_db_user
```

**Requirements**:
- Database user must be created with IAM authentication enabled
- IAM policy must include `rds-db:connect` permission

#### Option 3: Direct Config (For Testing Only)

```yaml
aws:
  region: us-east-1

authentication:
  method: config

  databases:
    - identifier: my-cluster-1
      endpoint: my-cluster-1.cluster-abc123.us-east-1.rds.amazonaws.com
      port: 3306
      user: admin
      password: 'MyPassword123!'
```

**WARNING**: Only use this method for testing. Do not commit passwords to git!

## Step 4: Verify Configuration

Test your AWS connectivity:

```bash
# Activate virtual environment
source venv/bin/activate

# Test AWS connectivity
python3 -c "import boto3; print(boto3.client('rds', region_name='us-east-1').describe_db_clusters())"
```

## Step 5: Run Your First Assessment

### Option A: Assess All MySQL 5.7 Clusters (Auto-Discovery)

```bash
source venv/bin/activate
python run_assessment.py
```

This will:
- Auto-discover all Aurora MySQL 5.7.x clusters
- Auto-discover all RDS MySQL 5.7.x instances
- Run 20 comprehensive checks on each
- Generate HTML, JSON, and Markdown reports

### Option B: Assess a Specific Cluster

```bash
source venv/bin/activate
python run_assessment.py --cluster my-cluster-id
```

### Option C: Assess with Custom Region

```bash
source venv/bin/activate
python run_assessment.py --region us-west-2 --profile production
```

### Option D: Verbose Output

```bash
source venv/bin/activate
python run_assessment.py --cluster my-cluster-id --verbose
```

## Step 6: View Results

After the assessment completes, you'll find reports in the `reports/` directory:

```bash
# View HTML report (opens in browser)
open reports/upgrade_assessment.html

# View JSON report
cat reports/upgrade_assessment.json | jq

# View executive summary
cat reports/executive_summary.md
```

## Understanding the Report

### Status Colors

- **GREEN**: No issues, ready to proceed
- **AMBER**: Warnings, review recommended
- **RED**: Critical issues, must fix before upgrade

### Report Sections

1. **Executive Summary**: High-level overview
2. **Detailed Findings**: All 20 checks with issues and recommendations
3. **Upgrade Plan**: Step-by-step upgrade path
4. **Parameter Changes**: Aurora and RDS parameter updates needed

### The 20 Checks

1. Schema Information - Database size, table counts
2. Version Compatibility - Version validation
3. Character Sets - Legacy charset detection
4. Binary Log Settings - Replication configuration
5. Deprecated Features - Functions, auth methods
6. Parameters - Removed/changed parameters
7. Foreign Keys - Constraint analysis
8. Triggers/Views - Compatibility checks
9. New Features - MySQL 8.0 opportunities
10. **Reserved Keywords** - Conflicts with MySQL 8.0 keywords
11. Partition Compatibility - Partitioned tables
12. User Privileges - Security and authentication
13. JSON Usage - JSON columns and optimization
14. Stored Routine Complexity - Procedure analysis
15. Spatial SRID - Spatial data requirements
16. Functional Indexes - New indexing opportunities
17. Index Statistics - Duplicate and inefficient indexes
18. Auto-Increment Exhaustion - Capacity planning
19. Replication Topology - Replication health
20. Connection Configuration - Connection pooling

## Common Issues and Solutions

### Issue: "Configuration file not found"

**Solution**:
```bash
cp config/config_example.yaml config/config.yaml
vi config/config.yaml
# Add your settings
```

### Issue: "No MySQL 5.7.x databases found"

**Possible Causes**:
1. Wrong region specified
2. No MySQL 5.7.x clusters in the account
3. Insufficient IAM permissions

**Solution**:
```bash
# Check what clusters exist
aws rds describe-db-clusters --region us-east-1 | jq '.DBClusters[] | {Identifier: .DBClusterIdentifier, Engine: .Engine, Version: .EngineVersion}'

# Check IAM permissions
aws iam get-user
```

### Issue: "Failed to connect to database"

**Possible Causes**:
1. Incorrect credentials
2. Security group blocking connection
3. Database in VPC without public access

**Solutions**:
- Verify credentials in Secrets Manager or config
- Check security group rules allow your IP
- Run from EC2 instance in same VPC
- Use VPC endpoints for private access

### Issue: "IAM authentication failed"

**Requirements**:
```sql
-- Create IAM-enabled database user
CREATE USER 'iam_db_user' IDENTIFIED WITH AWSAuthenticationPlugin AS 'RDS';
GRANT SELECT ON *.* TO 'iam_db_user'@'%';
```

IAM Policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "rds-db:connect",
    "Resource": "arn:aws:rds-db:us-east-1:123456789012:dbuser:cluster-ABC123DEF456/iam_db_user"
  }]
}
```

## Testing Tips

### Start Small
```bash
# Test with one cluster first
python run_assessment.py --cluster my-test-cluster --verbose
```

### Review Each Check
Open the HTML report and review each of the 20 checks:
- Understand what each check found
- Prioritize RED issues first
- Plan remediation for AMBER warnings

### Test Authentication Methods
```bash
# Test IAM auth
# Edit config.yaml: method: iam
python run_assessment.py --cluster my-cluster

# Test Secrets Manager
# Edit config.yaml: method: secrets_manager
python run_assessment.py --cluster my-cluster

# Test direct config (testing only)
# Edit config.yaml: method: config
python run_assessment.py --cluster my-cluster
```

## Next Steps

1. **Review the Security Report**: `SECURITY_AUDIT_REPORT.md`
2. **Read the Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`
3. **Check Full Documentation**: `README.md`
4. **Address RED Issues**: Fix critical blockers before upgrade
5. **Plan Upgrade**: Follow upgrade path in report
6. **Test in Non-Production**: Always test upgrades first

## Command Reference

```bash
# Basic assessment
python run_assessment.py

# Specific cluster
python run_assessment.py --cluster my-cluster-id

# Custom region and profile
python run_assessment.py --region us-west-2 --profile prod

# Verbose logging
python run_assessment.py --verbose

# Combination
python run_assessment.py --cluster my-cluster --region us-east-1 --verbose

# Help
python run_assessment.py --help
```

## Getting Help

### Check Logs
```bash
# View logs
tail -f logs/auc.log

# Check for errors
grep ERROR logs/auc.log
```

### Enable Debug Logging
```yaml
# In config.yaml
logging:
  level: DEBUG
```

### Test Individual Components
```python
# Test AWS connection
python3 -c "from src.utils.aws_utils import AWSUtils; aws = AWSUtils('us-east-1'); print(aws.get_aurora_clusters())"

# Test configuration
python3 -c "from src.utils.config_loader import ConfigLoader; cfg = ConfigLoader(); print(cfg.get_region())"
```

## Security Best Practices

1. **Use Secrets Manager** in production
2. **Never commit** `config/config.yaml` to git (already in .gitignore)
3. **Use IAM roles** on EC2 instead of access keys
4. **Enable CloudTrail** for audit logging
5. **Review IAM permissions** - use least privilege
6. **Rotate credentials** regularly (90 days recommended)

## Support

If you encounter issues:
1. Check this guide first
2. Review `README.md` for detailed documentation
3. Check `SECURITY_AUDIT_REPORT.md` for security considerations
4. Enable verbose logging: `--verbose`
5. Review logs in `logs/auc.log`

---

**Ready to start?** Run `./scripts/setup.sh` and then configure `config/config.yaml`!
