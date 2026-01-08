"""
Configuration loader for Aurora Upgrade Checker.

Handles loading, validation, and access to configuration settings from YAML files.
"""

import yaml
import os
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigError(Exception):
    """Exception raised for configuration errors."""
    pass


class ConfigLoader:
    """
    Configuration loader and validator.

    Loads configuration from YAML files and provides structured access to settings.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader.

        Args:
            config_path: Path to configuration file (default: config/config.yaml)

        Raises:
            ConfigError: If configuration file cannot be loaded or is invalid
        """
        if config_path is None:
            # Default to config/config.yaml in the project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / 'config' / 'config.yaml'

        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._validate_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Dictionary containing configuration

        Raises:
            ConfigError: If file cannot be loaded or parsed
        """
        if not self.config_path.exists():
            raise ConfigError(f"Configuration file not found: {self.config_path}")

        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            if config is None:
                raise ConfigError("Configuration file is empty")

            return config

        except yaml.YAMLError as e:
            raise ConfigError(f"Failed to parse configuration file: {str(e)}")
        except Exception as e:
            raise ConfigError(f"Failed to load configuration: {str(e)}")

    def _validate_config(self):
        """
        Validate configuration structure and required fields.

        Raises:
            ConfigError: If configuration is invalid
        """
        # Validate AWS section
        if 'aws' not in self.config:
            raise ConfigError("Missing 'aws' section in configuration")

        aws_config = self.config['aws']
        if 'region' not in aws_config:
            raise ConfigError("Missing 'region' in AWS configuration")

        # Validate authentication section
        if 'authentication' not in self.config:
            raise ConfigError("Missing 'authentication' section in configuration")

        auth_config = self.config['authentication']
        if 'method' not in auth_config:
            raise ConfigError("Missing 'method' in authentication configuration")

        auth_method = auth_config['method']
        valid_methods = ['iam', 'secrets_manager', 'config']
        if auth_method not in valid_methods:
            raise ConfigError(
                f"Invalid authentication method '{auth_method}'. "
                f"Valid methods: {', '.join(valid_methods)}"
            )

        # Validate method-specific configuration
        if auth_method == 'secrets_manager':
            if 'secrets' not in auth_config:
                raise ConfigError("Authentication method 'secrets_manager' requires 'secrets' configuration")

        elif auth_method == 'iam':
            if 'iam' not in auth_config:
                raise ConfigError("Authentication method 'iam' requires 'iam' configuration")
            if 'username' not in auth_config['iam']:
                raise ConfigError("IAM authentication requires 'username' configuration")

        elif auth_method == 'config':
            if 'databases' not in auth_config:
                raise ConfigError("Authentication method 'config' requires 'databases' configuration")

    def get_aws_config(self) -> Dict[str, Any]:
        """
        Get AWS configuration.

        Returns:
            Dictionary with AWS settings (region, profile, endpoints, etc.)
        """
        return self.config.get('aws', {})

    def get_region(self) -> str:
        """Get AWS region."""
        return self.config['aws']['region']

    def get_profile(self) -> Optional[str]:
        """Get AWS CLI profile name."""
        return self.config['aws'].get('profile')

    def get_auth_method(self) -> str:
        """Get authentication method (iam, secrets_manager, or config)."""
        return self.config['authentication']['method']

    def get_auth_config(self) -> Dict[str, Any]:
        """
        Get authentication configuration.

        Returns:
            Dictionary with authentication settings
        """
        return self.config.get('authentication', {})

    def get_secrets_config(self) -> Dict[str, str]:
        """
        Get Secrets Manager configuration.

        Returns:
            Dictionary mapping cluster IDs to secret names/ARNs
        """
        return self.config.get('authentication', {}).get('secrets', {})

    def get_iam_username(self) -> Optional[str]:
        """Get IAM database username."""
        return self.config.get('authentication', {}).get('iam', {}).get('username')

    def get_database_configs(self) -> list:
        """
        Get direct database configurations.

        Returns:
            List of database configuration dictionaries
        """
        return self.config.get('authentication', {}).get('databases', [])

    def get_assessment_options(self) -> Dict[str, Any]:
        """
        Get assessment options.

        Returns:
            Dictionary with assessment settings (timeouts, parallelization, etc.)
        """
        return self.config.get('assessment', {})

    def get_timeout(self, check_name: Optional[str] = None) -> int:
        """
        Get timeout for checks.

        Args:
            check_name: Specific check name (optional)

        Returns:
            Timeout in seconds
        """
        assessment = self.config.get('assessment', {})
        timeouts = assessment.get('timeouts', {})

        if check_name and check_name in timeouts:
            return timeouts[check_name]

        return timeouts.get('default', 300)  # Default 5 minutes

    def get_parallel_checks(self) -> bool:
        """Get whether to run checks in parallel."""
        return self.config.get('assessment', {}).get('parallel_checks', False)

    def get_max_workers(self) -> int:
        """Get maximum number of parallel workers."""
        return self.config.get('assessment', {}).get('max_workers', 5)

    def get_report_options(self) -> Dict[str, Any]:
        """
        Get report generation options.

        Returns:
            Dictionary with report settings
        """
        return self.config.get('report', {})

    def get_output_dir(self) -> str:
        """Get output directory for reports."""
        output_dir = self.config.get('report', {}).get('output_dir', 'reports')
        return str(Path(output_dir).absolute())

    def get_report_formats(self) -> list:
        """Get list of report formats to generate."""
        return self.config.get('report', {}).get('formats', ['html', 'json'])

    def get_all(self) -> Dict[str, Any]:
        """
        Get entire configuration.

        Returns:
            Complete configuration dictionary
        """
        return self.config