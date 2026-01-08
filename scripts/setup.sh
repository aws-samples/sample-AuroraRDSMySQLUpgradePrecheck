#!/bin/bash
# Aurora Upgrade Checker - Setup Script
# This script sets up the AUC tool on a fresh system

set -e  # Exit on error

echo "========================================="
echo "Aurora Upgrade Checker - Setup"
echo "========================================="
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 7 ]); then
    echo "ERROR: Python 3.7 or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi
echo "✓ Python version: $PYTHON_VERSION"
echo ""

# Create directories
echo "Creating directories..."
mkdir -p config
mkdir -p reports
mkdir -p logs
mkdir -p src/utils
mkdir -p src/checker
mkdir -p templates
mkdir -p scripts
echo "✓ Directories created"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet
echo "✓ Pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
    echo "✓ Dependencies installed"
else
    echo "WARNING: requirements.txt not found"
fi
echo ""

# Copy example configuration if config doesn't exist
echo "Setting up configuration..."
if [ ! -f "config/config.yaml" ]; then
    if [ -f "config/config_example.yaml" ]; then
        cp config/config_example.yaml config/config.yaml
        echo "✓ Configuration template copied to config/config.yaml"
        echo "  IMPORTANT: Edit config/config.yaml with your settings"
    else
        echo "WARNING: config_example.yaml not found"
    fi
else
    echo "✓ Configuration file already exists"
fi
echo ""

# Check AWS CLI
echo "Checking AWS CLI..."
if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version 2>&1 | awk '{print $1}')
    echo "✓ AWS CLI installed: $AWS_VERSION"

    # Check AWS credentials
    if aws sts get-caller-identity &> /dev/null; then
        echo "✓ AWS credentials configured"
    else
        echo "WARNING: AWS credentials not configured"
        echo "  Run: aws configure"
    fi
else
    echo "WARNING: AWS CLI not installed"
    echo "  Install: https://aws.amazon.com/cli/"
fi
echo ""

# Check MySQL client
echo "Checking MySQL client..."
if command -v mysql &> /dev/null; then
    MYSQL_VERSION=$(mysql --version 2>&1 | awk '{print $5}' | cut -d, -f1)
    echo "✓ MySQL client installed: $MYSQL_VERSION"
else
    echo "INFO: MySQL client not installed (optional for testing)"
fi
echo ""

# Create __init__.py files
echo "Creating Python package files..."
touch src/__init__.py
touch src/utils/__init__.py
touch src/checker/__init__.py
echo "✓ Package files created"
echo ""

# Test imports
echo "Testing Python imports..."
python3 -c "import mysql.connector; import boto3; import yaml" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ Core dependencies importable"
else
    echo "WARNING: Some dependencies failed to import"
fi
echo ""

# Summary
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit config/config.yaml with your AWS and database settings"
echo "2. Configure AWS credentials if not already done:"
echo "   aws configure"
echo "3. Test the tool:"
echo "   source venv/bin/activate"
echo "   python run_assessment.py --help"
echo ""
echo "For more information, see README.md"
echo ""
