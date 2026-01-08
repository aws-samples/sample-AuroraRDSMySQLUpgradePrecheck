"""
AWS utilities for Aurora and RDS MySQL cluster discovery and authentication.

This module provides functionality to:
- Discover Aurora and RDS MySQL clusters in AWS accounts
- Handle multiple authentication methods (IAM, Secrets Manager, Config)
- Test database connectivity
- Manage credentials securely
"""

import boto3
import json
import socket
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError


class AWSUtilsError(Exception):
    """Base exception for AWS Utils."""
    pass


class ClusterDiscoveryError(AWSUtilsError):
    """Exception raised when cluster discovery fails."""
    pass


class AuthenticationError(AWSUtilsError):
    """Exception raised when authentication fails."""
    pass


class ConnectivityError(AWSUtilsError):
    """Exception raised when connectivity test fails."""
    pass


class AWSUtils:
    """
    AWS utilities for RDS/Aurora cluster discovery and credential management.

    Supports three authentication methods:
    1. IAM Database Authentication
    2. AWS Secrets Manager
    3. Direct configuration (config file)
    """

    def __init__(self, region: str = 'us-east-1', profile: Optional[str] = None):
        """
        Initialize AWS utilities.

        Args:
            region: AWS region (default: us-east-1)
            profile: AWS CLI profile name (optional)
        """
        self.region = region
        self.profile = profile

        try:
            session_kwargs = {'region_name': region}
            if profile:
                session_kwargs['profile_name'] = profile

            self.session = boto3.Session(**session_kwargs)
            self.rds_client = self.session.client('rds')
            self.secrets_client = self.session.client('secretsmanager')

        except NoCredentialsError as e:
            raise AuthenticationError(
                f"AWS credentials not found. Please configure AWS CLI or set credentials. Error: {str(e)}"
            )
        except Exception as e:
            raise AWSUtilsError(f"Failed to initialize AWS session: {str(e)}")

    def get_aurora_clusters(self, cluster_ids: Optional[List[str]] = None,
                          tags: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        Discover Aurora MySQL clusters in the account.

        Args:
            cluster_ids: List of specific cluster IDs to discover (optional)
            tags: Dictionary of tags to filter clusters (optional)

        Returns:
            List of cluster information dictionaries

        Raises:
            ClusterDiscoveryError: If cluster discovery fails
        """
        clusters = []

        try:
            # Describe DB clusters
            if cluster_ids:
                # Get specific clusters
                for cluster_id in cluster_ids:
                    try:
                        response = self.rds_client.describe_db_clusters(
                            DBClusterIdentifier=cluster_id
                        )
                        clusters.extend(response.get('DBClusters', []))
                    except ClientError as e:
                        if e.response['Error']['Code'] != 'DBClusterNotFoundFault':
                            raise
            else:
                # Get all clusters with pagination
                paginator = self.rds_client.get_paginator('describe_db_clusters')
                for page in paginator.paginate():
                    clusters.extend(page.get('DBClusters', []))

            # Filter for Aurora MySQL 5.7.x clusters
            aurora_mysql_clusters = []
            for cluster in clusters:
                engine = cluster.get('Engine', '')
                version = cluster.get('EngineVersion', '')

                # Only include Aurora MySQL and MySQL 5.7.x
                if ('aurora-mysql' in engine or engine == 'mysql') and version.startswith('5.7'):
                    cluster_info = self._extract_cluster_info(cluster, 'AURORA' if 'aurora' in engine else 'RDS')

                    # Apply tag filtering if specified
                    if tags:
                        cluster_tags = self._get_cluster_tags(cluster['DBClusterArn'])
                        if all(cluster_tags.get(k) == v for k, v in tags.items()):
                            aurora_mysql_clusters.append(cluster_info)
                    else:
                        aurora_mysql_clusters.append(cluster_info)

            return aurora_mysql_clusters

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            raise ClusterDiscoveryError(
                f"Failed to discover Aurora clusters. Error: {error_code} - {error_msg}"
            )
        except Exception as e:
            raise ClusterDiscoveryError(f"Unexpected error during cluster discovery: {str(e)}")

    def get_rds_instances(self, instance_ids: Optional[List[str]] = None,
                         tags: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        Discover RDS MySQL instances in the account.

        Args:
            instance_ids: List of specific instance IDs to discover (optional)
            tags: Dictionary of tags to filter instances (optional)

        Returns:
            List of instance information dictionaries

        Raises:
            ClusterDiscoveryError: If instance discovery fails
        """
        instances = []

        try:
            # Describe DB instances
            if instance_ids:
                # Get specific instances
                for instance_id in instance_ids:
                    try:
                        response = self.rds_client.describe_db_instances(
                            DBInstanceIdentifier=instance_id
                        )
                        instances.extend(response.get('DBInstances', []))
                    except ClientError as e:
                        if e.response['Error']['Code'] != 'DBInstanceNotFound':
                            raise
            else:
                # Get all instances with pagination
                paginator = self.rds_client.get_paginator('describe_db_instances')
                for page in paginator.paginate():
                    instances.extend(page.get('DBInstances', []))

            # Filter for MySQL 5.7.x instances (non-Aurora)
            mysql_instances = []
            for instance in instances:
                engine = instance.get('Engine', '')
                version = instance.get('EngineVersion', '')

                # Only include MySQL 5.7.x (not Aurora)
                if engine == 'mysql' and version.startswith('5.7'):
                    instance_info = self._extract_instance_info(instance)

                    # Apply tag filtering if specified
                    if tags:
                        instance_tags = self._get_instance_tags(instance['DBInstanceArn'])
                        if all(instance_tags.get(k) == v for k, v in tags.items()):
                            mysql_instances.append(instance_info)
                    else:
                        mysql_instances.append(instance_info)

            return mysql_instances

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            raise ClusterDiscoveryError(
                f"Failed to discover RDS instances. Error: {error_code} - {error_msg}"
            )
        except Exception as e:
            raise ClusterDiscoveryError(f"Unexpected error during instance discovery: {str(e)}")

    def get_iam_auth_token(self, endpoint: str, port: int, username: str) -> str:
        """
        Generate IAM database authentication token.

        Args:
            endpoint: Database endpoint
            port: Database port
            username: Database username

        Returns:
            IAM authentication token

        Raises:
            AuthenticationError: If token generation fails
        """
        try:
            token = self.rds_client.generate_db_auth_token(
                DBHostname=endpoint,
                Port=port,
                DBUsername=username,
                Region=self.region
            )
            return token
        except Exception as e:
            raise AuthenticationError(f"Failed to generate IAM auth token: {str(e)}")

    def get_secret(self, secret_name: str) -> Dict[str, Any]:
        """
        Retrieve credentials from AWS Secrets Manager.

        Args:
            secret_name: Secret name or ARN

        Returns:
            Dictionary with credentials (username, password, host, port)

        Raises:
            AuthenticationError: If secret retrieval fails
        """
        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_name)

            if 'SecretString' in response:
                secret = json.loads(response['SecretString'])
                return {
                    'user': secret.get('username'),
                    'password': secret.get('password'),
                    'host': secret.get('host'),
                    'port': secret.get('port', 3306)
                }
            else:
                raise AuthenticationError("Secret does not contain SecretString")

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                raise AuthenticationError(f"Secret '{secret_name}' not found")
            elif error_code == 'AccessDeniedException':
                raise AuthenticationError(f"Access denied to secret '{secret_name}'")
            else:
                raise AuthenticationError(f"Failed to retrieve secret: {e.response['Error']['Message']}")
        except json.JSONDecodeError:
            raise AuthenticationError("Secret value is not valid JSON")
        except Exception as e:
            raise AuthenticationError(f"Unexpected error retrieving secret: {str(e)}")

    def test_connectivity(self, endpoint: str, port: int, timeout: int = 5) -> bool:
        """
        Test network connectivity to database endpoint.

        Args:
            endpoint: Database endpoint
            port: Database port
            timeout: Connection timeout in seconds (default: 5)

        Returns:
            True if connection successful, False otherwise

        Raises:
            ConnectivityError: If connectivity test fails
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((endpoint, port))
            sock.close()

            if result == 0:
                return True
            else:
                raise ConnectivityError(
                    f"Cannot connect to {endpoint}:{port}. "
                    f"Check security groups, network ACLs, and VPC routing."
                )

        except socket.gaierror:
            raise ConnectivityError(f"Cannot resolve hostname: {endpoint}")
        except socket.timeout:
            raise ConnectivityError(f"Connection timeout to {endpoint}:{port}")
        except Exception as e:
            raise ConnectivityError(f"Connectivity test failed: {str(e)}")

    def _extract_cluster_info(self, cluster: Dict[str, Any], cluster_type: str) -> Dict[str, Any]:
        """Extract relevant information from cluster description."""
        return {
            'identifier': cluster.get('DBClusterIdentifier'),
            'type': cluster_type,
            'engine': cluster.get('Engine'),
            'version': cluster.get('EngineVersion'),
            'endpoint': cluster.get('Endpoint'),
            'reader_endpoint': cluster.get('ReaderEndpoint'),
            'port': cluster.get('Port', 3306),
            'status': cluster.get('Status'),
            'multi_az': cluster.get('MultiAZ', False),
            'storage_encrypted': cluster.get('StorageEncrypted', False),
            'arn': cluster.get('DBClusterArn'),
            'members': [
                {
                    'instance_id': member.get('DBInstanceIdentifier'),
                    'is_writer': member.get('IsClusterWriter', False)
                }
                for member in cluster.get('DBClusterMembers', [])
            ]
        }

    def _extract_instance_info(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant information from instance description."""
        return {
            'identifier': instance.get('DBInstanceIdentifier'),
            'type': 'RDS',
            'engine': instance.get('Engine'),
            'version': instance.get('EngineVersion'),
            'endpoint': instance.get('Endpoint', {}).get('Address') if instance.get('Endpoint') else None,
            'port': instance.get('Endpoint', {}).get('Port', 3306) if instance.get('Endpoint') else 3306,
            'status': instance.get('DBInstanceStatus'),
            'instance_class': instance.get('DBInstanceClass'),
            'multi_az': instance.get('MultiAZ', False),
            'storage_encrypted': instance.get('StorageEncrypted', False),
            'arn': instance.get('DBInstanceArn')
        }

    def _get_cluster_tags(self, arn: str) -> Dict[str, str]:
        """Get tags for a cluster."""
        try:
            response = self.rds_client.list_tags_for_resource(ResourceName=arn)
            return {tag['Key']: tag['Value'] for tag in response.get('TagList', [])}
        except Exception:
            return {}

    def _get_instance_tags(self, arn: str) -> Dict[str, str]:
        """Get tags for an instance."""
        try:
            response = self.rds_client.list_tags_for_resource(ResourceName=arn)
            return {tag['Key']: tag['Value'] for tag in response.get('TagList', [])}
        except Exception:
            return {}