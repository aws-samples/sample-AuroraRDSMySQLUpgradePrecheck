# Frequently Asked Questions (FAQ)

## General Questions

### What does this tool do?
This tool assesses your MySQL 5.7 database (RDS or Aurora) for compatibility issues before upgrading to MySQL 8.0. It performs 20+ automated checks and generates a comprehensive report with actionable recommendations.

### Does this tool modify my database?
No. The tool only performs read-only queries on your database. It does not execute any DDL (Data Definition Language) or DML (Data Manipulation Language) statements that would modify your data or schema.

### How long does an assessment take?
Typical assessment times:
- Small databases (<10 GB): 2-5 minutes
- Medium databases (10-100 GB): 5-15 minutes
- Large databases (>100 GB): 15-30 minutes

The duration depends on database size, number of tables, and network latency.

### Can I run this on a production database?
Yes, the tool is safe to run on production databases as it only performs read-only queries. However, we recommend:
- Running during low-traffic periods
- Testing on a non-production environment first
- Monitoring database performance during the assessment

---

## AWS and Credentials

### How does the tool access my database credentials?
The tool retrieves credentials from AWS Secrets Manager using your RDS resource ID. It follows this priority:
1. AWS Secrets Manager (recommended)
2. Environment variables (fallback)
3. AWS CLI configuration

### What IAM permissions are required?
Minimum required permissions:
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

### Can I use this tool with databases in private VPCs?
Yes, but you need:
- VPN connection to the VPC, OR
- EC2 instance in the same VPC to run the tool, OR
- Bastion host with port forwarding

### Does this tool work with RDS Proxy?
Yes, the tool works with RDS Proxy endpoints. Use the proxy endpoint as your database endpoint.

---

## Assessment and Reports

### What compatibility checks are performed?
The tool performs 20+ checks including:
- Reserved keywords conflicts
- Deprecated authentication methods
- Character set compatibility
- Spatial data SRID requirements
- Auto-increment exhaustion
- Deprecated SQL modes
- Storage engine compatibility
- And more...

See README.md for the complete list.

### What do the readiness scores mean?
- **80-100%**: Ready for upgrade with minor fixes
- **60-79%**: Address warnings before upgrading
- **Below 60%**: Fix critical issues before considering upgrade

### How should I prioritize the issues found?
Follow this priority order:
1. **Critical (Red)** - Must fix before upgrade (blocking issues)
2. **Warning (Amber)** - Should fix for optimal performance
3. **Passed (Green)** - No action needed

### Can I run multiple assessments on the same database?
Yes, you can run the tool multiple times. This is useful for:
- Tracking remediation progress
- Verifying fixes
- Regular compliance checks

The tool generates timestamped reports so you can compare results over time.

---

## Installation and Setup

### What are the system requirements?
- Python 3.8 or higher
- AWS CLI configured
- Network access to your RDS/Aurora instances
- 100 MB free disk space

### Do I need to install MySQL client?
No, the tool uses the Python MySQL connector library and doesn't require a separate MySQL client installation.

### Can I run this on Windows?
The tool is primarily designed for Unix-based systems (macOS, Linux). For Windows:
- Use WSL (Windows Subsystem for Linux)
- Use Git Bash
- Modify scripts for PowerShell (advanced users)

### How do I update the tool?
```bash
cd mysql-upgrade-assessment-tool
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

---

## Troubleshooting

### Connection refused or timeout errors
Check:
1. Security group allows inbound from your IP (port 3306)
2. Database is publicly accessible (if running locally)
3. VPN connection is active (for private VPCs)
4. Database endpoint is correct

### "Credentials not found" error
Verify:
1. Secret exists in AWS Secrets Manager
2. Secret name matches RDS resource ID pattern: `rds!cluster-*` or `rds!db-*`
3. IAM permissions allow `secretsmanager:GetSecretValue`
4. AWS region matches your database region

### "Access denied" errors
This could mean:
1. Database user doesn't have SELECT permissions
2. IAM role/user lacks required AWS permissions
3. Security group or network ACL blocking connection

### Python import errors
```bash
# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## Upgrade Process

### After fixing all issues, how do I upgrade?
We recommend using AWS RDS Blue/Green deployment:
1. Fix all critical issues identified by the tool
2. Re-run assessment to verify (target 80%+ readiness)
3. Create manual database snapshot
4. Use Blue/Green deployment for zero-downtime upgrade
5. Test thoroughly on green environment
6. Switch traffic to green environment
7. Monitor for 24-48 hours before deleting blue environment

See DEPLOYMENT_GUIDE.md for detailed steps.

### Should I test the upgrade first?
Absolutely! Always test in a non-production environment:
1. Restore snapshot to test environment
2. Run the assessment tool
3. Fix identified issues
4. Perform test upgrade
5. Validate application compatibility
6. Only then proceed with production

### Can I rollback if something goes wrong?
Yes, with Blue/Green deployment:
- The blue (old) environment remains available
- You can switch back instantly if issues arise
- Keep blue environment for 24-48 hours as safety net

### Do I need to upgrade my application code?
Possibly. MySQL 8.0 has some behavior changes that may affect your application:
- Changes in default authentication plugin
- Deprecated features removed
- SQL mode changes
- Character set handling differences

Test your application thoroughly before production upgrade.

---

## Performance and Scaling

### Will this tool impact my database performance?
The tool runs read-only queries on information_schema and performance_schema. Impact is minimal, but:
- May cause slight CPU increase
- Recommended to run during low-traffic periods
- Monitor with CloudWatch during assessment

### Can I run this on multiple databases simultaneously?
Yes, but run each assessment in a separate terminal session:
```bash
# Terminal 1
python run_assessment.py --cluster cluster-1 --region us-east-1

# Terminal 2
python run_assessment.py --cluster cluster-2 --region us-west-2
```

### Can this tool assess hundreds of databases?
Yes, but consider:
- Running assessments sequentially to avoid AWS API throttling
- Using a script to automate multiple assessments
- Running on EC2 in the same region for better performance

---

## Support and Community

### Where can I report bugs?
Report issues on our GitHub repository:
- Create a new issue with detailed description
- Include error messages and logs
- Specify your environment (OS, Python version, AWS region)

### How can I contribute?
We welcome contributions:
- Fork the repository
- Create a feature branch
- Submit a pull request
- Follow coding standards and include tests

### Is there a commercial support option?
For enterprise support, contact AWS Support or your account team.

### Can I use this tool for other MySQL versions?
This tool is specifically designed for MySQL 5.7 to 8.0 upgrades. For other versions:
- 5.6 to 5.7: Some checks may still be relevant
- 8.0 to 8.x: Use MySQL's built-in upgrade checker
- MariaDB: Not supported (different compatibility requirements)

---

## Security and Privacy

### Does this tool send data anywhere?
No. The tool:
- Runs entirely in your environment
- Does not transmit data to external services
- Reports are generated locally only

### What credentials are stored?
None. Credentials are:
- Retrieved from AWS Secrets Manager at runtime
- Never written to disk
- Not included in reports or logs

### Can I audit the code?
Yes, the code is open source. You can:
- Review all source files
- Run security scans (Bandit, pip-audit)
- Modify for your security requirements

---

**Last Updated**: 2025-12-12
**Version**: 1.0.0
