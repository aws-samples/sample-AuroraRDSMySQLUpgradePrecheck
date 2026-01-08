#!/bin/bash
# Helper script to discover your Aurora/RDS clusters and Secrets Manager secrets
# This helps you configure config.yaml

set -e

echo "========================================="
echo "Aurora Upgrade Checker - Cluster Discovery"
echo "========================================="
echo ""

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo "❌ ERROR: AWS CLI is not installed"
    echo "Install it from: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if jq is available (optional but helpful)
if ! command -v jq &> /dev/null; then
    echo "⚠️  WARNING: jq is not installed (optional but recommended)"
    echo "Install it with: brew install jq (macOS) or apt install jq (Linux)"
    echo ""
fi

# Get AWS region
echo "Enter your AWS region (e.g., us-east-1, us-west-2):"
read -r AWS_REGION

if [ -z "$AWS_REGION" ]; then
    echo "❌ Region is required"
    exit 1
fi

echo ""
echo "Using region: $AWS_REGION"
echo ""

# Test AWS credentials
echo "Testing AWS credentials..."
if ! aws sts get-caller-identity --region "$AWS_REGION" > /dev/null 2>&1; then
    echo "❌ ERROR: Cannot authenticate with AWS"
    echo "Run: aws configure"
    exit 1
fi

echo "✓ AWS credentials valid"
echo ""

# Discover Aurora clusters
echo "========================================="
echo "1. Discovering Aurora MySQL Clusters"
echo "========================================="
echo ""

AURORA_CLUSTERS=$(aws rds describe-db-clusters \
    --region "$AWS_REGION" \
    --query 'DBClusters[?Engine==`aurora-mysql`].[DBClusterIdentifier,EngineVersion,Endpoint,Port]' \
    --output text)

if [ -z "$AURORA_CLUSTERS" ]; then
    echo "No Aurora MySQL clusters found."
else
    echo "Found Aurora MySQL clusters:"
    echo ""
    echo "$AURORA_CLUSTERS" | while read -r IDENTIFIER VERSION ENDPOINT PORT; do
        echo "  Cluster ID: $IDENTIFIER"
        echo "  Version:    $VERSION"
        echo "  Endpoint:   $ENDPOINT"
        echo "  Port:       $PORT"
        echo ""
    done
fi

# Discover RDS instances
echo "========================================="
echo "2. Discovering RDS MySQL Instances"
echo "========================================="
echo ""

RDS_INSTANCES=$(aws rds describe-db-instances \
    --region "$AWS_REGION" \
    --query 'DBInstances[?Engine==`mysql`].[DBInstanceIdentifier,EngineVersion,Endpoint.Address,Endpoint.Port]' \
    --output text)

if [ -z "$RDS_INSTANCES" ]; then
    echo "No RDS MySQL instances found."
else
    echo "Found RDS MySQL instances:"
    echo ""
    echo "$RDS_INSTANCES" | while read -r IDENTIFIER VERSION ENDPOINT PORT; do
        echo "  Instance ID: $IDENTIFIER"
        echo "  Version:     $VERSION"
        echo "  Endpoint:    $ENDPOINT"
        echo "  Port:        $PORT"
        echo ""
    done
fi

# Discover Secrets
echo "========================================="
echo "3. Discovering Secrets Manager Secrets"
echo "========================================="
echo ""

SECRETS=$(aws secretsmanager list-secrets \
    --region "$AWS_REGION" \
    --query 'SecretList[*].[Name,ARN]' \
    --output text)

if [ -z "$SECRETS" ]; then
    echo "No secrets found in Secrets Manager."
else
    echo "Found secrets:"
    echo ""
    echo "$SECRETS" | while read -r NAME ARN; do
        echo "  Name: $NAME"
        echo "  ARN:  $ARN"
        echo ""
    done
fi

# Generate config.yaml template
echo "========================================="
echo "4. Generating config.yaml Template"
echo "========================================="
echo ""

CONFIG_FILE="config/config.yaml"
TEMPLATE_FILE="/tmp/auc_config_template_$$.yaml"

cat > "$TEMPLATE_FILE" << EOF
# Aurora Upgrade Checker Configuration
# Generated on $(date)

aws:
  region: $AWS_REGION

authentication:
  method: secrets_manager

  # Map your cluster/instance IDs to secret names
  secrets:
EOF

# Add Aurora clusters
if [ -n "$AURORA_CLUSTERS" ]; then
    echo "    # Aurora MySQL Clusters:" >> "$TEMPLATE_FILE"
    echo "$AURORA_CLUSTERS" | while read -r IDENTIFIER VERSION ENDPOINT PORT; do
        if [[ "$VERSION" == 5.7* ]]; then
            echo "    $IDENTIFIER: YOUR_SECRET_NAME_HERE  # Version: $VERSION" >> "$TEMPLATE_FILE"
        else
            echo "    # $IDENTIFIER: YOUR_SECRET_NAME_HERE  # Version: $VERSION (not 5.7.x)" >> "$TEMPLATE_FILE"
        fi
    done
    echo "" >> "$TEMPLATE_FILE"
fi

# Add RDS instances
if [ -n "$RDS_INSTANCES" ]; then
    echo "    # RDS MySQL Instances:" >> "$TEMPLATE_FILE"
    echo "$RDS_INSTANCES" | while read -r IDENTIFIER VERSION ENDPOINT PORT; do
        if [[ "$VERSION" == 5.7* ]]; then
            echo "    $IDENTIFIER: YOUR_SECRET_NAME_HERE  # Version: $VERSION" >> "$TEMPLATE_FILE"
        else
            echo "    # $IDENTIFIER: YOUR_SECRET_NAME_HERE  # Version: $VERSION (not 5.7.x)" >> "$TEMPLATE_FILE"
        fi
    done
    echo "" >> "$TEMPLATE_FILE"
fi

cat >> "$TEMPLATE_FILE" << EOF

assessment:
  parallel_checks: false
  include_replicas: false
  timeouts:
    default: 300

report:
  output_dir: reports
  formats:
    - html
    - json

logging:
  level: INFO
EOF

echo "Template generated at: $TEMPLATE_FILE"
echo ""
echo "========================================="
echo "5. Next Steps"
echo "========================================="
echo ""
echo "1. Review the generated template:"
echo "   cat $TEMPLATE_FILE"
echo ""
echo "2. Update YOUR_SECRET_NAME_HERE with your actual secret names from step 3 above"
echo ""
echo "3. Copy template to config.yaml:"
echo "   cp $TEMPLATE_FILE $CONFIG_FILE"
echo "   vi $CONFIG_FILE  # Edit the secret names"
echo ""
echo "4. Run the assessment:"
echo "   source venv/bin/activate"
echo "   python run_assessment.py --verbose"
echo ""
echo "========================================="
echo ""

# Show available secrets for easy copy-paste
if [ -n "$SECRETS" ]; then
    echo "Available secret names for copy-paste:"
    echo "$SECRETS" | while read -r NAME ARN; do
        echo "  $NAME"
    done
    echo ""
fi

echo "✓ Discovery complete!"
