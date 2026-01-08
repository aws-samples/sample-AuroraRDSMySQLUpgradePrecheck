# MySQL 5.7 to 8.0 Upgrade Assessment Tool

A comprehensive, enterprise-grade tool for assessing MySQL 5.7 database readiness for upgrading to MySQL 8.0. This tool works with both Amazon Aurora MySQL and Amazon RDS MySQL instances.

## What Does This Tool Do?

This tool performs **20+ automated compatibility checks** on your MySQL 5.7 databases to identify potential issues before upgrading to MySQL 8.0. It generates a professional, enterprise-grade HTML report with:

- **Executive Dashboard** with readiness scores
- **Risk Assessment Matrix** for prioritizing fixes
- **Detailed Findings** for each compatibility check
- **AWS Blue/Green Deployment** guidance and resources
- **Actionable Recommendations** with step-by-step remediation

## Prerequisites

### AWS Requirements
- AWS Account with RDS MySQL 5.7 or Aurora MySQL 5.7 instances
- IAM permissions to:
  - Read RDS/Aurora metadata (`rds:Describe*`)
  - Access Secrets Manager (`secretsmanager:GetSecretValue`)
- AWS CLI configured or AWS credentials available

### Local Environment
- **Python 3.8+**
- **Network Access** to your RDS/Aurora instances
- **AWS Region** where your databases are located

### Database Requirements
- MySQL 5.7 instance (Aurora or RDS)
- Database credentials stored in AWS Secrets Manager
- Network connectivity from your machine to the database

## Quick Start

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/aurora-upgrade-checker.git
cd aurora-upgrade-checker
```

### Step 2: Run Setup Script

```bash
./scripts/setup.sh
```

This will:
- Create Python virtual environment
- Install all dependencies
- Set up directory structure
- Verify AWS CLI installation

### Step 3: Configure AWS Credentials

```bash
# Option 1: AWS CLI
aws configure

# Option 2: Environment Variables
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_SESSION_TOKEN="your-session-token"  # If using temporary credentials
```

### Step 4: Discover Your Databases (Optional)

```bash
./scripts/discover_clusters.sh
```

This helper script will list all MySQL 5.7 instances in your AWS account.

### Step 5: Run the Assessment

```bash
source venv/bin/activate
python run_assessment.py --cluster your-cluster-name --region us-east-2
```

### Step 6: View the Report

```bash
open reports/upgrade_assessment.html
```

## Detailed Usage

### Command-Line Options

```bash
python run_assessment.py [OPTIONS]

Options:
  --cluster CLUSTER      Database cluster or instance identifier (required)
  --region REGION        AWS region (default: us-east-1)
  --profile PROFILE      AWS CLI profile name (optional)
  --verbose             Enable verbose logging
  -h, --help            Show help message
```

### Examples

**Assess a specific Aurora cluster:**
```bash
python run_assessment.py --cluster my-aurora-cluster --region us-west-2
```

**Assess an RDS instance with custom profile:**
```bash
python run_assessment.py --cluster my-rds-instance --region eu-west-1 --profile prod
```

**Run with verbose logging:**
```bash
python run_assessment.py --cluster my-cluster --region us-east-1 --verbose
```

## Understanding the Report

### Executive Dashboard
- **Readiness Score**: 0-100% indicating upgrade readiness
- **Critical Issues**: Must-fix items before upgrade
- **Warnings**: Items to address for optimal performance
- **Passed Checks**: Areas ready for upgrade

### Risk Assessment Matrix
- **🔴 Critical Risk**: Blocking issues that prevent upgrade
- **🟡 Medium Risk**: Warnings that should be addressed
- **🟢 Low Risk**: Areas ready for upgrade

### Detailed Findings
Each check includes:
- **Status**: Red (critical), Amber (warning), or Green (passed)
- **Issues**: Specific problems found
- **Recommendations**: Step-by-step remediation guidance

### Upgrade Strategy
- AWS RDS Blue/Green Deployment guidance
- Prerequisites checklist
- Step-by-step deployment process
- AWS documentation links

## Compatibility Checks Performed

The tool performs 20+ checks including:

1. **Version Compatibility** - Current version validation
2. **Reserved Keywords** - MySQL 8.0 keyword conflicts
3. **Deprecated Features** - Removed features in MySQL 8.0
4. **Authentication Methods** - Deprecated auth plugins
5. **Character Sets** - Character set compatibility
6. **Storage Engines** - Storage engine support
7. **SQL Modes** - SQL mode compatibility
8. **Partitioning** - Partitioning limitations
9. **Spatial Data** - SRID requirements
10. **Foreign Keys** - FK constraint compatibility
11. **Triggers & Stored Procedures** - Routine compatibility
12. **Views** - View definition compatibility
13. **JSON Columns** - JSON data type usage
14. **Auto-Increment** - Auto-increment exhaustion
15. **Duplicate Indexes** - Redundant indexes
16. **Parameters** - Deprecated parameters
17. **InnoDB Settings** - InnoDB compatibility
18. **Query Cache** - Removed feature warnings
19. **Binary Logging** - Replication settings
20. **Collations** - Collation compatibility

## Configuration

### AWS Secrets Manager Setup

Your database credentials should be stored in AWS Secrets Manager. The tool automatically discovers credentials based on your RDS resource ID.

**Secret format:**
```json
{
  "username": "admin",
  "password": "your-secure-password"
}
```

### Custom Configuration (Optional)

Create `config/config.yaml`:

```yaml
aws:
  region: us-east-2
  profile: default

database:
  connect_timeout: 30
  read_timeout: 300

report:
  output_dir: reports
  format: html
```

## Security & Credentials

### How Credentials Are Handled

1. **AWS Credentials**: Uses standard AWS credential chain
   - IAM roles (recommended for EC2/Lambda)
   - AWS CLI configuration
   - Environment variables

2. **Database Credentials**: Retrieved from AWS Secrets Manager
   - Never stored locally
   - Encrypted in transit
   - Automatic rotation support

### Required IAM Permissions

```json
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
```

## Output Files

After running the assessment, you'll find:

```
reports/
├── upgrade_assessment.html      # Interactive HTML report
├── upgrade_assessment.json      # Machine-readable JSON
└── executive_summary.md         # Markdown summary
```

- **HTML Report**: Open in any web browser for interactive viewing
- **JSON Report**: Use for automation/parsing
- **Executive Summary**: Quick overview in markdown format

## Troubleshooting

### Common Issues

**Issue**: Cannot connect to database
```
Solution: Verify:
1. Security group allows inbound from your IP
2. Database is publicly accessible (if running locally)
3. VPN connection is active (if using private subnets)
```

**Issue**: Credentials not found
```
Solution:
1. Check Secrets Manager for RDS resource ID
2. Verify IAM permissions for Secrets Manager
3. Confirm AWS region matches your database
```

**Issue**: Import errors
```
Solution:
1. Activate virtual environment: source venv/bin/activate
2. Reinstall dependencies: pip install -r requirements.txt
```

**Issue**: No databases found
```
Solution:
1. Verify AWS credentials are configured
2. Check --region parameter matches your database
3. Confirm you have rds:Describe* permissions
```

See `docs/TROUBLESHOOTING.md` for more solutions.

## Best Practices

### Before Running the Tool
1.  Take a snapshot of your database
2.  Run during low-traffic period
3.  Review database size (large databases take longer)
4.  Ensure stable network connection

### After Getting Results
1.  Address all Critical (Red) issues first
2.  Plan for Warning (Amber) issues
3.  Test fixes in development environment
4.  Re-run assessment after fixes
5.  Use AWS Blue/Green deployment for upgrade

### Upgrade Readiness Scores
- **80-100%**: Ready for upgrade
- **60-79%**: Address warnings, then proceed
- **Below 60%**: Fix critical issues before considering upgrade

## Additional Documentation

- [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) - Detailed deployment instructions
- [`USER_GUIDE.md`](USER_GUIDE.md) - Comprehensive user guide
- [`docs/FAQ.md`](docs/FAQ.md) - Frequently asked questions
- [`docs/AWS_SETUP.md`](docs/AWS_SETUP.md) - AWS prerequisites and setup
- [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) - Common issues and solutions

## Upgrade Path

Once all issues are resolved:

1. **Validate Fixes**: Re-run assessment (target 80%+ readiness)
2. **Backup**: Create manual snapshot
3. **Test Environment**: Validate in non-production first
4. **Blue/Green Deployment**: Use AWS RDS Blue/Green feature
5. **Monitor**: Watch metrics during and after upgrade
6. **Rollback Plan**: Keep blue environment for quick revert

## Authors

**Authored by:** Kiran mayee Mulupuru, Sr. Database Specialist TAM
- **Email:** kiranmam@amazon.com
- **Role:** Senior Database Specialist, Technical Account Manager

## Reviewers & Contributors

**Reviewed by:** Vijay Karumajji, Prin WW SSA MySQL & Abhimanyu Tomar, Sr.STAM-DB (NAMER)

**Contributors:** Jigar Mandli, ESL TAM

---

## Support

For issues or questions:
- 📖 Check documentation in `docs/` directory
- 🐛 Report bugs via GitHub Issues
- 💬 Contact your AWS support team
- 📧 Tool author: kiranmam@amazon.com

## License

Copyright © 2025. All rights reserved.

---

**Version**: 1.0.0
**Last Updated**: 2025-12-12
**Minimum Python**: 3.8+
**AWS Services**: RDS MySQL, Aurora MySQL, Secrets Manager
