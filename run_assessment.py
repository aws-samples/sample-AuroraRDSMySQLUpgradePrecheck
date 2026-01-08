#!/usr/bin/env python3

import os
import sys
import yaml
import json
import argparse
from datetime import datetime, date
from decimal import Decimal
import logging

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from aurora_upgrade_checker import AuroraUpgradeChecker
from src.utils.aws_utils import AWSUtils
from src.utils.config_loader import ConfigLoader

# Add this class after the imports
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, bytes):
            return obj.decode('utf-8')
        try:
            return super().default(obj)
        except Exception as e:
            return str(obj) # Fallback to string representation

def set_to_list(obj):
    """Convert sets to lists recursively in nested structures"""
    from decimal import Decimal
    
    if isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, dict):
        return {key: set_to_list(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [set_to_list(item) for item in obj]
    elif isinstance(obj, Decimal): # Add handling for Decimal
        return float(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    
    return obj

def filter_recommendations(assessment_results):
    """Remove specific feature recommendations (GTID and Parallel Query) from assessment results"""
    
    # Keywords to filter out
    filter_keywords = ['gtid', 'parallel query', 'parallel_query']
    
    # Filter detailed summary
    detailed_summary = assessment_results.get('detailed_summary', {})
    
    # Filter common issues
    if 'common_issues' in detailed_summary:
        detailed_summary['common_issues'] = [
            issue for issue in detailed_summary['common_issues'] 
            if not any(keyword in issue.lower() for keyword in filter_keywords)
        ]
    
    # Filter immediate actions
    if 'upgrade_path' in detailed_summary and 'immediate_actions' in detailed_summary['upgrade_path']:
        detailed_summary['upgrade_path']['immediate_actions'] = [
            action for action in detailed_summary['upgrade_path']['immediate_actions'] 
            if not any(keyword in action.lower() for keyword in filter_keywords)
        ]
    
    # Filter parameter changes
    if 'upgrade_path' in detailed_summary and 'parameter_changes' in detailed_summary['upgrade_path']:
        for engine_type in ['aurora', 'rds']:
            if engine_type in detailed_summary['upgrade_path']['parameter_changes']:
                params = detailed_summary['upgrade_path']['parameter_changes'][engine_type]
                # Remove filtered parameters
                keys_to_remove = [key for key in params.keys() 
                                if any(keyword in key.lower() for keyword in filter_keywords)]
                for key in keys_to_remove:
                    del params[key]
    
    # Filter pre-upgrade recommendations
    if 'recommendations' in detailed_summary and 'pre_upgrade' in detailed_summary['recommendations']:
        detailed_summary['recommendations']['pre_upgrade'] = [
            rec for rec in detailed_summary['recommendations']['pre_upgrade'] 
            if not any(keyword in rec.lower() for keyword in filter_keywords)
        ]
    
    # Filter during-upgrade recommendations
    if 'recommendations' in detailed_summary and 'during_upgrade' in detailed_summary['recommendations']:
        detailed_summary['recommendations']['during_upgrade'] = [
            rec for rec in detailed_summary['recommendations']['during_upgrade'] 
            if not any(keyword in rec.lower() for keyword in filter_keywords)
        ]
    
    # Filter post-upgrade recommendations
    if 'recommendations' in detailed_summary and 'post_upgrade' in detailed_summary['recommendations']:
        detailed_summary['recommendations']['post_upgrade'] = [
            rec for rec in detailed_summary['recommendations']['post_upgrade'] 
            if not any(keyword in rec.lower() for keyword in filter_keywords)
        ]
    
    # Filter database-specific checks
    for db_id, db_info in assessment_results.get('databases', {}).items():
        filtered_checks = []
        
        for check in db_info.get('checks', []):
            # Skip checks that are entirely about filtered features
            if any(keyword in check.get('name', '').lower() for keyword in filter_keywords):
                continue
                
            # Filter issues
            if 'issues' in check:
                check['issues'] = [
                    issue for issue in check['issues'] 
                    if not any(keyword in issue.lower() for keyword in filter_keywords)
                ]
            
            # Filter recommendations
            if 'recommendations' in check:
                check['recommendations'] = [
                    rec for rec in check['recommendations'] 
                    if not any(keyword in rec.lower() for keyword in filter_keywords)
                ]
            
            # Update status if no issues left
            if not check.get('issues') and check['status'] != 'GREEN':
                check['status'] = 'GREEN'
                
            filtered_checks.append(check)
        
        db_info['checks'] = filtered_checks
    
    return assessment_results


def generate_summary_report(assessment_results):
    """Generate a comprehensive summary with recommendations"""
    summary = {
        'overview': {
            'total_databases': len(assessment_results.get('databases', {})),
            'databases_needing_upgrade': 0,
            'databases_needing_parameter_updates': 0,
            'aurora_clusters': [],
            'rds_instances': [],
            'status': 'GREEN',
            'total_issues': 0,
            'blocking_issues': 0,
            'warnings': 0
        },
        'upgrade_path': {
            'immediate_actions': [],
            'upgrade_order': [],
            'parameter_changes': {
                'aurora': {
                    'log_bin_trust_function_creators': 'ON',
                    # 'gtid_mode': 'ON',
                    # 'enforce_gtid_consistency': 'ON',
                    'character_set_server': 'utf8mb4',
                    'collation_server': 'utf8mb4_0900_ai_ci'
                },
                'rds': {
                    'binlog_format': 'ROW',
                    # 'gtid_mode': 'ON',
                    # 'enforce_gtid_consistency': 'ON',
                    'log_bin_trust_function_creators': 'ON',
                    'character_set_server': 'utf8mb4',
                    'collation_server': 'utf8mb4_0900_ai_ci',
                    'max_allocated_packet': '67108864(64MB)',
                    'table_open_cache': '4000',
                    'explicit_defaults_for_timestamp': 'ON'
                }
            }
        },
        'common_issues': [],
        'recommendations': {
            'pre_upgrade': [
                "Update parameter groups with recommended settings",
                "Take full backup of all databases",
                "Convert character sets to utf8mb4 where needed",
                "Make sure that the instance have enough resources (CPU, Memory, IOPS, storage) for the upgrade process",
                "Ensure there are no long-running transaction",
                "Make sure HLL is not high"
            ],
            'during_upgrade': [
                "Follow upgrade order as specified",
                "Test each upgrade in non-production first",
                "Monitor replication lag during upgrades",
                "Verify application compatibility",
                "Have rollback plan ready"
            ],
            'post_upgrade': [
                "Verify all stored procedures and views",
                "Check application performance",
                "Update monitoring and alerts",
                "Review and update backup strategies",
                "Document changes and lessons learned"
            ]
        }
    }

    # Analyze each database
    for db_id, db_info in assessment_results.get('databases', {}).items():
        db_type = db_info.get('type', 'UNKNOWN')
        engine_version = db_info.get('version', '')
        db_summary = db_info.get('summary', {})
        
        # Update overall status and counts
        if db_summary.get('status') == 'RED':
            summary['overview']['status'] = 'RED'
            summary['overview']['blocking_issues'] += db_summary.get('blocking_issues', 0)
        elif db_summary.get('status') == 'AMBER' and summary['overview']['status'] != 'RED':
            summary['overview']['status'] = 'AMBER'
            summary['overview']['warnings'] += db_summary.get('warnings', 0)
        
        summary['overview']['total_issues'] += db_summary.get('total_issues', 0)
        
        if '5.7' in engine_version:
            summary['overview']['databases_needing_upgrade'] += 1
            
            if db_type == 'AURORA':
                summary['overview']['aurora_clusters'].append({
                    'identifier': db_id,
                    'version': engine_version,
                    'issues': db_summary.get('total_issues', 0)
                })
            else:
                summary['overview']['rds_instances'].append({
                    'identifier': db_id,
                    'version': engine_version,
                    'issues': db_summary.get('total_issues', 0)
                })

    # Sort databases by version for upgrade order
    aurora_clusters = sorted(summary['overview']['aurora_clusters'], 
                           key=lambda x: x['version'])
    rds_instances = sorted(summary['overview']['rds_instances'], 
                          key=lambda x: x['version'])

    # Generate upgrade order
    summary['upgrade_path']['upgrade_order'] = [
        f"Aurora cluster {cluster['identifier']} ({cluster['version']})"
        for cluster in aurora_clusters
    ] + [
        f"RDS instance {instance['identifier']} ({instance['version']})"
        for instance in rds_instances
    ]

    # Add immediate actions based on common issues - organized by check
    immediate_actions = []
    critical_checks = []

    for db_id, db_info in assessment_results.get('databases', {}).items():
        for check in db_info.get('checks', []):
            if check['status'] == 'RED':
                check_name = check.get('name', 'Unknown Check')
                issues_count = len(check.get('issues', []))

                # Get the first 1-2 key recommendations (not all)
                recommendations = check.get('recommendations', [])
                key_recs = []
                for rec in recommendations[:2]:  # Limit to first 2 recommendations
                    # Skip overly verbose recommendations
                    if len(rec) < 200 and not rec.startswith('Found'):
                        key_recs.append(rec)

                if key_recs:
                    action_text = f"<strong>{check_name}</strong> ({issues_count} issues): {key_recs[0]}"
                    immediate_actions.append(action_text)

    summary['upgrade_path']['immediate_actions'] = immediate_actions[:10]  # Limit to top 10

    # Collect common issues
    common_issues = set()
    for db_id, db_info in assessment_results.get('databases', {}).items():
        for check in db_info.get('checks', []):
            if check['status'] in ['RED', 'AMBER']:
                for issue in check.get('issues', []):
                    common_issues.add(issue)
    
    summary['common_issues'] = list(common_issues)

    return summary

def generate_html_report(assessment_results, cluster_id=None, customer_name=None):
    """Generate HTML report using the template with 2 tabs"""
    try:
        logger.info("=== Starting HTML Report Generation ===")
        
        # Prepare the data
        summary = assessment_results.get('detailed_summary', {})
        
        # Create output directory
        reports_dir = os.path.join('reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        # If cluster_id is specified, filter to only that cluster
        databases = assessment_results.get('databases', {})
        if cluster_id:
            if cluster_id in databases:
                filtered_databases = {cluster_id: databases[cluster_id]}
            else:
                filtered_databases = {}
                logger.warning(f"Cluster ID {cluster_id} not found in assessment results")
        else:
            filtered_databases = databases
            
        # Calculate readiness score
        total_checks = 0
        passed_checks = 0
        red_count = 0
        amber_count = 0
        green_count = 0
        
        for db_id, db_info in filtered_databases.items():
            for check in db_info.get('checks', []):
                total_checks += 1
                if check.get('status') == 'GREEN':
                    passed_checks += 1
                    green_count += 1
                elif check.get('status') == 'AMBER':
                    amber_count += 1
                elif check.get('status') == 'RED':
                    red_count += 1
        
        readiness_score = int((passed_checks / total_checks * 100) if total_checks > 0 else 100)
        
        # Calculate percentages for chart
        # Add these lines before the if total_count > 0: block
        red_percentage = 0
        amber_percentage = 0
        green_percentage = 0

        total_count = red_count + amber_count + green_count
        if total_count > 0:
            red_percentage = int((red_count / total_count * 100))
            amber_percentage = int((amber_count / total_count * 100))
            green_percentage = int((green_count / total_count * 100))
    
            # Ensure at least one segment has width if it has items
            if red_count > 0 and red_percentage == 0:
                red_percentage = 1
            if amber_count > 0 and amber_percentage == 0:
                amber_percentage = 1
            if green_count > 0 and green_percentage == 0:
                green_percentage = 1
        
            chart_html = f"""<div class="chart-bar">
            <div class="bar-segment red" style="width: {red_percentage}%">{red_count}</div>
            <div class="bar-segment amber" style="width: {amber_percentage}%">{amber_count}</div>
            <div class="bar-segment green" style="width: {green_percentage}%">{green_count}</div>
        </div>"""
        else:
            chart_html = """<div class="empty-chart-message">No issues found - all checks passed!</div>"""
        
        # Estimate effort based on issue counts
        if red_count > 5 or total_count > 15:
            effort_level = "high"
            effort_hours = f"{red_count * 8 + amber_count * 4 + green_count}"
        elif red_count > 0 or amber_count > 5:
            effort_level = "medium"
            effort_hours = f"{red_count * 6 + amber_count * 3 + green_count}"
        else:
            effort_level = "low"
            effort_hours = f"{amber_count * 2 + green_count}"
            
        # Count database objects with issues
        tables_count = 0
        tables_with_issues = 0
        procedures_count = 0
        procedures_with_issues = 0
        views_count = 0
        views_with_issues = 0
        triggers_count = 0
        triggers_with_issues = 0
        
        for db_id, db_info in filtered_databases.items():
            # Extract schema info from check results
            for check in db_info.get('checks', []):
                if check.get('name') == 'Schema Information':
                    tables_count = check.get('details', {}).get('summary', {}).get('total_tables', 0)
                    # Estimate tables with issues based on issues list
                    tables_with_issues = len([i for i in check.get('issues', []) if 'table' in i.lower()])
                elif check.get('name') == 'Triggers and Views Check':
                    triggers_count = check.get('details', {}).get('summary', {}).get('trigger_count', 0)
                    views_count = check.get('details', {}).get('summary', {}).get('view_count', 0)
                    # Estimate issues based on status
                    if check.get('status') != 'GREEN':
                        triggers_with_issues = triggers_count // 2  # Rough estimate
                        views_with_issues = views_count // 2  # Rough estimate
                elif check.get('name') == 'Deprecated Features Check':
                    # Try to extract stored procedure count
                    procedures_count = len(check.get('details', {}).get('functions_and_syntax', {}).get('affected_objects', []))
                    procedures_with_issues = procedures_count  # All are affected if listed
        
        # Generate findings content in new enterprise format
        findings_content = ""

        # Map status to icons
        status_icons = {
            'red': '🔴',
            'amber': '🟡',
            'green': '🟢'
        }

        for db_id, db_info in filtered_databases.items():
            # Show ALL checks, not just ones with issues
            for check in db_info.get('checks', []):
                check_status = check.get('status', 'UNKNOWN').lower()
                check_description = check.get('description', '')
                check_name = check.get('name', 'Unknown Check')

                # HTML escape all text content to prevent special characters from breaking HTML
                escaped_name = check_name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                escaped_desc = check_description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

                findings_content += f"""<div class="check-item {check_status}">
    <div class="check-header" onclick="toggleCheck(this)">
        <div class="check-icon {check_status}">
            {status_icons.get(check_status, '●')}
        </div>
        <div class="check-title">
            <div class="check-name">{escaped_name}</div>
            <div class="check-description">{escaped_desc}</div>
        </div>
        <div class="check-badge {check_status}">{check.get('status', 'UNKNOWN')}</div>
        <div class="expand-icon">▼</div>
    </div>
    <div class="check-content">
"""
                # Show issues if any
                if check.get('issues'):
                    findings_content += """        <div class="issues-section">
            <div class="issues-title">⚠️ Issues Detected</div>
            <ul class="issues-list">
"""
                    for issue in check.get('issues', []):
                        # HTML escape to prevent <schema>, <table>, etc. from being interpreted as tags
                        escaped_issue = issue.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        findings_content += f"                <li>{escaped_issue}</li>\n"
                    findings_content += """            </ul>
        </div>
"""
                else:
                    # No issues - show success message
                    findings_content += """        <div class="success-message">
            <span>✓</span>
            <span>No issues found - this check passed successfully</span>
        </div>
"""

                # Show recommendations if any
                if check.get('recommendations'):
                    findings_content += """        <div class="recommendations-section">
            <div class="recommendations-title">💡 Recommendations</div>
            <ul class="recommendations-list">
"""
                    for rec in check.get('recommendations', []):
                        # HTML escape to prevent <schema>, <table>, etc. from being interpreted as tags
                        escaped_rec = rec.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        findings_content += f"                <li>{escaped_rec}</li>\n"
                    findings_content += """            </ul>
        </div>
"""
                findings_content += """    </div>
</div>
"""

        # No immediate actions section - users will click Critical metric card instead
        immediate_actions_html = ""

        # Calculate score color and circular progress
        if readiness_score >= 80:
            score_color = "#27ae60"  # Green
        elif readiness_score >= 60:
            score_color = "#f39c12"  # Amber
        else:
            score_color = "#e74c3c"  # Red

        # Calculate stroke-dashoffset for circular progress (circumference = 2 * π * r = 502.4)
        circumference = 502.4
        score_dashoffset = circumference - (circumference * readiness_score / 100)

        # Get cluster info
        cluster_id_display = "Unknown"
        version_display = "Unknown"
        if cluster_id and cluster_id in databases:
            cluster_id_display = cluster_id
            version_display = databases[cluster_id].get('version', 'Unknown')
        elif filtered_databases:
            first_db = list(filtered_databases.values())[0]
            cluster_id_display = list(filtered_databases.keys())[0]
            version_display = first_db.get('version', 'Unknown')

        # Read the HTML template from file
        template_path = os.path.join('templates', 'enterprise_report_template.html')
        with open(template_path, 'r') as f:
            html_template = f.read()
        
        # Prepare customer banner HTML if customer name provided
        customer_banner_html = ''
        if customer_name:
            customer_banner_html = f'''<div class="customer-banner">
                    <div class="customer-label">Prepared for</div>
                    <div class="customer-name">{customer_name}</div>
                </div>'''

        # Prepare data for report
        report_data = {
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'cluster_id': cluster_id_display,
            'customer_name': customer_name if customer_name else '',
            'customer_banner': customer_banner_html,
            'version': version_display,
            'blocking_issues': summary.get('overview', {}).get('blocking_issues', 0),
            'warnings': summary.get('overview', {}).get('warnings', 0),
            'total_issues': summary.get('overview', {}).get('total_issues', 0),
            'status': summary.get('overview', {}).get('status', 'GREEN'),
            'status_color': summary.get('overview', {}).get('status', 'GREEN').lower(),
            'immediate_actions_html': immediate_actions_html,
            'findings_html': findings_content,
            # Score visualization data
            'readiness_score': readiness_score,
            'score_color': score_color,
            'score_dashoffset': score_dashoffset,
            'red_count': red_count,
            'amber_count': amber_count,
            'green_count': green_count
        }

        # Replace placeholders in template
        for key, value in report_data.items():
            html_template = html_template.replace(f'{{{{{key}}}}}', str(value))
        
        # Save the report
        html_path = os.path.join(reports_dir, 'upgrade_assessment.html')
        with open(html_path, 'w') as f:
            f.write(html_template)
            
        logger.info(f"HTML report generated successfully")
        return html_template

    except Exception as e:
        logger.error(f"Error generating HTML report: {str(e)}")
        logger.exception("Full traceback:")
        return f"""
        <html>
        <body>
            <h1>Error Generating Report</h1>
            <p>An error occurred while generating the report: {str(e)}</p>
        </body>
        </html>
        """


def generate_executive_summary(assessment_results, cluster_id=None):
    """Generate an executive summary in markdown format"""
    summary = assessment_results['detailed_summary']
    
    # If cluster_id is specified, adjust the title
    if cluster_id:
        title = f"MySQL 5.7 to 8.0 Upgrade Assessment for {cluster_id}"
    else:
        title = "MySQL 5.7 to 8.0 Upgrade Assessment"
    
    md = f"""# {title}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview
- Total Databases: {1 if cluster_id else summary['overview']['total_databases']}
- Databases Needing Upgrade: {1 if cluster_id and cluster_id in assessment_results['databases'] and '5.7' in assessment_results['databases'][cluster_id].get('version', '') else summary['overview']['databases_needing_upgrade']}
- Total Issues: {summary['overview']['total_issues']}
- Blocking Issues: {summary['overview']['blocking_issues']}
- Warnings: {summary['overview']['warnings']}

## Overall Status: {summary['overview']['status']}

## Immediate Actions Required
"""
    
    for action in summary['upgrade_path']['immediate_actions']:
        md += f"- {action}\n"
    
    md += "\n## Upgrade Order\n"
    for step in summary['upgrade_path']['upgrade_order']:
        md += f"- {step}\n"
    
    md += "\n## Common Issues Found\n"
    for issue in summary['common_issues']:
        md += f"- {issue}\n"
    
    md += "\n## Recommendations\n"
    
    md += "\n### Pre-Upgrade Tasks\n"
    for rec in summary['recommendations']['pre_upgrade']:
        md += f"- {rec}\n"
    
    md += "\n### During Upgrade\n"
    for rec in summary['recommendations']['during_upgrade']:
        md += f"- {rec}\n"
    
    md += "\n### Post-Upgrade Tasks\n"
    for rec in summary['recommendations']['post_upgrade']:
        md += f"- {rec}\n"
    
    return md

def get_credentials(aws_utils, config_loader, cluster_identifier, endpoint, port=3306):
    """
    Get database credentials based on configured authentication method.

    Args:
        aws_utils: AWSUtils instance
        config_loader: ConfigLoader instance
        cluster_identifier: Cluster/instance identifier
        endpoint: Database endpoint
        port: Database port (default: 3306)

    Returns:
        dict: Credentials with user, password, host, port
    """
    auth_method = config_loader.get_auth_method()

    try:
        if auth_method == 'secrets_manager':
            logger.info(f"Using Secrets Manager for {cluster_identifier}")
            secrets_config = config_loader.get_secrets_config()

            if cluster_identifier not in secrets_config:
                raise ValueError(f"No secret configured for cluster '{cluster_identifier}'. "
                               f"Add it to config.yaml under authentication.secrets")

            secret_name = secrets_config[cluster_identifier]
            credentials = aws_utils.get_secret(secret_name)

            # Use endpoint from cluster if not in secret
            if not credentials.get('host'):
                credentials['host'] = endpoint
            if not credentials.get('port'):
                credentials['port'] = port

            return credentials

        elif auth_method == 'iam':
            logger.info(f"Using IAM authentication for {cluster_identifier}")
            username = config_loader.get_iam_username()

            if not username:
                raise ValueError("IAM username not configured. Set it in config.yaml under authentication.iam.username")

            # Generate IAM auth token
            token = aws_utils.get_iam_auth_token(endpoint, port, username)

            return {
                'user': username,
                'password': token,
                'host': endpoint,
                'port': port
            }

        elif auth_method == 'config':
            logger.info(f"Using config file credentials for {cluster_identifier}")
            databases = config_loader.get_database_configs()

            # Find matching database config
            db_config = next((db for db in databases if db['identifier'] == cluster_identifier), None)

            if not db_config:
                raise ValueError(f"No credentials configured for cluster '{cluster_identifier}'. "
                               f"Add it to config.yaml under authentication.databases")

            return {
                'user': db_config['user'],
                'password': db_config['password'],
                'host': db_config.get('endpoint', endpoint),
                'port': db_config.get('port', port)
            }

        else:
            raise ValueError(f"Unknown authentication method: {auth_method}")

    except Exception as e:
        logger.error(f"Failed to get credentials for {cluster_identifier}: {str(e)}")
        raise

def main():
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Run MySQL upgrade assessment')
        parser.add_argument('--cluster', type=str, help='Specific cluster ID to assess')
        parser.add_argument('--customer', type=str, help='Customer/Company name for the report header')
        parser.add_argument('--region', type=str, help='AWS region (overrides config)')
        parser.add_argument('--profile', type=str, help='AWS CLI profile (overrides config)')
        parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
        args = parser.parse_args()

        # Set logging level
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.setLevel(logging.DEBUG)

        # Load configuration
        try:
            config_loader = ConfigLoader()
        except Exception as e:
            logger.error(f"Failed to load configuration: {str(e)}")
            logger.error("Please ensure config/config.yaml exists and is properly formatted.")
            logger.error("You can copy config/config_example.yaml as a starting point.")
            sys.exit(1)

        # Get AWS settings (CLI args override config)
        region = args.region or config_loader.get_region()
        profile = args.profile or config_loader.get_profile()

        # Initialize utilities
        logger.info(f"Initializing AWS utilities (region: {region}, profile: {profile or 'default'})")
        aws_utils = AWSUtils(region=region, profile=profile)
        checker = AuroraUpgradeChecker()

        logger.info("Discovering MySQL 5.7 databases...")

        # Get clusters (Aurora)
        try:
            all_clusters = aws_utils.get_aurora_clusters()
            logger.info(f"Found {len(all_clusters)} Aurora MySQL 5.7.x clusters")
        except Exception as e:
            logger.error(f"Failed to discover Aurora clusters: {str(e)}")
            all_clusters = []

        # Get RDS instances
        try:
            all_instances = aws_utils.get_rds_instances()
            logger.info(f"Found {len(all_instances)} RDS MySQL 5.7.x instances")
        except Exception as e:
            logger.error(f"Failed to discover RDS instances: {str(e)}")
            all_instances = []

        # Combine all databases
        databases = all_clusters + all_instances

        if not databases:
            logger.error("No MySQL 5.7.x databases found in the specified region.")
            logger.error("Please check:")
            logger.error("  1. AWS credentials are configured correctly")
            logger.error("  2. The region is correct")
            logger.error("  3. IAM permissions are sufficient")
            logger.error("  4. You have MySQL 5.7.x clusters/instances")
            sys.exit(1)

        # If cluster ID is provided, filter databases
        if args.cluster:
            logger.info(f"Filtering to assess only: {args.cluster}")
            databases = [db for db in databases if db['identifier'] == args.cluster]
            if not databases:
                logger.error(f"Cluster/instance '{args.cluster}' not found.")
                logger.error(f"Available databases: {[db['identifier'] for db in (all_clusters + all_instances)]}")
                sys.exit(1)

        logger.info(f"Will assess {len(databases)} database(s)")

        assessment_results = {
            'summary': {
                'total_databases': len(databases),
                'green_databases': 0,
                'amber_databases': 0,
                'red_databases': 0,
                'error_databases': 0
            },
            'databases': {},
            'generated_at': datetime.now().isoformat()
        }

        for db in databases:
            logger.info(f"\n{'='*60}")
            logger.info(f"Assessing {db['type']}: {db['identifier']}")
            logger.info(f"Endpoint: {db['endpoint']}")
            logger.info(f"Version: {db['version']}")
            logger.info(f"{'='*60}")

            try:
                # Get credentials for this database
                credentials = get_credentials(
                    aws_utils,
                    config_loader,
                    db['identifier'],
                    db['endpoint'],
                    db.get('port', 3306)
                )

                # Run the assessment
                results = checker.run_checks(db, credentials)
                assessment_results['databases'][db['identifier']] = results
                
                # Update summary
                if results.get('summary', {}).get('status') == 'GREEN':
                    assessment_results['summary']['green_databases'] += 1
                elif results.get('summary', {}).get('status') == 'AMBER':
                    assessment_results['summary']['amber_databases'] += 1
                elif results.get('summary', {}).get('status') == 'RED':
                    assessment_results['summary']['red_databases'] += 1
                else:
                    assessment_results['summary']['error_databases'] += 1
                    
            except Exception as e:
                logger.error(f"Error assessing {db['identifier']}: {str(e)}")
                assessment_results['databases'][db['identifier']] = {
                    'status': 'ERROR',
                    'message': str(e)
                }
                assessment_results['summary']['error_databases'] += 1

        # Generate comprehensive summary
        assessment_results['detailed_summary'] = generate_summary_report(assessment_results)

        # Add this line to filter out GTID and Parallel Query recommendations
        assessment_results = filter_recommendations(assessment_results)

        # Create output directory
        os.makedirs('reports', exist_ok=True)

        # Convert sets to lists for JSON serialization
        serializable_results = set_to_list(assessment_results)

        # Save JSON report
        json_path = os.path.join('reports', 'upgrade_assessment.json')
        with open(json_path, 'w') as f:
            json.dump(serializable_results, f, indent=2, cls=CustomJSONEncoder)

        # Generate HTML report
        try:
            html_report = generate_html_report(serializable_results, args.cluster, args.customer)
            logger.info(f"HTML report generated successfully")
        except Exception as e:
            logger.error(f"Error generating HTML report: {str(e)}")
            logger.exception("Full traceback:")
            raise

        # Generate executive summary
        try:
            summary_path = os.path.join('reports', 'executive_summary.md')
            with open(summary_path, 'w') as f:
                f.write(generate_executive_summary(serializable_results, args.cluster))
            logger.info(f"Executive summary saved to: {summary_path}")
        except Exception as e:
            logger.error(f"Error generating executive summary: {str(e)}")
            raise

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise

if __name__ == '__main__':
    main()