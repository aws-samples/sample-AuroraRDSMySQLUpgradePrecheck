# MySQL 5.7 to 8.0 Upgrade Assessment
Generated: 2026-01-21 21:57:15

## Overview
- Total Databases: 2
- Databases Needing Upgrade: 2
- Total Issues: 52
- Blocking Issues: 41
- Warnings: 0

## Overall Status: RED

## Immediate Actions Required
- <strong>Deprecated Features Check</strong> (11 issues): 
- <strong>Parameter Compatibility Check</strong> (3 issues): Aurora automatically manages parameter group compatibility during upgrades - you will be required to use a MySQL 8.0-compatible parameter group
- <strong>Deprecated Features Check</strong> (11 issues): 
- <strong>Parameter Compatibility Check</strong> (16 issues): Remove or replace parameters that will be removed in 8.0

## Upgrade Order
- Aurora cluster ams-5740212 (5.7.mysql_aurora.2.12.0)
- RDS instance rdsmysql5744 (5.7.44-rds.20240408)

## Common Issues Found
- Found 1 users with mysql_native_password (informational)
- Parameter will be removed in 8.0: query_cache_type
- Deprecated system variable in use: multi_range_count
- Deprecated system variable in use: secure_auth
- Parameter will be removed in 8.0: sync_frm
- Server character set: latin1
- Deprecated system variable in use: innodb_file_format
- Parameter will be removed in 8.0: innodb_support_xa
- Parameter will be removed in 8.0: max_tmp_tables
- Parameter will be removed in 8.0: innodb_file_format_check
- Deprecated system variable in use: innodb_file_format_max
- Server default character set is 'latin1' (MySQL 8.0 defaults to utf8mb4)
- Deprecated system variable in use: query_cache_size
- Parameter will be removed in 8.0: innodb_file_format
- Server collation: latin1_swedish_ci
- Deprecated system variable in use: query_cache_type
- Critical parameter log_bin_trust_function_creators not set to required value 1
- binlog_format is 'MIXED' - ROW format is strongly recommended for MySQL 8.0
- Parameter will be removed in 8.0: query_cache_size
- Deprecated system variable in use: tx_read_only
- Critical parameter binlog_format not set to required value ROW
- Parameter will be removed in 8.0: log_warnings
- Deprecated system variable in use: tx_isolation
- Parameter will be removed in 8.0: innodb_file_format_max
- Current version 5.7.40 needs upgrade to 8.0
- Parameter will be removed in 8.0: secure_auth
- Parameter innodb_autoinc_lock_mode default changing to 2
- Current version 5.7.44-rds.20240408-log needs upgrade to 8.0
- Query cache is enabled but will be removed in 8.0
- Parameter will be removed in 8.0: multi_range_count
- Parameter will be removed in 8.0: innodb_large_prefix
- Deprecated system variable in use: innodb_file_format_check

## Recommendations

### Pre-Upgrade Tasks
- Update parameter groups with recommended settings
- Take full backup of all databases
- Convert character sets to utf8mb4 where needed
- Make sure that the instance have enough resources (CPU, Memory, IOPS, storage) for the upgrade process
- Ensure there are no long-running transaction
- Make sure HLL is not high

### During Upgrade
- Follow upgrade order as specified
- Test each upgrade in non-production first
- Monitor replication lag during upgrades
- Verify application compatibility
- Have rollback plan ready

### Post-Upgrade Tasks
- Verify all stored procedures and views
- Check application performance
- Update monitoring and alerts
- Review and update backup strategies
- Document changes and lessons learned