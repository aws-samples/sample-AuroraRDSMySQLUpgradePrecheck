import mysql.connector
from datetime import datetime
import logging

# Set up logger
logger = logging.getLogger(__name__)


class AuroraUpgradeChecker:
    def __init__(self):
        self.checks = [
            self._check_schema_info,
            self._check_version_compatibility,
            self._check_character_sets,
            self._check_binlog_settings,
            self._check_deprecated_features,
            self._check_parameters,
            self._check_foreign_keys,
            self._check_triggers_views,
            self._check_new_features_compatibility,
            # New checks for comprehensive upgrade assessment
            self._check_reserved_keywords,
            self._check_partition_compatibility,
            self._check_user_privileges,
            self._check_json_usage,
            self._check_stored_routine_complexity,
            self._check_spatial_srid,
            self._check_functional_index_opportunities,
            self._check_index_statistics,
            self._check_autoinc_exhaustion,
            self._check_replication_topology,
            self._check_connection_configuration
        ]
        self.db_info = None  # Store db_info for checks to access

    def run_checks(self, db_info, credentials):
        conn = None
        try:
            # Store db_info for access by individual checks
            self.db_info = db_info

            conn = self._get_connection(db_info, credentials)
            results = {
                'cluster_id': db_info['identifier'],
                'version': db_info['version'],
                'engine': db_info['engine'],
                'type': db_info.get('type', 'AURORA'),
                'checks': [],
                'summary': {
                    'status': 'GREEN',
                    'total_issues': 0,
                    'blocking_issues': 0,
                    'warnings': 0
                }
            }

            for check in self.checks:
                try:
                    check_result = check(conn)
                    results['checks'].append(check_result)
                    
                    if check_result['status'] == 'RED':
                        results['summary']['status'] = 'RED'
                        results['summary']['blocking_issues'] += len(check_result.get('issues', []))
                    elif check_result['status'] == 'AMBER' and results['summary']['status'] != 'RED':
                        results['summary']['status'] = 'AMBER'
                        results['summary']['warnings'] += len(check_result.get('issues', []))

                    if check_result['status'] != 'GREEN':
                        results['summary']['total_issues'] += len(check_result.get('issues', []))
                except Exception as check_error:
                    print(f"Error in check {check.__name__}: {str(check_error)}")
                    results['checks'].append({
                        'name': check.__name__.replace('_check_', '').replace('_', ' ').title(),
                        'status': 'ERROR',
                        'issues': [str(check_error)],
                        'recommendations': ['Check database permissions and connectivity']
                    })

            return results
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': str(e)
            }
        finally:
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.exception("Error closing connection: %s", e)

    def _get_connection(self, db_info, credentials):
        return mysql.connector.connect(
            host=db_info['endpoint'],
            user=credentials['user'],
            password=credentials['password'],
            port=credentials['port'],
            connection_timeout=10
        )

    def _check_schema_info(self, conn):
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Get schema sizes and table counts
            cursor.execute("""
                SELECT 
                    table_schema,
                    COUNT(DISTINCT table_name) as table_count,
                    SUM(data_length + index_length) / 1024 / 1024 as size_mb,
                    GROUP_CONCAT(DISTINCT engine) as engines,
                    GROUP_CONCAT(DISTINCT table_collation) as collations
                FROM information_schema.tables
                WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
                GROUP BY table_schema
            """)
            schemas = cursor.fetchall()

            # Get detailed table information
            cursor.execute("""
                SELECT 
                    table_schema,
                    table_name,
                    engine,
                    table_rows,
                    data_length + index_length as size_bytes,
                    table_collation,
                    create_time,
                    update_time
                FROM information_schema.tables
                WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
                AND table_type = 'BASE TABLE'
                ORDER BY (data_length + index_length) DESC
            """)
            tables = cursor.fetchall()

            result = {
                'name': 'Schema Information',
                'description': 'Analyzes database schemas, table counts, sizes, and storage engines to assess overall database complexity',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'schemas': schemas,
                    'tables': tables,
                    'summary': {
                        'total_schemas': len(schemas),
                        'total_tables': len(tables),
                        'total_size_mb': sum(schema['size_mb'] for schema in schemas if schema['size_mb']),
                        'engines_used': set(engine 
                                         for schema in schemas 
                                         if schema['engines']
                                         for engine in schema['engines'].split(','))
                    }
                }
            }

            # Check for potential issues
            large_tables = [t for t in tables if t['size_bytes'] and t['size_bytes'] > 10 * 1024 * 1024 * 1024]  # 10GB
            if large_tables:
                result['status'] = 'AMBER'
                result['issues'].extend([
                    f"Large table detected: {t['table_schema']}.{t['table_name']} "
                    f"({t['size_bytes'] / 1024 / 1024 / 1024:.2f} GB)"
                    for t in large_tables
                ])
                result['recommendations'].extend([
                    "Consider partitioning large tables before upgrade",
                    f"Total large tables (>10GB): {len(large_tables)}",
                    "Review table statistics and index usage"
                ])

            return result
        except Exception as e:
            raise Exception(f"Schema information check failed: {str(e)}")
        finally:
            if cursor:
                cursor.close()

    def _check_version_compatibility(self, conn):
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT 
                    @@version as version,
                    @@version_comment as version_comment,
                    @@version_compile_os as version_compile_os,
                    @@version_compile_machine as version_compile_machine,
                    @@character_set_server as charset_server,
                    @@collation_server as collation_server
            """)
            version_info = cursor.fetchone()

            result = {
                'name': 'Version Compatibility',
                'description': 'Validates current MySQL 5.7 version and identifies version-specific compatibility issues for MySQL 8.0 upgrade',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': version_info
            }

            if '5.7' in version_info['version']:
                result['status'] = 'AMBER'
                result['issues'].extend([
                    f"Current version {version_info['version']} needs upgrade to 8.0",
                    f"Server character set: {version_info['charset_server']}",
                    f"Server collation: {version_info['collation_server']}"
                ])
                result['recommendations'].extend([
                    "Plan upgrade to MySQL 8.0",
                    "Review MySQL 8.0 compatibility requirements",
                    "Consider using Aurora MySQL 8.0 parallel query feature",
                    "Review character set and collation settings for 8.0 compatibility"
                ])

            return result
        except Exception as e:
            raise Exception(f"Version check failed: {str(e)}")
        finally:
            if cursor:
                cursor.close()

    def _check_character_sets(self, conn):
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)

            # Get server-level character set configuration
            cursor.execute("""
                SELECT
                    @@character_set_server as character_set_server,
                    @@collation_server as collation_server,
                    @@character_set_database as character_set_database,
                    @@collation_database as collation_database
            """)
            server_config = cursor.fetchone()

            # Get schema character sets
            cursor.execute("""
                SELECT
                    schema_name,
                    default_character_set_name,
                    default_collation_name
                FROM information_schema.schemata
                WHERE schema_name NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
            """)
            schema_charsets = cursor.fetchall() or []

            # Get detailed character set information for tables and columns
            # IMPORTANT: Only include columns that actually have character sets (exclude numeric types)
            cursor.execute("""
                SELECT
                    t.table_schema,
                    t.table_name,
                    t.table_collation,
                    c.column_name,
                    c.character_set_name,
                    c.collation_name,
                    c.column_type,
                    c.data_type
                FROM information_schema.tables t
                JOIN information_schema.columns c
                    ON t.table_schema = c.table_schema
                    AND t.table_name = c.table_name
                WHERE c.character_set_name IS NOT NULL
                AND c.data_type IN ('char', 'varchar', 'text', 'tinytext', 'mediumtext', 'longtext', 'enum', 'set')
                AND t.table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
                AND t.table_type = 'BASE TABLE'
                ORDER BY t.table_schema, t.table_name, c.column_name
            """)
            all_charset_columns = cursor.fetchall() or []

            result = {
                'name': 'Character Set Check',
                'description': 'Reviews character set configuration and identifies compatibility considerations for MySQL 8.0',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'server_config': server_config,
                    'schema_charsets': schema_charsets,
                    'utf8mb3_columns': [],
                    'latin1_columns': [],
                    'other_charset_columns': [],
                    'summary': {
                        'total_columns_reviewed': len(all_charset_columns),
                        'utf8mb3_count': 0,
                        'latin1_count': 0,
                        'utf8mb4_count': 0,
                        'other_count': 0
                    }
                }
            }

            # Categorize columns by charset
            utf8mb3_columns = []
            latin1_columns = []
            other_charset_columns = []

            for col in all_charset_columns:
                charset = col.get('character_set_name', '')

                if charset in ['utf8', 'utf8mb3']:
                    utf8mb3_columns.append(col)
                    result['details']['summary']['utf8mb3_count'] += 1
                elif charset == 'latin1':
                    latin1_columns.append(col)
                    result['details']['summary']['latin1_count'] += 1
                elif charset == 'utf8mb4':
                    result['details']['summary']['utf8mb4_count'] += 1
                else:
                    other_charset_columns.append(col)
                    result['details']['summary']['other_count'] += 1

            result['details']['utf8mb3_columns'] = utf8mb3_columns
            result['details']['latin1_columns'] = latin1_columns
            result['details']['other_charset_columns'] = other_charset_columns

            # Check for utf8/utf8mb3 usage (AMBER - not blocking)
            if utf8mb3_columns:
                result['status'] = 'AMBER'
                result['issues'].append(
                    f"Found {len(utf8mb3_columns)} columns using utf8/utf8mb3 character set"
                )
                result['recommendations'].extend([
                    "",
                    "UTF8/UTF8MB3 Considerations:",
                    "- utf8mb3 is not removed in MySQL 8.0 and remains usable through MySQL 8.4",
                    "- MySQL 8.0 changes the default charset to utf8mb4, but existing utf8mb3 data is unaffected",
                    "- Client library upgrades may be required (older clients don't recognize utf8mb3 keyword)",
                    "- You may continue using utf8mb3 if you accept the 3-byte UTF-8 limitation",
                    "",
                    "IMPORTANT: If converting to utf8mb4:",
                    "- Perform charset conversion BEFORE or AFTER the MySQL upgrade, never during",
                    "- Test thoroughly before conversion",
                    "- Conversion command example:",
                    "  ALTER TABLE <table> CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
                ])

            # Check for latin1 usage (Informational only - not a blocker)
            if latin1_columns:
                if result['status'] == 'GREEN':
                    result['status'] = 'AMBER'
                result['issues'].append(
                    f"Found {len(latin1_columns)} columns using latin1 character set (informational)"
                )
                result['recommendations'].extend([
                    "",
                    "LATIN1 Considerations:",
                    "- latin1 is fully supported in MySQL 8.0 and there are no plans to deprecate it",
                    "- If latin1 usage is intentional for your application, no action is required",
                    "- MySQL 8.0 changes the default server charset to utf8mb4, but this only affects NEW objects",
                    "- Existing latin1 schemas and tables are unaffected and continue to work",
                    "",
                    "Optional: If you want to standardize on utf8mb4:",
                    "- Perform conversion BEFORE or AFTER upgrade, never during",
                    "- Only convert if your application requirements warrant it"
                ])

            # Note about default charset changes
            if server_config:
                server_charset = server_config.get('character_set_server', '')
                if server_charset in ['latin1', 'utf8', 'utf8mb3']:
                    if result['status'] == 'GREEN':
                        result['status'] = 'AMBER'
                    result['issues'].append(
                        f"Server default character set is '{server_charset}' (MySQL 8.0 defaults to utf8mb4)"
                    )
                    result['recommendations'].extend([
                        "",
                        "Default Character Set Note:",
                        "- MySQL 8.0 changes default character_set_server to utf8mb4",
                        "- This only affects NEW objects created without explicit charset specification",
                        "- Existing schemas, tables, and columns are NOT affected",
                        "- No pre-upgrade action is required",
                        "- Post-upgrade: Set character_set_server explicitly in parameter group if needed"
                    ])

            # If everything is utf8mb4, give positive feedback
            if result['status'] == 'GREEN':
                result['recommendations'].append(
                    "Character set configuration is optimal for MySQL 8.0 (utf8mb4 in use)"
                )

            return result
        except Exception as e:
            raise Exception(f"Character set check failed: {str(e)}")
        finally:
            if cursor:
                cursor.close()

    def _check_binlog_settings(self, conn):
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT 
                    @@binlog_format as binlog_format,
                    @@binlog_row_image as binlog_row_image,
                    @@gtid_mode as gtid_mode,
                    @@enforce_gtid_consistency as enforce_gtid_consistency,
                    @@log_bin as log_bin,
                    @@binlog_rows_query_log_events as binlog_rows_query_log_events,
                    @@binlog_transaction_dependency_tracking as dependency_tracking,
                    @@sync_binlog as sync_binlog,
                    @@innodb_flush_log_at_trx_commit as flush_log_at_trx_commit
            """)
            settings = cursor.fetchone()

            result = {
                'name': 'Binary Log Settings',
                'description': 'Verifies binary logging configuration and format requirements for MySQL 8.0 replication compatibility',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'current_settings': settings,
                    'required_changes': [],
                    'optional_changes': []
                }
            }

            # Check critical settings
            if settings['binlog_format'] != 'ROW':
                # ROW format is strongly recommended for MySQL 8.0 but not absolutely required
                # It becomes critical if using certain features (replication, certain storage engines)
                if result['status'] == 'GREEN':
                    result['status'] = 'AMBER'
                result['issues'].append(
                    f"binlog_format is '{settings['binlog_format']}' - ROW format is strongly recommended for MySQL 8.0"
                )
                result['details']['required_changes'].append({
                    'parameter': 'binlog_format',
                    'current': settings['binlog_format'],
                    'required': 'ROW',
                    'reason': 'Required for safe replication and certain MySQL 8.0 features'
                })
                result['recommendations'].extend([
                    "",
                    "binlog_format Clarification:",
                    "- ROW format is required if using:",
                    "  * Replication with row-based triggers",
                    "  * NDB Cluster",
                    "  * Group Replication",
                    "  * Certain MySQL 8.0 features",
                    "- If not using these features, STATEMENT or MIXED may be acceptable",
                    "- ROW format is generally recommended for data consistency and safety"
                ])

            if settings['gtid_mode'] != 'ON':
                result['status'] = 'AMBER'
                result['issues'].append(
                    f"GTID mode is {settings['gtid_mode']}, recommended to be ON"
                )
                result['details']['required_changes'].append({
                    'parameter': 'gtid_mode',
                    'current': settings['gtid_mode'],
                    'required': 'ON'
                })

            # Check optional settings
            if settings['sync_binlog'] != 1:
                result['issues'].append(
                    f"sync_binlog is set to {settings['sync_binlog']}, recommended value is 1"
                )
                result['details']['optional_changes'].append({
                    'parameter': 'sync_binlog',
                    'current': settings['sync_binlog'],
                    'recommended': 1
                })

            if settings['flush_log_at_trx_commit'] != 1:
                result['issues'].append(
                    f"innodb_flush_log_at_trx_commit is {settings['flush_log_at_trx_commit']}, "
                    "recommended value is 1"
                )
                result['details']['optional_changes'].append({
                    'parameter': 'innodb_flush_log_at_trx_commit',
                    'current': settings['flush_log_at_trx_commit'],
                    'recommended': 1
                })

            if result['issues']:
                result['recommendations'].extend([
                    "Update parameter group with the following changes:",
                    "Required changes:",
                    *[f"  - Set {change['parameter']} = {change.get('required') or change.get('recommended')}"
                      for change in result['details']['required_changes']],
                    "Optional changes for better durability:",
                    *[f"  - Consider setting {change['parameter']} = {change['recommended']}"
                      for change in result['details']['optional_changes']],
                    "Review replication topology before making changes",
                    "Test application performance with new settings",
                    "Plan for potential replication lag during transition"
                ])

            return result
        except Exception as e:
            raise Exception(f"Binary log check failed: {str(e)}")
        finally:
            if cursor:
                cursor.close()

    def _check_deprecated_features(self, conn):
        cursor = None
        try:
            result = {
                'name': 'Deprecated Features Check',
                'description': 'Detects deprecated functions, authentication methods, and SQL modes that are removed in MySQL 8.0',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'authentication': {
                        'status': 'GREEN',
                        'issues': [],
                        'affected_users': []
                    },
                    'functions_and_syntax': {
                        'status': 'GREEN',
                        'issues': [],
                        'affected_objects': []
                    },
                    'system_variables': {
                        'status': 'GREEN',
                        'issues': [],
                        'deprecated_vars': []
                    },
                    'query_cache': {
                        'status': 'GREEN',
                        'issues': [],
                        'settings': []
                    },
                    'innodb_features': {
                        'status': 'GREEN',
                        'issues': [],
                        'deprecated_settings': []
                    },
                    'data_types': {
                        'status': 'GREEN',
                        'issues': [],
                        'temporal_columns': [],
                        'spatial_columns': []
                    },
                    'sql_modes': {
                        'status': 'GREEN',
                        'issues': [],
                        'deprecated_modes': []
                    },
                    'summary': {
                        'total_issues': 0,
                        'critical_issues': 0,
                        'warnings': 0
                    }
                }
            }

            cursor = conn.cursor(dictionary=True)

            # 1. Authentication Methods Check
            try:
                # Check for truly deprecated plugins (RED)
                cursor.execute("""
                    SELECT user, host, plugin, authentication_string
                    FROM mysql.user
                    WHERE plugin IN ('mysql_old_password')
                """)
                truly_deprecated_auth = cursor.fetchall()
                if truly_deprecated_auth:
                    result['details']['authentication']['status'] = 'RED'
                    result['details']['authentication']['affected_users'] = truly_deprecated_auth
                    result['issues'].append(
                        f"Found {len(truly_deprecated_auth)} users with mysql_old_password (removed in MySQL 8.0)"
                    )
                    result['status'] = 'RED'
                    result['details']['summary']['critical_issues'] += 1

                # Check for mysql_native_password (informational only - AMBER)
                cursor.execute("""
                    SELECT user, host, plugin, authentication_string
                    FROM mysql.user
                    WHERE plugin IN ('mysql_native_password')
                    AND user NOT IN ('mysql.sys', 'mysql.session', 'mysql.infoschema', 'rdsadmin')
                """)
                native_password_users = cursor.fetchall()
                if native_password_users:
                    if result['status'] == 'GREEN':
                        result['status'] = 'AMBER'
                    result['details']['authentication']['native_password_users'] = native_password_users
                    result['issues'].append(
                        f"Found {len(native_password_users)} users with mysql_native_password (informational)"
                    )
                    result['details']['summary']['warnings'] += 1
            except Exception as e:
                result['issues'].append(f"Could not check authentication methods: {str(e)}")

            # 2. Deprecated Functions and Syntax
            deprecated_functions = [
                ('PASSWORD', 'Use SHA2() instead'),
                ('OLD_PASSWORD', 'Remove usage'),
                ('ENCODE', 'Use AES_ENCRYPT()'),
                ('DECODE', 'Use AES_DECRYPT()'),
                ('ENCRYPT', 'Use SHA2() or AES_ENCRYPT()'),
                ('DES_ENCRYPT', 'Use AES_ENCRYPT()'),
                ('DES_DECRYPT', 'Use AES_DECRYPT()')
            ]

            for func, replacement in deprecated_functions:
                # Build a safe parameterized query. `func` is from an internal whitelist above.
                func_pattern = rf"{func}\s*\("
                excluded_schemas = ['mysql', 'sys', 'information_schema', 'performance_schema']
                placeholders = ','.join(['%s'] * len(excluded_schemas))
                sql = f"""
                    SELECT 
                        ROUTINE_SCHEMA, 
                        ROUTINE_NAME, 
                        ROUTINE_TYPE,
                        CREATED,
                        LAST_ALTERED
                    FROM information_schema.routines 
                    WHERE ROUTINE_DEFINITION REGEXP %s
                    AND ROUTINE_SCHEMA NOT IN ({placeholders})
                """
                params = [func_pattern] + excluded_schemas
                try:
                    cursor.execute(sql, params)
                    deprecated_usage = cursor.fetchall()
                except Exception as e:
                    logger.exception("Error querying routines for %s: %s", func, e)
                    continue
                if deprecated_usage:
                    result['details']['functions_and_syntax']['status'] = 'RED'
                    for routine in deprecated_usage:
                        schema = routine.get('ROUTINE_SCHEMA') or routine.get('routine_schema')
                        name = routine.get('ROUTINE_NAME') or routine.get('routine_name')
                        typ = routine.get('ROUTINE_TYPE') or routine.get('routine_type')
                        created = routine.get('CREATED') or routine.get('created')
                        last_altered = routine.get('LAST_ALTERED') or routine.get('last_altered')
                        result['details']['functions_and_syntax']['affected_objects'].append({
                            'schema': schema,
                            'object_name': name,
                            'object_type': typ,
                            'created': created.isoformat() if created else None,
                            'last_modified': last_altered.isoformat() if last_altered else None,
                            'deprecated_function': func,
                            'replacement': replacement
                        })
                        result['issues'].append(
                            f"Deprecated function {func} used in {schema}.{name}"
                        )
                    result['status'] = 'RED'
                    result['details']['summary']['critical_issues'] += len(deprecated_usage)

            # 3. System Variables Check
            deprecated_vars = [
                ('query_cache_size', 'Remove - query cache is deprecated'),
                ('query_cache_type', 'Remove - query cache is deprecated'),
                ('innodb_file_format', 'Remove - only Barracuda format supported'),
                ('innodb_file_format_check', 'Remove - only Barracuda format supported'),
                ('innodb_file_format_max', 'Remove - only Barracuda format supported'),
                ('tx_isolation', 'Use transaction_isolation instead'),
                ('tx_read_only', 'Use transaction_read_only instead'),
                ('secure_auth', 'Remove - secure auth is mandatory'),
                ('multi_range_count', 'Remove - no longer used')
            ]

            for var, recommendation in deprecated_vars:
                try:
                    cursor.execute("SHOW VARIABLES LIKE %s", (var,))
                    var_value = cursor.fetchone()
                except Exception as e:
                    logger.exception("Error checking variable %s: %s", var, e)
                    continue
                if var_value:
                    # support dict or tuple row formats
                    if hasattr(var_value, 'get'):
                        current_value = var_value.get('Value') or var_value.get('value')
                    else:
                        current_value = var_value[1] if len(var_value) > 1 else None
                    result['details']['system_variables']['status'] = 'AMBER'
                    result['details']['system_variables']['deprecated_vars'].append({
                        'variable': var,
                        'current_value': current_value,
                        'recommendation': recommendation
                    })
                    result['issues'].append(f"Deprecated system variable in use: {var}")
                    result['details']['summary']['warnings'] += 1
                    if result['status'] == 'GREEN':
                        result['status'] = 'AMBER'

            # 4. Query Cache Check
            cursor.execute("SHOW VARIABLES LIKE 'query_cache%'")
            query_cache_vars = cursor.fetchall()
            enabled_cache_vars = [var for var in query_cache_vars 
                                if var['Value'] != '0' and var['Value'].lower() != 'off']
            if enabled_cache_vars:
                result['details']['query_cache']['status'] = 'RED'
                result['details']['query_cache']['settings'] = enabled_cache_vars
                result['issues'].append("Query cache is enabled but will be removed in 8.0")
                result['status'] = 'RED'
                result['details']['summary']['critical_issues'] += 1

            # 5. Data Types Check
            # Check temporal columns
            cursor.execute("""
                SELECT 
                    TABLE_SCHEMA,
                    TABLE_NAME,
                    COLUMN_NAME,
                    COLUMN_TYPE,
                    DATETIME_PRECISION
                FROM information_schema.columns
                WHERE DATA_TYPE IN ('TIMESTAMP', 'DATETIME', 'TIME')
                AND TABLE_SCHEMA NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema')
            """)
            temporal_columns = cursor.fetchall()
            old_temporal = [col for col in temporal_columns if col['DATETIME_PRECISION'] is None]
            if old_temporal:
                result['details']['data_types']['status'] = 'AMBER'
                result['details']['data_types']['temporal_columns'] = old_temporal
                result['issues'].append(f"Found {len(old_temporal)} temporal columns without fractional seconds")
                result['details']['summary']['warnings'] += len(old_temporal)
                if result['status'] == 'GREEN':
                    result['status'] = 'AMBER'

            # Check spatial columns
            cursor.execute("""
                SELECT 
                    TABLE_SCHEMA,
                    TABLE_NAME,
                    COLUMN_NAME,
                    COLUMN_TYPE,
                    (
                        SELECT COUNT(*)
                        FROM information_schema.statistics s
                        WHERE s.table_schema = c.table_schema
                        AND s.table_name = c.table_name
                        AND s.column_name = c.column_name
                        AND s.index_type = 'SPATIAL'
                    ) as has_spatial_index
                FROM information_schema.columns c
                WHERE DATA_TYPE IN ('GEOMETRY', 'POINT', 'LINESTRING', 'POLYGON', 
                                'MULTIPOINT', 'MULTILINESTRING', 'MULTIPOLYGON', 
                                'GEOMETRYCOLLECTION')
                AND TABLE_SCHEMA NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema')
            """)
            spatial_columns = cursor.fetchall()
            if spatial_columns:
                result['details']['data_types']['spatial_columns'] = spatial_columns
                result['issues'].append(f"Found {len(spatial_columns)} spatial columns - review SRID requirements")
                result['details']['summary']['warnings'] += len(spatial_columns)
                if result['status'] == 'GREEN':
                    result['status'] = 'AMBER'

            # 6. SQL Modes Check
            cursor.execute("SELECT @@sql_mode as sql_mode")
            sql_modes = cursor.fetchone()['sql_mode'].split(',')
            deprecated_modes = ['NO_AUTO_CREATE_USER', 'NO_ZERO_DATE', 'ERROR_FOR_DIVISION_BY_ZERO']
            found_deprecated = [mode for mode in sql_modes if mode in deprecated_modes]
            if found_deprecated:
                result['details']['sql_modes']['status'] = 'AMBER'
                result['details']['sql_modes']['deprecated_modes'] = found_deprecated
                result['issues'].append(f"Deprecated SQL modes in use: {', '.join(found_deprecated)}")
                result['details']['summary']['warnings'] += len(found_deprecated)
                if result['status'] == 'GREEN':
                    result['status'] = 'AMBER'

            # Update summary
            result['details']['summary']['total_issues'] = (
                result['details']['summary']['critical_issues'] + 
                result['details']['summary']['warnings']
            )

            # Generate recommendations based on findings
            if result['details']['summary']['total_issues'] > 0:
                # Recommendations for mysql_old_password (critical)
                if result['details']['authentication'].get('affected_users'):
                    result['recommendations'].extend([
                        "CRITICAL: mysql_old_password is removed in MySQL 8.0",
                        "Pre-upgrade action required: Migrate these users to mysql_native_password or caching_sha2_password"
                    ])

                # Recommendations for mysql_native_password (informational)
                if result['details']['authentication'].get('native_password_users'):
                    result['recommendations'].extend([
                        "",
                        "Note: mysql_native_password authentication plugin:",
                        "- Remains supported in MySQL 8.0",
                        "- No pre-upgrade action required",
                        "- POST-UPGRADE: Consider migrating to caching_sha2_password for enhanced security",
                        "- caching_sha2_password is the default in MySQL 8.0 but migration is optional",
                        "- Client library compatibility should be verified before migration"
                    ])
                if result['details']['functions_and_syntax']['affected_objects']:
                    result['recommendations'].append(
                        "Remove or replace deprecated function usage in stored procedures and functions"
                    )
                if result['details']['query_cache']['settings']:
                    result['recommendations'].append(
                        "Disable query cache and remove related settings"
                    )
                if result['details']['system_variables']['deprecated_vars']:
                    result['recommendations'].append(
                        "Update system variables to use new names and remove deprecated ones"
                    )
                if result['details']['data_types']['temporal_columns']:
                    result['recommendations'].append(
                        "Review temporal columns for fractional seconds support"
                    )
                if result['details']['data_types']['spatial_columns']:
                    result['recommendations'].append(
                        "Add SRID to spatial columns and rebuild spatial indexes"
                    )
                if result['details']['sql_modes']['deprecated_modes']:
                    result['recommendations'].append(
                        "Update SQL modes to remove deprecated options"
                    )

            return result
        except Exception as e:
            return {
                'name': 'Deprecated Features Check',
                'description': 'Detects deprecated functions, authentication methods, and SQL modes that are removed in MySQL 8.0',
                'status': 'ERROR',
                'issues': [f"Error checking deprecated features: {str(e)}"],
                'recommendations': [
                    "Verify database permissions",
                    "Check if information_schema is accessible"
                ]
            }
        finally:
            if cursor:
                cursor.close()

    def _check_parameters(self, conn):
        cursor = None
        try:
            # Check if this is Aurora
            is_aurora = (self.db_info and
                        self.db_info.get('engine', '').startswith('aurora'))

            result = {
                'name': 'Parameter Compatibility Check',
                'description': 'Identifies removed or changed system variables that require configuration updates before upgrading',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'is_aurora': is_aurora,
                    'critical_parameters': [],
                    'behavioral_changes': [],
                    'removed_parameters': [],
                    'deprecated_parameters': [],
                    'new_default_values': [],
                    'summary': {
                        'total_issues': 0,
                        'critical_issues': 0,
                        'warnings': 0
                    }
                }
            }

            cursor = conn.cursor(dictionary=True)

            # 1. Check Parameters Being Removed
            removed_params = [
                ('innodb_file_format', 'Removed - Only Barracuda format supported'),
                ('innodb_file_format_check', 'Removed - Only Barracuda format supported'),
                ('innodb_file_format_max', 'Removed - Only Barracuda format supported'),
                ('innodb_large_prefix', 'Removed - Large prefix is always enabled'),
                ('sync_frm', 'Removed - .frm files no longer used'),
                ('secure_auth', 'Removed - Secure authentication is mandatory'),
                ('multi_range_count', 'Removed - No longer used'),
                ('log_warnings', 'Use log_error_verbosity instead'),
                ('ignore_builtin_innodb', 'Removed - InnoDB cannot be disabled'),
                ('innodb_support_xa', 'Removed - XA support is always enabled'),
                ('query_cache_size', 'Removed - Query cache is removed'),
                ('query_cache_type', 'Removed - Query cache is removed'),
                ('innodb_undo_tablespaces', 'Removed in 8.0.4 - See innodb_undo_tablespaces_implicit'),
                ('max_tmp_tables', 'Removed - No longer used')
            ]

            # For Aurora, parameter compatibility is managed automatically
            if is_aurora:
                result['recommendations'].append(
                    "Aurora automatically manages parameter group compatibility during upgrades - "
                    "you will be required to use a MySQL 8.0-compatible parameter group"
                )
                # Still check for informational purposes but don't flag as critical
                # removed_params is an internal whitelist — validate before formatting into SQL
                allowed_params = {p for p, _ in removed_params}
                found_removed = []
                for param, note in removed_params:
                    if param not in allowed_params:
                        logger.warning("Skipping unapproved parameter check: %s", param)
                        continue
                    sql = f"SELECT @@{param} as value"
                    try:
                        cursor.execute(sql)
                        row = cursor.fetchone()
                    except Exception as e:
                        logger.exception("Error checking parameter %s: %s", param, e)
                        continue
                    if row:
                        # support dict or tuple formats
                        if hasattr(row, 'get'):
                            val = row.get('value') or row.get('VALUE') or row.get('Value')
                        else:
                            val = row[0] if len(row) > 0 else None
                        if val is not None:
                            found_removed.append(param)

                if found_removed:
                    result['recommendations'].append(
                        f"Note: Detected {len(found_removed)} parameters that will be removed in 8.0, "
                        "but Aurora will handle this automatically during upgrade"
                    )
            else:
                # For RDS MySQL (non-Aurora), removed parameters are critical
                # removed_params is an internal whitelist — validate before formatting into SQL
                allowed_params = {p for p, _ in removed_params}
                for param, note in removed_params:
                    if param not in allowed_params:
                        logger.warning("Skipping unapproved parameter check: %s", param)
                        continue
                    sql = f"SELECT @@{param} as value"
                    try:
                        cursor.execute(sql)
                        row = cursor.fetchone()
                    except Exception as e:
                        logger.exception("Error checking parameter %s: %s", param, e)
                        continue
                    if row:
                        # support dict or tuple formats
                        if hasattr(row, 'get'):
                            val = row.get('value') or row.get('VALUE') or row.get('Value')
                        else:
                            val = row[0] if len(row) > 0 else None
                        if val is not None:
                            result['details']['removed_parameters'].append({
                                'parameter': param,
                                'note': note,
                                'action_required': 'Remove from configuration'
                            })
                            result['issues'].append(f"Parameter will be removed in 8.0: {param}")
                            result['status'] = 'RED'
                            result['details']['summary']['critical_issues'] += 1

            # 2. Check Default Value Changes
            default_changes = [
                {
                    'param': 'explicit_defaults_for_timestamp',
                    'old_default': '0',
                    'new_default': '1',
                    'query': 'SELECT @@explicit_defaults_for_timestamp as value',
                    'note': 'Affects timestamp column behavior'
                },
                {
                    'param': 'binlog_expire_logs_seconds',
                    'old_default': None,
                    'new_default': '2592000',
                    'query': 'SELECT @@binlog_expire_logs_seconds as value',
                    'note': 'Replaces expire_logs_days'
                },
                {
                    'param': 'completion_type',
                    'old_default': '0',
                    'new_default': 'NO_CHAIN',
                    'query': 'SELECT @@completion_type as value',
                    'note': 'Affects transaction completion behavior'
                },
                {
                    'param': 'transaction_isolation',
                    'old_default': 'REPEATABLE-READ',
                    'new_default': 'REPEATABLE-READ',
                    'query': 'SELECT @@transaction_isolation as value',
                    'note': 'Replaces tx_isolation'
                },
                {
                    'param': 'innodb_autoinc_lock_mode',
                    'old_default': '1',
                    'new_default': '2',
                    'query': 'SELECT @@innodb_autoinc_lock_mode as value',
                    'note': 'Affects auto-increment locking behavior'
                }
            ]

            for param in default_changes:
                try:
                    cursor.execute(param['query'])
                    row = cursor.fetchone()
                    current_value = None
                    if row:
                        if hasattr(row, 'get'):
                            current_value = row.get('value') or row.get('VALUE') or row.get('Value')
                        else:
                            current_value = row[0] if len(row) > 0 else None
                    if str(current_value) != str(param['new_default']):
                        result['details']['new_default_values'].append({
                            'parameter': param['param'],
                            'current_value': current_value,
                            'new_default': param['new_default'],
                            'note': param['note']
                        })
                        result['issues'].append(
                            f"Parameter {param['param']} default changing to {param['new_default']}"
                        )
                        if result['status'] == 'GREEN':
                            result['status'] = 'AMBER'
                        result['details']['summary']['warnings'] += 1
                except Exception as e:
                    # Skip variables that don't exist in MySQL 5.7 (like binlog_expire_logs_seconds)
                    if 'Unknown system variable' in str(e):
                        logger.debug("Skipping %s check (not available in this MySQL version)", param.get('param'))
                    else:
                        logger.exception("Error checking default change for %s: %s", param.get('param'), e)
                    continue

            # 3. Check Behavioral Changes
            behavioral_changes = [
                {
                    'param': 'sql_mode',
                    'query': 'SELECT @@sql_mode as value',
                    'check': lambda x: x is None or 'NO_AUTO_CREATE_USER' not in x.split(','),
                    'note': 'NO_AUTO_CREATE_USER removed, use CREATE USER statement'
                },
                {
                    'param': 'innodb_flush_method',
                    'query': 'SELECT @@innodb_flush_method as value',
                    'check': lambda x: x is None or x != 'ALL_O_DIRECT',
                    'note': 'ALL_O_DIRECT replaced by O_DIRECT_NO_FSYNC'
                },
                {
                    'param': 'max_length_for_sort_data',
                    'query': 'SELECT @@max_length_for_sort_data as value',
                    'check': lambda x: x is None or int(x) <= 4096,
                    'note': 'Default reduced to 4096 to avoid memory issues'
                }
            ]

            for change in behavioral_changes:
                try:
                    cursor.execute(change['query'])
                    row = cursor.fetchone()
                    current_value = None
                    if row:
                        if hasattr(row, 'get'):
                            current_value = row.get('value') or row.get('Value') or row.get('VALUE')
                        else:
                            current_value = row[0] if len(row) > 0 else None
                    if current_value is not None and not change['check'](current_value):
                        result['details']['behavioral_changes'].append({
                            'parameter': change['param'],
                            'current_value': current_value,
                            'note': change['note']
                        })
                        result['issues'].append(
                            f"Parameter {change['param']} behavior changes in 8.0"
                        )
                        if result['status'] == 'GREEN':
                            result['status'] = 'AMBER'
                        result['details']['summary']['warnings'] += 1
                except Exception as e:
                    logger.exception("Error checking behavioral change for %s: %s", change.get('param'), e)
                    continue

            # 4. Check Critical Parameters
            critical_params = [
                {
                    'param': 'log_bin_trust_function_creators',
                    'expected': 1,
                    'query': 'SELECT @@log_bin_trust_function_creators as value',
                    'note': 'Required for stored function creation with binary logging'
                },
                {
                    'param': 'enforce_gtid_consistency',
                    'expected': 'ON',
                    'query': 'SELECT @@enforce_gtid_consistency as value',
                    'note': 'Required for GTID-based replication'
                },
                {
                    'param': 'innodb_strict_mode',
                    'expected': 1,
                    'query': 'SELECT @@innodb_strict_mode as value',
                    'note': 'Recommended for data integrity'
                },
                {
                    'param': 'binlog_format',
                    'expected': 'ROW',
                    'query': 'SELECT @@binlog_format as value',
                    'note': 'Required for safe replication'
                }
            ]

            for param in critical_params:
                try:
                    cursor.execute(param['query'])
                    row = cursor.fetchone()
                    current_value = None
                    if row:
                        if hasattr(row, 'get'):
                            current_value = row.get('value') or row.get('Value') or row.get('VALUE')
                        else:
                            current_value = row[0] if len(row) > 0 else None
                    if str(current_value).upper() != str(param['expected']).upper():
                        result['details']['critical_parameters'].append({
                            'parameter': param['param'],
                            'current_value': current_value,
                            'required_value': param['expected'],
                            'note': param['note']
                        })
                        result['issues'].append(
                            f"Critical parameter {param['param']} not set to required value {param['expected']}"
                        )
                        result['status'] = 'RED'
                        result['details']['summary']['critical_issues'] += 1
                except Exception as e:
                    logger.exception("Error checking critical parameter %s: %s", param.get('param'), e)
                    continue

            # 5. Check for XA Transaction Support
            try:
                cursor.execute("XA RECOVER")
                xa_transactions = cursor.fetchall()
                if xa_transactions:
                    result['status'] = 'RED'
                    result['issues'].append(
                        f"Found {len(xa_transactions)} prepared XA transactions that must be resolved before upgrade"
                    )
                    result['details']['summary']['critical_issues'] += 1
            except Exception as e:
                logger.exception("Could not check XA transactions status: %s", e)
                result['issues'].append("Could not check XA transactions status")

            # Update summary
            result['details']['summary']['total_issues'] = (
                result['details']['summary']['critical_issues'] +
                result['details']['summary']['warnings']
            )

            # Generate recommendations
            if result['details']['summary']['total_issues'] > 0:
                if result['details']['removed_parameters']:
                    result['recommendations'].append(
                        "Remove or replace parameters that will be removed in 8.0"
                    )
                if result['details']['new_default_values']:
                    result['recommendations'].append(
                        "Review and test with new parameter default values"
                    )
                if result['details']['behavioral_changes']:
                    result['recommendations'].append(
                        "Test applications with changed parameter behaviors"
                    )
                if result['details']['critical_parameters']:
                    result['recommendations'].append(
                        "Update critical parameters to required values"
                    )

            return result
        except Exception as e:
            return {
                'name': 'Parameter Compatibility Check',
                'description': 'Identifies removed or changed system variables that require configuration updates before upgrading',
                'status': 'ERROR',
                'issues': [f"Error checking parameters: {str(e)}"],
                'recommendations': ["Verify database permissions"]
            }
        finally:
            if cursor:
                cursor.close()

    def _check_foreign_keys(self, conn):
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT 
                    tc.table_schema,
                    tc.table_name,
                    tc.constraint_name,
                    kcu.column_name,
                    kcu.referenced_table_schema,
                    kcu.referenced_table_name,
                    kcu.referenced_column_name,
                    rc.update_rule,
                    rc.delete_rule,
                    s.index_name as supporting_index
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.referential_constraints rc
                    ON tc.constraint_name = rc.constraint_name
                    AND tc.table_schema = rc.constraint_schema
                LEFT JOIN information_schema.statistics s
                    ON kcu.table_schema = s.table_schema
                    AND kcu.table_name = s.table_name
                    AND kcu.column_name = s.column_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
                ORDER BY tc.table_schema, tc.table_name, tc.constraint_name
            """)
            foreign_keys = cursor.fetchall()

            result = {
                'name': 'Foreign Key Check',
                'description': 'Analyzes foreign key constraints for potential compatibility issues and validates referential integrity',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'foreign_keys': foreign_keys,
                    'summary': {
                        'total_foreign_keys': len(foreign_keys),
                        'affected_schemas': len(set(fk['table_schema'] for fk in foreign_keys)),
                        'affected_tables': len(set(f"{fk['table_schema']}.{fk['table_name']}" 
                                                 for fk in foreign_keys))
                    }
                }
            }

            if foreign_keys:
                result['status'] = 'AMBER'
                # Group by schema for better organization
                by_schema = {}
                for fk in foreign_keys:
                    schema = fk['table_schema']
                    if schema not in by_schema:
                        by_schema[schema] = []
                    by_schema[schema].append(fk)

                # Add detailed issues
                for schema, schema_fks in by_schema.items():
                    result['issues'].append(f"\nSchema: {schema}")
                    for fk in schema_fks:
                        result['issues'].append(
                            f"  FK: {fk['constraint_name']}\n"
                            f"    Table: {fk['table_name']}.{fk['column_name']}\n"
                            f"    References: {fk['referenced_table_schema']}."
                            f"{fk['referenced_table_name']}.{fk['referenced_column_name']}\n"
                            f"    Update Rule: {fk['update_rule']}, Delete Rule: {fk['delete_rule']}\n"
                            f"    Supporting Index: {fk['supporting_index'] or 'None'}"
                        )

                result['recommendations'].extend([
                    f"\nForeign Key Statistics:",
                    f"- Total foreign keys: {result['details']['summary']['total_foreign_keys']}",
                    f"- Affected schemas: {result['details']['summary']['affected_schemas']}",
                    f"- Affected tables: {result['details']['summary']['affected_tables']}",
                    "\nRecommended Actions:",
                    "1. Verify all foreign key constraints before upgrade",
                    "2. Check for missing indexes on foreign key columns",
                    "3. Consider temporarily disabling foreign keys during upgrade",
                    "4. Take backup before modifying any constraints",
                    "5. Review update and delete rules for each constraint",
                    "6. Test referential integrity after upgrade",
                    "\nSQL Commands:",
                    "-- To disable foreign key checks during upgrade:",
                    "SET foreign_key_checks = 0;",
                    "-- Don't forget to re-enable after upgrade:",
                    "SET foreign_key_checks = 1;"
                ])

            return result
        except Exception as e:
            raise Exception(f"Foreign key check failed: {str(e)}")
        finally:
            if cursor:
                cursor.close()
                
    def _check_triggers_views(self, conn):
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Get detailed trigger information
            cursor.execute("""
                SELECT 
                    trigger_schema,
                    trigger_name,
                    event_manipulation,
                    event_object_schema,
                    event_object_table,
                    action_statement,
                    action_timing,
                    created,
                    definer,
                    character_set_client,
                    collation_connection,
                    database_collation
                FROM information_schema.triggers
                WHERE trigger_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
                ORDER BY trigger_schema, trigger_name
            """)
            triggers = cursor.fetchall()

            # Get detailed view information
            cursor.execute("""
                SELECT 
                    table_schema,
                    table_name,
                    view_definition,
                    check_option,
                    is_updatable,
                    definer,
                    security_type,
                    character_set_client,
                    collation_connection
                FROM information_schema.views
                WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
                ORDER BY table_schema, table_name
            """)
            views = cursor.fetchall()

            # Get view dependencies (checking MySQL version first)
            cursor.execute("SELECT @@version as version")
            version_info = cursor.fetchone()
            
            if '8.0' in version_info['version']:
                try:
                    cursor.execute("""
                        SELECT 
                            table_schema,
                            table_name,
                            referenced_table_schema,
                            referenced_table_name
                        FROM information_schema.view_table_usage
                        WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
                        ORDER BY table_schema, table_name
                    """)
                    view_dependencies = cursor.fetchall()
                except Exception as e:
                    logger.exception("Error querying view dependencies: %s", e)
                    view_dependencies = []
            else:
                # For MySQL 5.7, skip view dependencies check
                view_dependencies = []
            result = {
                'name': 'Triggers and Views Check',
                'description': 'Examines triggers and views for syntax changes, deprecated features, and complexity issues',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'triggers': triggers,
                    'views': views,
                    'view_dependencies': view_dependencies,
                    'summary': {
                        'trigger_count': len(triggers),
                        'view_count': len(views),
                        'affected_schemas': len(set(t['trigger_schema'] for t in triggers) | 
                                          set(v['table_schema'] for v in views))
                    }
                }
            }

            # Check triggers
            if triggers:
                result['status'] = 'AMBER'
                # Group by schema
                by_schema = {}
                for trigger in triggers:
                    schema = trigger['trigger_schema']
                    if schema not in by_schema:
                        by_schema[schema] = []
                    by_schema[schema].append(trigger)

                result['issues'].append("\nTriggers:")
                for schema, schema_triggers in by_schema.items():
                    result['issues'].append(f"\nSchema: {schema}")
                    for t in schema_triggers:
                        # Check for potential issues in trigger definition
                        potential_issues = []
                        action_stmt = t['action_statement'].upper()
                        
                        if 'PASSWORD(' in action_stmt:
                            potential_issues.append("Uses deprecated PASSWORD() function")
                        if 'OLD_PASSWORD(' in action_stmt:
                            potential_issues.append("Uses deprecated OLD_PASSWORD() function")
                        if 'ENCRYPT(' in action_stmt:
                            potential_issues.append("Uses deprecated ENCRYPT() function")
                        
                        result['issues'].append(
                            f"  Trigger: {t['trigger_name']}\n"
                            f"    On Table: {t['event_object_table']}\n"
                            f"    Event: {t['action_timing']} {t['event_manipulation']}\n"
                            f"    Created: {t['created']}\n"
                            f"    Definer: {t['definer']}\n"
                            f"    Character Set: {t['character_set_client']}\n"
                            + (f"    Potential Issues: {', '.join(potential_issues)}\n" 
                               if potential_issues else "")
                        )

            # Check views
            if views:
                result['status'] = 'AMBER'
                # Group by schema
                by_schema = {}
                for view in views:
                    schema = view['table_schema']
                    if schema not in by_schema:
                        by_schema[schema] = []
                    by_schema[schema].append(view)

                result['issues'].append("\nViews:")
                for schema, schema_views in by_schema.items():
                    result['issues'].append(f"\nSchema: {schema}")
                    for v in schema_views:
                        # Check for potential issues in view definition
                        potential_issues = []
                        view_def = v['view_definition'].upper()
                        
                        if 'PASSWORD(' in view_def:
                            potential_issues.append("Uses deprecated PASSWORD() function")
                        if 'GROUP BY' in view_def and 'ANY_VALUE(' not in view_def:
                            potential_issues.append("May need ANY_VALUE() for GROUP BY in 8.0")
                        
                        # Get dependencies for this view
                        deps = [d for d in view_dependencies 
                               if d['table_schema'] == v['table_schema'] 
                               and d['table_name'] == v['table_name']]
                        
                        # Create the dependencies string separately
                        dep_str = ""
                        if deps:
                            dep_list = []
                            for dep in deps:
                                dep_list.append(f"{dep['referenced_table_schema']}.{dep['referenced_table_name']}")
                            dep_str = f"    Dependencies: {', '.join(dep_list)}\n"

                        result['issues'].append(
                            f"  View: {v['table_name']}\n"
                            f"    Updatable: {v['is_updatable']}\n"
                            f"    Security: {v['security_type']}\n"
                            f"    Definer: {v['definer']}\n"
                            f"    Character Set: {v['character_set_client']}\n"
                            + (f"    Potential Issues: {', '.join(potential_issues)}\n" 
                               if potential_issues else "")
                            + dep_str
                        )

            if triggers or views:
                result['recommendations'].extend([
                    f"\nSummary:",
                    f"- Total objects to review: {len(triggers) + len(views)}",
                    f"- Triggers: {len(triggers)}",
                    f"- Views: {len(views)}",
                    f"- Affected schemas: {result['details']['summary']['affected_schemas']}",
                    "\nRecommended Actions:",
                    "1. Review all triggers and views for 8.0 compatibility",
                    "2. Test triggers and views in upgrade simulation",
                    "3. Consider temporarily disabling triggers during upgrade",
                    "4. Take backup of all view and trigger definitions",
                    "5. Check for deprecated syntax in view definitions",
                    "6. Verify trigger privileges and security settings",
                    "7. Review view dependencies and updatability",
                    "\nBackup Commands:",
                    "-- To get trigger definitions:",
                    "SHOW TRIGGERS;",
                    "-- To get view definitions:",
                    "SHOW CREATE VIEW view_name;",
                    "\nDisabling/Enabling Triggers:",
                    "-- To disable triggers on a table:",
                    "ALTER TABLE table_name DISABLE TRIGGERS;",
                    "-- To enable triggers on a table:",
                    "ALTER TABLE table_name ENABLE TRIGGERS;"
                ])

            return result
        except Exception as e:
            raise Exception(f"Triggers and views check failed: {str(e)}")
        finally:
            if cursor:
                cursor.close()
                
    def _check_new_features_compatibility(self, conn):
        cursor = None
        try:
            result = {
                'name': 'New Features Compatibility',
                'description': 'Highlights MySQL 8.0 features (CTEs, window functions, JSON) available after upgrade',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'new_features': {
                        'hash_joins': {
                            'available': False,
                            'benefits': [
                                "Improved performance for large table joins without indexes",
                                "Better memory utilization for specific join types",
                                "Automatic optimization for suitable queries"
                            ],
                            'usage_examples': [
                                "SELECT /*+ HASH_JOIN(t1, t2) */ * FROM t1 JOIN t2 ON t1.id = t2.id",
                                "Optimizer automatically chooses hash joins when beneficial"
                            ]
                        },
                        'invisible_indexes': {
                            'available': False,
                            'benefits': [
                                "Test index impact before removal",
                                "Maintain indexes while preventing optimizer usage",
                                "Safe index management in production"
                            ],
                            'usage_examples': [
                                "ALTER TABLE tbl ALTER INDEX idx INVISIBLE;",
                                "CREATE INDEX idx ON tbl (col) INVISIBLE;"
                            ]
                        },
                        'descending_indexes': {
                            'available': False,
                            'benefits': [
                                "Improved performance for mixed ASC/DESC ordering",
                                "Better optimization for ORDER BY clauses",
                                "Reduced need for temporary tables"
                            ],
                            'usage_examples': [
                                "CREATE INDEX idx ON tbl (col1 ASC, col2 DESC);",
                                "Supports efficient mixed-order range scans"
                            ]
                        },
                        'window_functions': {
                            'available': False,
                            'benefits': [
                                "Advanced analytical queries",
                                "Row-based calculations within result sets",
                                "Complex reporting capabilities"
                            ],
                            'usage_examples': [
                                "ROW_NUMBER() OVER (PARTITION BY col ORDER BY col2)",
                                "LAG(), LEAD(), FIRST_VALUE(), LAST_VALUE()"
                            ]
                        },
                        'instant_ddl': {
                            'available': False,
                            'benefits': [
                                "Add/drop columns instantly",
                                "Reduced downtime for schema changes",
                                "No table copy for supported operations"
                            ],
                            'usage_examples': [
                                "ALTER TABLE tbl ADD COLUMN col1 INT DEFAULT 0, ALGORITHM=INSTANT;",
                                "Supports adding columns with defaults"
                            ]
                        },
                        'check_constraints': {
                            'available': False,
                            'benefits': [
                                "Enhanced data integrity",
                                "Better constraint management",
                                "Improved data validation"
                            ],
                            'usage_examples': [
                                "CREATE TABLE t1 (c1 INT CHECK (c1 > 10));",
                                "ALTER TABLE t1 ADD CONSTRAINT CHECK (c1 < 100);"
                            ]
                        },
                        'roles': {
                            'available': False,
                            'benefits': [
                                "Simplified user privilege management",
                                "Role-based access control",
                                "Better security management"
                            ],
                            'usage_examples': [
                                "CREATE ROLE 'app_read', 'app_write';",
                                "GRANT SELECT ON db.* TO 'app_read';"
                            ]
                        }
                    },
                    'performance_improvements': [
                        {
                            'feature': 'Instant DDL',
                            'description': "Many ALTER TABLE operations complete instantly",
                            'benefit': "Reduced downtime for schema changes",
                            'recommendation': "Use ALGORITHM=INSTANT for supported operations"
                        },
                        {
                            'feature': 'Improved InnoDB deadlock detection',
                            'description': "Better handling of deadlock scenarios",
                            'benefit': "Reduced transaction conflicts",
                            'recommendation': "Monitor deadlock patterns after upgrade"
                        },
                        {
                            'feature': 'Enhanced optimizer hints',
                            'description': "More control over query execution",
                            'benefit': "Better query optimization options",
                            'recommendation': "Review slow queries for hint opportunities"
                        },
                        {
                            'feature': 'Multi-valued indexes',
                            'description': "Index generation for JSON arrays",
                            'benefit': "Improved JSON array search performance",
                            'recommendation': "Consider for JSON array fields"
                        }
                    ],
                    'security_enhancements': [
                        {
                            'feature': 'caching_sha2_password',
                            'description': "New default authentication plugin",
                            'benefit': "Improved security with good performance",
                            'recommendation': "Plan user authentication updates"
                        },
                        {
                            'feature': 'SQL Roles',
                            'description': "Role-based privilege management",
                            'benefit': "Simplified access control",
                            'recommendation': "Design role hierarchy for applications"
                        }
                    ]
                }
            }

            cursor = conn.cursor(dictionary=True)
            
            # Check current version to determine feature availability
            cursor.execute("SELECT @@version as version")
            version_info = cursor.fetchone()
            is_8_0 = '8.0' in version_info['version']

            if not is_8_0:
                # Check potential benefits based on current database usage
                
                # 1. Check for potential hash join benefits
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM information_schema.tables t1
                    JOIN information_schema.statistics s1
                    ON t1.table_schema = s1.table_schema 
                    AND t1.table_name = s1.table_name
                    WHERE t1.table_schema NOT IN ('mysql', 'information_schema', 'performance_schema')
                    GROUP BY t1.table_schema, t1.table_name
                    HAVING count(*) = 0
                """)
                unindexed_tables = cursor.fetchall()
                
                if unindexed_tables:
                    result['recommendations'].append(
                        "Consider hash joins for tables without indexes after upgrade"
                    )

                # 2. Check for complex ORDER BY usage
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM information_schema.tables
                    WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema')
                    AND table_type = 'BASE TABLE'
                """)
                table_count = cursor.fetchone()['count']
                
                if table_count > 10:
                    result['recommendations'].append(
                        "Review queries with mixed ORDER BY directions for descending index benefits"
                    )

                # 3. Check for potential window function usage
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM information_schema.tables
                    WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema')
                    AND table_type = 'BASE TABLE'
                    AND (table_rows > 10000 OR table_rows IS NULL)
                """)
                large_tables = cursor.fetchone()['count']
                
                if large_tables > 0:
                    result['recommendations'].append(
                        "Consider window functions for analytical queries on large tables"
                    )

                # 4. Check for JSON usage
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM information_schema.columns
                    WHERE data_type = 'json'
                    AND table_schema NOT IN ('mysql', 'information_schema', 'performance_schema')
                """)
                json_columns = cursor.fetchone()['count']
                
                if json_columns > 0:
                    result['recommendations'].append(
                        f"Found {json_columns} JSON columns - review new JSON functions and multi-valued indexes"
                    )

                # Add general recommendations
                result['recommendations'].extend([
                    "\nNew Feature Opportunities in 8.0:",
                    "1. Hash Joins for better join performance",
                    "2. Invisible Indexes for safe index management",
                    "3. Descending Indexes for mixed-order queries",
                    "4. Window Functions for analytical queries",
                    "5. Instant DDL for faster schema changes",
                    "6. SQL Roles for better security management",
                    "7. Check Constraints for data integrity",
                    "\nPerformance Improvements:",
                    "- Enhanced optimizer features",
                    "- Improved deadlock detection",
                    "- Better temporary table handling",
                    "- Instant DDL operations",
                    "\nSecurity Enhancements:",
                    "- New authentication plugin (caching_sha2_password)",
                    "- Role-based access control",
                    "- Enhanced password management"
                ])

            return result
        except Exception as e:
            return {
                'name': 'New Features Compatibility',
                'description': 'Highlights MySQL 8.0 features (CTEs, window functions, JSON) available after upgrade',
                'status': 'ERROR',
                'issues': [f"Error checking new features compatibility: {str(e)}"],
                'recommendations': ["Verify database permissions"]
            }
        finally:
            if cursor:
                cursor.close()

    # ========================================================================================
    # NEW CHECKS (10-20) - Comprehensive MySQL 8.0 Upgrade Assessment
    # ========================================================================================

    def _check_reserved_keywords(self, conn):
        """
        Check 10: Reserved Keywords Conflicts
        Identify database objects that conflict with MySQL 8.0 reserved keywords.
        """
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            result = {
                'name': 'Reserved Keywords Conflicts',
                'description': 'Identifies table and column names that conflict with new MySQL 8.0 reserved keywords',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'conflicting_tables': [],
                    'conflicting_columns': [],
                    'conflicting_routines': []
                }
            }

            # New reserved keywords in MySQL 8.0
            reserved_keywords = [
                'CUME_DIST', 'DENSE_RANK', 'EMPTY', 'EXCEPT', 'FIRST_VALUE',
                'GROUPING', 'GROUPS', 'LAG', 'LAST_VALUE', 'LEAD', 'NTH_VALUE',
                'NTILE', 'OVER', 'PERCENT_RANK', 'RANK', 'RECURSIVE', 'ROW_NUMBER',
                'SYSTEM', 'WINDOW', 'JSON_TABLE', 'LATERAL', 'MEMBER', 'OF'
            ]
            keywords_str = "', '".join(reserved_keywords)

            # Check table names
            cursor.execute(f"""
                SELECT table_schema, table_name, 'TABLE' as object_type
                FROM information_schema.tables
                WHERE table_schema NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema')
                AND UPPER(table_name) IN ('{keywords_str}')
                ORDER BY table_schema, table_name
            """)
            conflicting_tables = cursor.fetchall()

            # Check column names
            cursor.execute(f"""
                SELECT table_schema, table_name, column_name, 'COLUMN' as object_type
                FROM information_schema.columns
                WHERE table_schema NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema')
                AND UPPER(column_name) IN ('{keywords_str}')
                ORDER BY table_schema, table_name, column_name
            """)
            conflicting_columns = cursor.fetchall()

            # Check stored procedure/function names
            cursor.execute(f"""
                SELECT routine_schema, routine_name, routine_type as object_type
                FROM information_schema.routines
                WHERE routine_schema NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema')
                AND UPPER(routine_name) IN ('{keywords_str}')
                ORDER BY routine_schema, routine_name
            """)
            conflicting_routines = cursor.fetchall()

            # Process results
            if conflicting_tables:
                result['status'] = 'RED'
                result['details']['conflicting_tables'] = conflicting_tables
                for table in conflicting_tables:
                    result['issues'].append(
                        f"Table name '{table['table_schema']}.{table['table_name']}' conflicts with MySQL 8.0 reserved keyword"
                    )

            if conflicting_columns:
                result['status'] = 'RED'
                result['details']['conflicting_columns'] = conflicting_columns
                for col in conflicting_columns:
                    result['issues'].append(
                        f"Column name '{col['table_schema']}.{col['table_name']}.{col['column_name']}' conflicts with MySQL 8.0 reserved keyword"
                    )

            if conflicting_routines:
                result['status'] = 'RED'
                result['details']['conflicting_routines'] = conflicting_routines
                for routine in conflicting_routines:
                    result['issues'].append(
                        f"{routine['object_type']} '{routine['routine_schema']}.{routine['routine_name']}' conflicts with MySQL 8.0 reserved keyword"
                    )

            # Generate recommendations
            if result['status'] == 'RED':
                result['recommendations'].extend([
                    "CRITICAL: Rename objects that conflict with reserved keywords before upgrading",
                    "Option 1 - Rename objects:",
                    "  ALTER TABLE schema.rank RENAME TO schema.rank_data;",
                    "  ALTER TABLE schema.table ALTER COLUMN rank RENAME TO rank_value;",
                    "Option 2 - Use backticks in all queries:",
                    "  SELECT * FROM `rank` WHERE `rank`.`rank` > 10;",
                    "Note: Backticks are a workaround but renaming is recommended",
                    "Update application code to handle renamed objects"
                ])

            return result
        except Exception as e:
            return {
                'name': 'Reserved Keywords Conflicts',
                'description': 'Identifies table and column names that conflict with new MySQL 8.0 reserved keywords',
                'status': 'ERROR',
                'issues': [f"Error checking reserved keywords: {str(e)}"],
                'recommendations': ["Verify database permissions"]
            }
        finally:
            if cursor:
                cursor.close()

    def _check_partition_compatibility(self, conn):
        """
        Check 11: Partition Compatibility
        Identify partitioned tables with compatibility issues in MySQL 8.0.
        """
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            result = {
                'name': 'Partition Compatibility',
                'description': 'Validates partitioned tables for compatibility with MySQL 8.0 partitioning changes',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'partitioned_tables': [],
                    'high_partition_count': [],
                    'summary': {
                        'total_partitioned_tables': 0,
                        'total_partitions': 0
                    }
                }
            }

            # Get partitioned tables info
            # Note: Using subquery instead of window function for MySQL 5.7 compatibility
            cursor.execute("""
                SELECT
                    t.table_schema,
                    t.table_name,
                    t.partition_name,
                    t.partition_method,
                    t.subpartition_method,
                    t.partition_expression,
                    t.table_rows,
                    (SELECT COUNT(*)
                     FROM information_schema.partitions p
                     WHERE p.table_schema = t.table_schema
                     AND p.table_name = t.table_name
                     AND p.partition_name IS NOT NULL) as partition_count
                FROM information_schema.partitions t
                WHERE t.table_schema NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema')
                AND t.partition_name IS NOT NULL
                ORDER BY t.table_schema, t.table_name, t.partition_ordinal_position
            """)
            partitions = cursor.fetchall()

            if not partitions:
                result['recommendations'].append("No partitioned tables found")
                return result

            # Analyze partitions
            tables_seen = set()
            high_partition_tables = []

            for partition in partitions:
                table_key = f"{partition['table_schema']}.{partition['table_name']}"

                if table_key not in tables_seen:
                    tables_seen.add(table_key)
                    result['details']['partitioned_tables'].append({
                        'schema': partition['table_schema'],
                        'table': partition['table_name'],
                        'method': partition['partition_method'],
                        'partition_count': partition['partition_count']
                    })

                    # Check for high partition count
                    if partition['partition_count'] > 100:
                        result['status'] = 'AMBER' if result['status'] == 'GREEN' else result['status']
                        high_partition_tables.append(table_key)
                        result['issues'].append(
                            f"Table {table_key} has {partition['partition_count']} partitions (>100)"
                        )

            result['details']['summary']['total_partitioned_tables'] = len(tables_seen)
            result['details']['summary']['total_partitions'] = len(partitions)
            result['details']['high_partition_count'] = high_partition_tables

            # Generate recommendations
            if result['status'] != 'GREEN':
                result['recommendations'].extend([
                    "Review partitioning strategy before upgrade:",
                    "- Test partition pruning effectiveness",
                    "- Consider partition consolidation for tables with >100 partitions",
                    "- Verify partition maintenance operations in non-production first",
                    "- Monitor partition-related performance post-upgrade"
                ])
            else:
                result['recommendations'].append(
                    f"Found {len(tables_seen)} partitioned tables - verify compatibility during testing"
                )

            return result
        except Exception as e:
            return {
                'name': 'Partition Compatibility',
                'description': 'Validates partitioned tables for compatibility with MySQL 8.0 partitioning changes',
                'status': 'ERROR',
                'issues': [f"Error checking partition compatibility: {str(e)}"],
                'recommendations': ["Verify database permissions"]
            }
        finally:
            if cursor:
                cursor.close()

    def _check_user_privileges(self, conn):
        """
        Check 12: User Privileges and Security
        Analyze user accounts and identify security issues for MySQL 8.0.
        """
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            result = {
                'name': 'User Privileges and Security',
                'description': 'Reviews user accounts, authentication plugins, and privilege mappings for MySQL 8.0 security model',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'deprecated_auth_users': [],
                    'super_privilege_users': [],
                    'empty_password_users': [],
                    'total_users': 0
                }
            }

            # Get user information
            cursor.execute("""
                SELECT user, host, plugin, password_expired, account_locked,
                       Super_priv, Grant_priv, Create_user_priv
                FROM mysql.user
                WHERE user NOT IN ('mysql.sys', 'mysql.session', 'mysql.infoschema', 'rdsadmin')
                ORDER BY user, host
            """)
            users = cursor.fetchall()
            result['details']['total_users'] = len(users)

            # Analyze users
            for user in users:
                user_host = f"'{user['user']}'@'{user['host']}'"

                # Check authentication plugin
                if user['plugin'] in ['mysql_old_password', 'sha256_password']:
                    result['status'] = 'RED'
                    result['details']['deprecated_auth_users'].append(user_host)
                    result['issues'].append(
                        f"User {user_host} uses deprecated authentication plugin: {user['plugin']}"
                    )

                # Check for SUPER privilege
                if user['Super_priv'] == 'Y':
                    if result['status'] == 'GREEN':
                        result['status'] = 'AMBER'
                    result['details']['super_privilege_users'].append(user_host)
                    result['issues'].append(
                        f"User {user_host} has SUPER privilege (deprecated in 8.0, requires privilege mapping)"
                    )

            # Check for empty passwords (separate query for safety)
            try:
                cursor.execute("""
                    SELECT user, host
                    FROM mysql.user
                    WHERE (authentication_string = '' OR authentication_string IS NULL)
                    AND user NOT IN ('mysql.sys', 'mysql.session', 'mysql.infoschema', 'rdsadmin')
                """)
                empty_pass_users = cursor.fetchall()

                if empty_pass_users:
                    result['status'] = 'RED'
                    for user in empty_pass_users:
                        user_host = f"'{user['user']}'@'{user['host']}'"
                        result['details']['empty_password_users'].append(user_host)
                        result['issues'].append(f"User {user_host} has empty password")
            except Exception:
                pass  # Column might not exist in some versions

            # Generate recommendations
            if result['details']['deprecated_auth_users']:
                result['recommendations'].extend([
                    "Migrate users to caching_sha2_password authentication:",
                    "  ALTER USER 'user'@'host' IDENTIFIED WITH caching_sha2_password BY 'password';"
                ])

            if result['details']['super_privilege_users']:
                result['recommendations'].extend([
                    "Map SUPER privilege to dynamic privileges in MySQL 8.0:",
                    "  Common mappings:",
                    "  - SUPER -> SYSTEM_VARIABLES_ADMIN (for SET GLOBAL)",
                    "  - SUPER -> REPLICATION_SLAVE_ADMIN (for replication)",
                    "  - SUPER -> BINLOG_ADMIN (for binary logs)",
                    "  Example: GRANT SYSTEM_VARIABLES_ADMIN ON *.* TO 'user'@'host';"
                ])

            if result['details']['empty_password_users']:
                result['recommendations'].append(
                    "Set passwords for users with empty passwords before upgrade"
                )

            if result['status'] == 'GREEN':
                result['recommendations'].append("User authentication and privileges are compatible with MySQL 8.0")

            return result
        except Exception as e:
            return {
                'name': 'User Privileges and Security',
                'description': 'Reviews user accounts, authentication plugins, and privilege mappings for MySQL 8.0 security model',
                'status': 'ERROR',
                'issues': [f"Error checking user privileges: {str(e)}"],
                'recommendations': ["Verify database permissions"]
            }
        finally:
            if cursor:
                cursor.close()

    def _check_json_usage(self, conn):
        """
        Check 13: JSON Schema and Functions
        Identify JSON usage and optimization opportunities in MySQL 8.0.
        """
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            result = {
                'name': 'JSON Usage and Optimization',
                'description': 'Analyzes JSON column usage and recommends MySQL 8.0 JSON optimization opportunities',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'json_columns': [],
                    'json_in_routines': [],
                    'summary': {
                        'total_json_columns': 0,
                        'columns_without_indexes': 0,
                        'routines_with_json': 0
                    }
                }
            }

            # Find JSON columns
            cursor.execute("""
                SELECT
                    c.table_schema,
                    c.table_name,
                    c.column_name,
                    c.is_nullable,
                    (
                        SELECT COUNT(*)
                        FROM information_schema.statistics s
                        WHERE s.table_schema = c.table_schema
                        AND s.table_name = c.table_name
                        AND s.column_name = c.column_name
                    ) as has_index
                FROM information_schema.columns c
                WHERE c.data_type = 'json'
                AND c.table_schema NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema')
                ORDER BY c.table_schema, c.table_name, c.column_name
            """)
            json_columns = cursor.fetchall()

            result['details']['summary']['total_json_columns'] = len(json_columns)

            if json_columns:
                result['status'] = 'AMBER'
                for col in json_columns:
                    result['details']['json_columns'].append({
                        'schema': col['table_schema'],
                        'table': col['table_name'],
                        'column': col['column_name'],
                        'has_index': col['has_index'] > 0
                    })

                    if col['has_index'] == 0:
                        result['details']['summary']['columns_without_indexes'] += 1

                # Check for JSON functions in stored routines
                cursor.execute("""
                    SELECT routine_schema, routine_name, routine_type
                    FROM information_schema.routines
                    WHERE routine_schema NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema')
                    AND (
                        routine_definition LIKE '%JSON_%'
                        OR routine_definition LIKE '%->%'
                        OR routine_definition LIKE '%->>%'
                    )
                """)
                json_routines = cursor.fetchall()
                result['details']['json_in_routines'] = json_routines
                result['details']['summary']['routines_with_json'] = len(json_routines)

                # Generate recommendations
                result['issues'].append(
                    f"Found {len(json_columns)} JSON columns ({result['details']['summary']['columns_without_indexes']} without indexes)"
                )

                result['recommendations'].extend([
                    "JSON Optimization Opportunities in MySQL 8.0:",
                    f"- Consider multi-valued indexes for JSON array fields:",
                    "  CREATE INDEX idx ON table ((CAST(json_col->'$.array[*]' AS UNSIGNED ARRAY)));",
                    "- Use JSON_TABLE() for better query performance:",
                    "  SELECT * FROM table, JSON_TABLE(json_col, '$.path[*]' COLUMNS(...)) AS jt;",
                    "- Consider functional indexes for frequently queried JSON paths:",
                    "  CREATE INDEX idx ON table ((json_col->'$.field'));",
                    "- Test new JSON functions: JSON_OVERLAPS(), JSON_VALUE(), etc."
                ])

                if json_routines:
                    result['recommendations'].append(
                        f"Review {len(json_routines)} stored routines using JSON functions for compatibility"
                    )
            else:
                result['recommendations'].append("No JSON columns found in database")

            return result
        except Exception as e:
            return {
                'name': 'JSON Usage and Optimization',
                'description': 'Analyzes JSON column usage and recommends MySQL 8.0 JSON optimization opportunities',
                'status': 'ERROR',
                'issues': [f"Error checking JSON usage: {str(e)}"],
                'recommendations': ["Verify database permissions"]
            }
        finally:
            if cursor:
                cursor.close()

    def _check_stored_routine_complexity(self, conn):
        """
        Check 14: Stored Routine Complexity
        Analyze stored procedures and functions for complexity and potential issues.
        """
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            result = {
                'name': 'Stored Routine Complexity',
                'description': 'Evaluates stored procedures and functions for size, complexity, and potential upgrade issues',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'complex_routines': [],
                    'routines_with_dynamic_sql': [],
                    'summary': {
                        'total_routines': 0,
                        'complex_routines_count': 0,
                        'dynamic_sql_count': 0
                    }
                }
            }

            # Get stored routine complexity metrics
            cursor.execute("""
                SELECT
                    routine_schema,
                    routine_name,
                    routine_type,
                    LENGTH(routine_definition) as definition_length,
                    created,
                    last_altered,
                    definer,
                    security_type,
                    sql_data_access,
                    is_deterministic
                FROM information_schema.routines
                WHERE routine_schema NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema')
                ORDER BY definition_length DESC
            """)
            routines = cursor.fetchall()
            result['details']['summary']['total_routines'] = len(routines)

            if not routines:
                result['recommendations'].append("No stored routines found")
                return result

            # Analyze routines
            for routine in routines:
                # Check for large/complex routines (>10KB)
                if routine['definition_length'] > 10240:
                    result['status'] = 'AMBER' if result['status'] == 'GREEN' else result['status']
                    result['details']['complex_routines'].append({
                        'schema': routine['routine_schema'],
                        'name': routine['routine_name'],
                        'type': routine['routine_type'],
                        'size_kb': round(routine['definition_length'] / 1024, 2)
                    })
                    result['details']['summary']['complex_routines_count'] += 1
                    result['issues'].append(
                        f"{routine['routine_type']} '{routine['routine_schema']}.{routine['routine_name']}' "
                        f"is {round(routine['definition_length'] / 1024, 2)}KB (large/complex)"
                    )

            # Check for dynamic SQL usage
            cursor.execute("""
                SELECT routine_schema, routine_name, routine_type
                FROM information_schema.routines
                WHERE routine_schema NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema')
                AND routine_definition LIKE '%PREPARE%'
                AND routine_definition LIKE '%EXECUTE%'
            """)
            dynamic_sql_routines = cursor.fetchall()
            result['details']['routines_with_dynamic_sql'] = dynamic_sql_routines
            result['details']['summary']['dynamic_sql_count'] = len(dynamic_sql_routines)

            if dynamic_sql_routines:
                result['status'] = 'AMBER' if result['status'] == 'GREEN' else result['status']
                for routine in dynamic_sql_routines:
                    result['issues'].append(
                        f"{routine['routine_type']} '{routine['routine_schema']}.{routine['routine_name']}' uses dynamic SQL"
                    )

            # Generate recommendations
            if result['status'] != 'GREEN':
                result['recommendations'].extend([
                    "Complex Stored Routine Recommendations:",
                    "- Test all stored procedures/functions thoroughly in MySQL 8.0 environment",
                    "- Consider refactoring large routines (>10KB) into smaller, manageable units",
                    "- Review dynamic SQL execution with new 8.0 parser",
                    "- Document routine dependencies before upgrade",
                    "- Test error handling and exception scenarios"
                ])
            else:
                result['recommendations'].append(f"Found {len(routines)} stored routines - all appear compatible")

            return result
        except Exception as e:
            return {
                'name': 'Stored Routine Complexity',
                'description': 'Evaluates stored procedures and functions for size, complexity, and potential upgrade issues',
                'status': 'ERROR',
                'issues': [f"Error checking stored routine complexity: {str(e)}"],
                'recommendations': ["Verify database permissions"]
            }
        finally:
            if cursor:
                cursor.close()

    def _check_spatial_srid(self, conn):
        """
        Check 15: Spatial Data SRID Requirements
        Identify spatial columns lacking explicit SRID (required in MySQL 8.0).
        """
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            result = {
                'name': 'Spatial Data SRID Requirements',
                'description': 'Identifies spatial columns missing explicit SRID declarations required by MySQL 8.0',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'spatial_columns': [],
                    'summary': {
                        'total_spatial_columns': 0,
                        'columns_with_spatial_indexes': 0
                    }
                }
            }

            # Find all spatial columns
            cursor.execute("""
                SELECT
                    c.table_schema,
                    c.table_name,
                    c.column_name,
                    c.column_type,
                    c.data_type,
                    (
                        SELECT COUNT(*)
                        FROM information_schema.statistics s
                        WHERE s.table_schema = c.table_schema
                        AND s.table_name = c.table_name
                        AND s.column_name = c.column_name
                        AND s.index_type = 'SPATIAL'
                    ) as has_spatial_index,
                    t.table_rows
                FROM information_schema.columns c
                JOIN information_schema.tables t
                    ON c.table_schema = t.table_schema
                    AND c.table_name = t.table_name
                WHERE c.data_type IN (
                    'geometry', 'point', 'linestring', 'polygon',
                    'multipoint', 'multilinestring', 'multipolygon',
                    'geometrycollection'
                )
                AND c.table_schema NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema')
                ORDER BY c.table_schema, c.table_name, c.column_name
            """)
            spatial_columns = cursor.fetchall()

            result['details']['summary']['total_spatial_columns'] = len(spatial_columns)

            if not spatial_columns:
                result['recommendations'].append("No spatial data columns found")
                return result

            # Analyze spatial columns
            result['status'] = 'RED'  # Spatial columns without explicit SRID will fail in 8.0

            for col in spatial_columns:
                result['details']['spatial_columns'].append({
                    'schema': col['table_schema'],
                    'table': col['table_name'],
                    'column': col['column_name'],
                    'type': col['data_type'],
                    'has_spatial_index': col['has_spatial_index'] > 0
                })

                result['issues'].append(
                    f"Spatial column '{col['table_schema']}.{col['table_name']}.{col['column_name']}' "
                    f"({col['data_type']}) requires explicit SRID for MySQL 8.0"
                )

                if col['has_spatial_index'] > 0:
                    result['details']['summary']['columns_with_spatial_indexes'] += 1

            # Generate recommendations
            result['recommendations'].extend([
                "CRITICAL: All spatial columns require explicit SRID in MySQL 8.0:",
                "1. Add SRID to spatial columns:",
                "   ALTER TABLE schema.table MODIFY COLUMN location POINT SRID 4326;",
                "   (Common SRIDs: 4326 for WGS84 GPS coordinates, 0 for Cartesian)",
                "",
                "2. Rebuild all spatial indexes after adding SRID:",
                "   ALTER TABLE schema.table DROP INDEX spatial_idx;",
                "   ALTER TABLE schema.table ADD SPATIAL INDEX spatial_idx(location);",
                "",
                "3. Update application code to specify SRID:",
                "   ST_GeomFromText('POINT(1 1)', 4326)",
                "   ST_GeomFromWKB(wkb_data, 4326)",
                "",
                f"Found {len(spatial_columns)} spatial columns requiring SRID specification"
            ])

            return result
        except Exception as e:
            return {
                'name': 'Spatial Data SRID Requirements',
                'description': 'Identifies spatial columns missing explicit SRID declarations required by MySQL 8.0',
                'status': 'ERROR',
                'issues': [f"Error checking spatial SRID requirements: {str(e)}"],
                'recommendations': ["Verify database permissions"]
            }
        finally:
            if cursor:
                cursor.close()

    def _check_functional_index_opportunities(self, conn):
        """
        Check 16: Functional Index Opportunities
        Identify opportunities for MySQL 8.0 functional indexes.
        """
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            result = {
                'name': 'Functional Index Opportunities',
                'description': 'Suggests MySQL 8.0 functional indexes for expressions commonly used in WHERE clauses',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'string_columns': [],
                    'datetime_columns': [],
                    'json_columns': [],
                    'summary': {
                        'total_opportunities': 0
                    }
                }
            }

            # Find columns that could benefit from functional indexes

            # 1. String columns (for UPPER/LOWER functions)
            cursor.execute("""
                SELECT table_schema, table_name, column_name, data_type, column_type
                FROM information_schema.columns
                WHERE table_schema NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema')
                AND data_type IN ('varchar', 'char', 'text')
                AND character_maximum_length IS NOT NULL
                ORDER BY table_schema, table_name, column_name
                LIMIT 20
            """)
            string_columns = cursor.fetchall()
            result['details']['string_columns'] = string_columns

            # 2. DateTime columns (for DATE/YEAR functions)
            cursor.execute("""
                SELECT table_schema, table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema')
                AND data_type IN ('datetime', 'timestamp', 'date')
                ORDER BY table_schema, table_name, column_name
                LIMIT 20
            """)
            datetime_columns = cursor.fetchall()
            result['details']['datetime_columns'] = datetime_columns

            # 3. JSON columns (for path expressions)
            cursor.execute("""
                SELECT table_schema, table_name, column_name
                FROM information_schema.columns
                WHERE table_schema NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema')
                AND data_type = 'json'
                ORDER BY table_schema, table_name, column_name
            """)
            json_columns = cursor.fetchall()
            result['details']['json_columns'] = json_columns

            total_opportunities = len(string_columns) + len(datetime_columns) + len(json_columns)
            result['details']['summary']['total_opportunities'] = total_opportunities

            if total_opportunities > 0:
                result['issues'].append(
                    f"Found {total_opportunities} columns that could benefit from functional indexes"
                )

                result['recommendations'].extend([
                    "Functional Index Opportunities in MySQL 8.0:",
                    "",
                    "1. For case-insensitive string searches:",
                    "   CREATE INDEX idx_name_lower ON table ((LOWER(name)));",
                    "   Then use: SELECT * FROM table WHERE LOWER(name) = 'value';",
                    "",
                    "2. For date-based queries:",
                    "   CREATE INDEX idx_created_date ON table ((DATE(created_at)));",
                    "   CREATE INDEX idx_created_year ON table ((YEAR(created_at)));",
                    "",
                    "3. For JSON path expressions:",
                    "   CREATE INDEX idx_json_field ON table ((json_col->'$.field'));",
                    "   CREATE INDEX idx_json_array ON table ((CAST(json_col->'$.array[*]' AS UNSIGNED ARRAY)));",
                    "",
                    "Note: Test performance before deploying to production",
                    "Functional indexes work best for frequently executed queries"
                ])
            else:
                result['recommendations'].append("No obvious functional index opportunities identified")

            return result
        except Exception as e:
            return {
                'name': 'Functional Index Opportunities',
                'description': 'Suggests MySQL 8.0 functional indexes for expressions commonly used in WHERE clauses',
                'status': 'ERROR',
                'issues': [f"Error checking functional index opportunities: {str(e)}"],
                'recommendations': ["Verify database permissions"]
            }
        finally:
            if cursor:
                cursor.close()

    def _check_index_statistics(self, conn):
        """
        Check 17: Index Statistics and Duplication
        Identify duplicate indexes and low-cardinality indexes.
        """
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            result = {
                'name': 'Index Statistics and Duplication',
                'description': 'Detects duplicate indexes and low-cardinality indexes that impact performance',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'duplicate_indexes': [],
                    'low_cardinality_indexes': [],
                    'summary': {
                        'total_indexes': 0,
                        'duplicate_count': 0,
                        'low_cardinality_count': 0
                    }
                }
            }

            # Get all indexes with their columns
            cursor.execute("""
                SELECT
                    table_schema,
                    table_name,
                    index_name,
                    GROUP_CONCAT(column_name ORDER BY seq_in_index) as columns,
                    index_type,
                    non_unique,
                    MAX(cardinality) as max_cardinality
                FROM information_schema.statistics
                WHERE table_schema NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema')
                AND index_name != 'PRIMARY'
                GROUP BY table_schema, table_name, index_name, index_type, non_unique
                ORDER BY table_schema, table_name, index_name
            """)
            indexes = cursor.fetchall()
            result['details']['summary']['total_indexes'] = len(indexes)

            if not indexes:
                result['recommendations'].append("No secondary indexes found")
                return result

            # Find duplicate indexes
            index_map = {}
            for idx in indexes:
                key = f"{idx['table_schema']}.{idx['table_name']}"
                if key not in index_map:
                    index_map[key] = []
                index_map[key].append(idx)

            for table_key, table_indexes in index_map.items():
                # Compare indexes for duplicates
                for i in range(len(table_indexes)):
                    for j in range(i + 1, len(table_indexes)):
                        idx1 = table_indexes[i]
                        idx2 = table_indexes[j]

                        # Check if same column set
                        if idx1['columns'] == idx2['columns']:
                            result['status'] = 'AMBER' if result['status'] == 'GREEN' else result['status']
                            result['details']['duplicate_indexes'].append({
                                'table': table_key,
                                'index1': idx1['index_name'],
                                'index2': idx2['index_name'],
                                'columns': idx1['columns']
                            })
                            result['details']['summary']['duplicate_count'] += 1
                            result['issues'].append(
                                f"Duplicate indexes on {table_key}: '{idx1['index_name']}' and '{idx2['index_name']}' (both on {idx1['columns']})"
                            )

            # Check for low cardinality indexes (cardinality < 10)
            for idx in indexes:
                if idx['max_cardinality'] is not None and idx['max_cardinality'] < 10 and idx['non_unique'] == 1:
                    result['status'] = 'AMBER' if result['status'] == 'GREEN' else result['status']
                    result['details']['low_cardinality_indexes'].append({
                        'table': f"{idx['table_schema']}.{idx['table_name']}",
                        'index': idx['index_name'],
                        'cardinality': idx['max_cardinality']
                    })
                    result['details']['summary']['low_cardinality_count'] += 1

            # Generate recommendations
            if result['details']['duplicate_indexes']:
                result['recommendations'].extend([
                    "Remove duplicate indexes to improve performance:",
                    "- Use MySQL 8.0 invisible indexes to test before dropping:",
                    "  ALTER TABLE schema.table ALTER INDEX index_name INVISIBLE;",
                    "  -- Monitor performance, then drop if no issues:",
                    "  DROP INDEX index_name ON schema.table;"
                ])

            if result['details']['low_cardinality_indexes']:
                result['recommendations'].append(
                    f"Review {result['details']['summary']['low_cardinality_count']} low-cardinality indexes for effectiveness"
                )

            if result['status'] == 'GREEN':
                result['recommendations'].append(f"Analyzed {len(indexes)} indexes - no obvious issues found")

            return result
        except Exception as e:
            return {
                'name': 'Index Statistics and Duplication',
                'description': 'Detects duplicate indexes and low-cardinality indexes that impact performance',
                'status': 'ERROR',
                'issues': [f"Error checking index statistics: {str(e)}"],
                'recommendations': ["Verify database permissions"]
            }
        finally:
            if cursor:
                cursor.close()

    def _check_autoinc_exhaustion(self, conn):
        """
        Check 18: Auto-Increment Exhaustion
        Identify tables approaching auto-increment limits.
        """
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            result = {
                'name': 'Auto-Increment Exhaustion',
                'description': 'Identifies auto-increment columns approaching their maximum values based on data type limits',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'high_usage_tables': [],
                    'summary': {
                        'total_autoinc_tables': 0,
                        'critical_count': 0,
                        'warning_count': 0
                    }
                }
            }

            # Get auto-increment information
            # Note: Check for UNSIGNED/SIGNED to use correct max values
            cursor.execute("""
                SELECT
                    t.table_schema,
                    t.table_name,
                    t.auto_increment,
                    c.column_name,
                    c.data_type,
                    c.column_type,
                    CASE
                        -- UNSIGNED values
                        WHEN c.column_type LIKE '%unsigned%' AND c.data_type = 'tinyint' THEN 255
                        WHEN c.column_type LIKE '%unsigned%' AND c.data_type = 'smallint' THEN 65535
                        WHEN c.column_type LIKE '%unsigned%' AND c.data_type = 'mediumint' THEN 16777215
                        WHEN c.column_type LIKE '%unsigned%' AND c.data_type = 'int' THEN 4294967295
                        WHEN c.column_type LIKE '%unsigned%' AND c.data_type = 'bigint' THEN 18446744073709551615
                        -- SIGNED values (default if unsigned not specified)
                        WHEN c.data_type = 'tinyint' THEN 127
                        WHEN c.data_type = 'smallint' THEN 32767
                        WHEN c.data_type = 'mediumint' THEN 8388607
                        WHEN c.data_type = 'int' THEN 2147483647
                        WHEN c.data_type = 'bigint' THEN 9223372036854775807
                    END as max_value
                FROM information_schema.tables t
                JOIN information_schema.columns c
                    ON t.table_schema = c.table_schema
                    AND t.table_name = c.table_name
                WHERE t.table_schema NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema')
                AND t.auto_increment IS NOT NULL
                AND c.extra LIKE '%auto_increment%'
                ORDER BY t.table_schema, t.table_name
            """)
            autoinc_tables = cursor.fetchall()
            result['details']['summary']['total_autoinc_tables'] = len(autoinc_tables)

            if not autoinc_tables:
                result['recommendations'].append("No auto-increment tables found")
                return result

            # Analyze auto-increment usage
            for table in autoinc_tables:
                if table['max_value'] and table['auto_increment']:
                    percent_used = (table['auto_increment'] / table['max_value']) * 100

                    table_info = {
                        'schema': table['table_schema'],
                        'table': table['table_name'],
                        'column': table['column_name'],
                        'column_type': table['column_type'],
                        'current': table['auto_increment'],
                        'max': table['max_value'],
                        'percent_used': round(percent_used, 2)
                    }

                    # Critical: >90% capacity
                    if percent_used > 90:
                        result['status'] = 'RED'
                        result['details']['summary']['critical_count'] += 1
                        result['details']['high_usage_tables'].append(table_info)
                        result['issues'].append(
                            f"CRITICAL: Table '{table['table_schema']}.{table['table_name']}' "
                            f"column '{table['column_name']}' ({table['column_type']}) "
                            f"at {round(percent_used, 1)}% capacity "
                            f"({table['auto_increment']:,} of {table['max_value']:,})"
                        )

                    # Warning: >70% capacity
                    elif percent_used > 70:
                        if result['status'] == 'GREEN':
                            result['status'] = 'AMBER'
                        result['details']['summary']['warning_count'] += 1
                        result['details']['high_usage_tables'].append(table_info)
                        result['issues'].append(
                            f"WARNING: Table '{table['table_schema']}.{table['table_name']}' "
                            f"column '{table['column_name']}' ({table['column_type']}) "
                            f"at {round(percent_used, 1)}% capacity "
                            f"({table['auto_increment']:,} of {table['max_value']:,})"
                        )

            # Generate recommendations
            if result['status'] == 'RED':
                result['recommendations'].extend([
                    "CRITICAL: Auto-increment exhaustion detected!",
                    "",
                    "Immediate Actions:",
                    "1. Convert auto-increment columns to BIGINT:",
                    "   ALTER TABLE schema.table MODIFY COLUMN id BIGINT UNSIGNED AUTO_INCREMENT;",
                    "",
                    "2. Run ANALYZE TABLE after modification:",
                    "   ANALYZE TABLE schema.table;",
                    "",
                    "3. Consider data archiving to reset auto-increment:",
                    "   - Move old data to archive table",
                    "   - Drop and recreate original table",
                    "",
                    f"Found {result['details']['summary']['critical_count']} tables requiring immediate attention"
                ])
            elif result['status'] == 'AMBER':
                result['recommendations'].extend([
                    "Monitor auto-increment usage:",
                    "- Plan to convert columns to larger data types before 90% capacity",
                    "- Consider implementing data archiving strategy",
                    "- Monitor growth rate and project exhaustion timeline",
                    "",
                    f"Found {result['details']['summary']['warning_count']} tables approaching capacity limits"
                ])
            else:
                result['recommendations'].append(
                    f"Analyzed {len(autoinc_tables)} auto-increment tables - all within safe limits"
                )

            return result
        except Exception as e:
            return {
                'name': 'Auto-Increment Exhaustion',
                'description': 'Identifies auto-increment columns approaching their maximum values based on data type limits',
                'status': 'ERROR',
                'issues': [f"Error checking auto-increment exhaustion: {str(e)}"],
                'recommendations': ["Verify database permissions"]
            }
        finally:
            if cursor:
                cursor.close()

    def _check_replication_topology(self, conn):
        """
        Check 19: Replication Topology
        Analyze replication configuration and lag (NO GTID recommendations per user requirement).
        """
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            result = {
                'name': 'Replication Topology',
                'description': 'Analyzes replication configuration, lag, and readiness for upgrade with minimal downtime',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'replication_status': {},
                    'long_running_transactions': [],
                    'summary': {
                        'is_replica': False,
                        'replication_lag_seconds': None,
                        'long_transactions_count': 0
                    }
                }
            }

            # Check replication status
            try:
                cursor.execute("SHOW SLAVE STATUS")
                slave_status = cursor.fetchone()

                if slave_status:
                    result['details']['summary']['is_replica'] = True
                    result['details']['replication_status'] = {
                        'slave_io_running': slave_status.get('Slave_IO_Running'),
                        'slave_sql_running': slave_status.get('Slave_SQL_Running'),
                        'seconds_behind_master': slave_status.get('Seconds_Behind_Master'),
                        'last_error': slave_status.get('Last_Error')
                    }

                    lag_seconds = slave_status.get('Seconds_Behind_Master')
                    if lag_seconds is not None:
                        result['details']['summary']['replication_lag_seconds'] = lag_seconds

                        # Critical: lag >60 seconds
                        if lag_seconds > 60:
                            result['status'] = 'RED'
                            result['issues'].append(
                                f"CRITICAL: Replication lag is {lag_seconds} seconds (>60s threshold)"
                            )
                        # Warning: lag >10 seconds
                        elif lag_seconds > 10:
                            result['status'] = 'AMBER' if result['status'] == 'GREEN' else result['status']
                            result['issues'].append(
                                f"WARNING: Replication lag is {lag_seconds} seconds"
                            )
            except Exception:
                # Not a replica or permission issue
                pass

            # Check for long-running transactions that could block replication
            cursor.execute("""
                SELECT
                    id,
                    user,
                    host,
                    db,
                    command,
                    time,
                    state,
                    LEFT(info, 100) as query_preview
                FROM information_schema.processlist
                WHERE command NOT IN ('Sleep', 'Binlog Dump', 'Binlog Dump GTID')
                AND time > 300
                ORDER BY time DESC
            """)
            long_transactions = cursor.fetchall()
            result['details']['long_running_transactions'] = long_transactions
            result['details']['summary']['long_transactions_count'] = len(long_transactions)

            if long_transactions:
                result['status'] = 'AMBER' if result['status'] == 'GREEN' else result['status']
                result['issues'].append(
                    f"Found {len(long_transactions)} long-running transactions (>5 minutes)"
                )

            # Generate recommendations (NO GTID per user requirement)
            if result['status'] != 'GREEN':
                result['recommendations'].extend([
                    "Replication Recommendations:",
                    "",
                    "Before Upgrade:",
                    "- Resolve any replication lag before starting upgrade",
                    "- Kill or complete long-running transactions",
                    "- Monitor replication health closely",
                    "",
                    "During Upgrade:",
                    "- For Aurora: Upgrade replicas before primary instance",
                    "- Monitor replication lag throughout upgrade process",
                    "- Have rollback plan ready",
                    "",
                    "After Upgrade:",
                    "- Verify replication is functioning correctly",
                    "- Monitor for any lag or errors",
                    "- Test failover procedures"
                ])

                if long_transactions:
                    result['recommendations'].append(
                        "\nLong-running transactions detected - investigate and resolve before upgrade"
                    )
            else:
                if result['details']['summary']['is_replica']:
                    result['recommendations'].append("Replication is healthy and ready for upgrade")
                else:
                    result['recommendations'].append("Not configured as a replica - no replication checks needed")

            return result
        except Exception as e:
            return {
                'name': 'Replication Topology',
                'description': 'Analyzes replication configuration, lag, and readiness for upgrade with minimal downtime',
                'status': 'ERROR',
                'issues': [f"Error checking replication topology: {str(e)}"],
                'recommendations': ["Verify database permissions"]
            }
        finally:
            if cursor:
                cursor.close()

    def _check_connection_configuration(self, conn):
        """
        Check 20: Connection Configuration
        Analyze connection patterns and session settings.
        """
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            result = {
                'name': 'Connection Configuration',
                'description': 'Reviews connection limits, thread cache, and connection-related settings for optimal upgrade performance',
                'status': 'GREEN',
                'issues': [],
                'recommendations': [],
                'details': {
                    'connection_stats': {},
                    'system_variables': {},
                    'summary': {
                        'total_connections': 0,
                        'sleeping_connections': 0,
                        'active_connections': 0,
                        'max_connections': 0,
                        'usage_percent': 0
                    }
                }
            }

            # Get connection statistics from performance_schema
            try:
                cursor.execute("""
                    SELECT
                        processlist_user,
                        processlist_host,
                        COUNT(*) as connection_count,
                        SUM(IF(processlist_command = 'Sleep', 1, 0)) as sleeping,
                        SUM(IF(processlist_time > 30, 1, 0)) as long_running
                    FROM performance_schema.threads
                    WHERE processlist_user IS NOT NULL
                    AND processlist_user NOT IN ('system user', 'rdsadmin')
                    GROUP BY processlist_user, processlist_host
                    ORDER BY connection_count DESC
                    LIMIT 10
                """)
                connection_stats = cursor.fetchall()
                result['details']['connection_stats'] = connection_stats

                # Calculate totals
                total_conn = sum(c['connection_count'] for c in connection_stats)
                total_sleeping = sum(c['sleeping'] for c in connection_stats)
                result['details']['summary']['total_connections'] = total_conn
                result['details']['summary']['sleeping_connections'] = total_sleeping
                result['details']['summary']['active_connections'] = total_conn - total_sleeping
            except Exception:
                # performance_schema might not be available
                pass

            # Get system variables
            cursor.execute("""
                SELECT
                    @@max_connections as max_connections,
                    @@max_user_connections as max_user_connections,
                    @@thread_cache_size as thread_cache_size,
                    @@connect_timeout as connect_timeout,
                    @@wait_timeout as wait_timeout,
                    @@interactive_timeout as interactive_timeout
            """)
            system_vars = cursor.fetchone()
            result['details']['system_variables'] = system_vars

            if system_vars:
                result['details']['summary']['max_connections'] = system_vars['max_connections']

                # Check connection usage
                if result['details']['summary']['total_connections'] > 0:
                    usage_percent = (result['details']['summary']['total_connections'] / system_vars['max_connections']) * 100
                    result['details']['summary']['usage_percent'] = round(usage_percent, 2)

                    # Warning: >80% capacity
                    if usage_percent > 80:
                        result['status'] = 'AMBER'
                        result['issues'].append(
                            f"Connection usage at {round(usage_percent, 1)}% of max_connections ({result['details']['summary']['total_connections']}/{system_vars['max_connections']})"
                        )

            # Generate recommendations
            if result['status'] != 'GREEN':
                result['recommendations'].extend([
                    "Connection Configuration Recommendations:",
                    "",
                    "1. Consider increasing max_connections for MySQL 8.0:",
                    "   SET GLOBAL max_connections = <higher_value>;",
                    "   (Or update parameter group for RDS/Aurora)",
                    "",
                    "2. Review application connection pooling:",
                    "   - Ensure proper connection pool sizing",
                    "   - Implement connection timeout settings",
                    "   - Monitor for connection leaks",
                    "",
                    "3. Optimize thread cache:",
                    "   SET GLOBAL thread_cache_size = <optimized_value>;",
                    "   (Recommended: 8 + (max_connections / 100))",
                    "",
                    "4. Test with caching_sha2_password plugin:",
                    "   - MySQL 8.0 default authentication may impact connection setup time",
                    "   - Test application connection behavior in non-production first"
                ])
            else:
                result['recommendations'].append(
                    f"Connection configuration is healthy - {result['details']['summary']['usage_percent']}% utilization"
                )

            return result
        except Exception as e:
            return {
                'name': 'Connection Configuration',
                'description': 'Reviews connection limits, thread cache, and connection-related settings for optimal upgrade performance',
                'status': 'ERROR',
                'issues': [f"Error checking connection configuration: {str(e)}"],
                'recommendations': ["Verify database permissions"]
            }
        finally:
            if cursor:
                cursor.close()