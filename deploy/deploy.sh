#!/bin/bash
# Main deployment script for Post Generation project
# This script clones/updates the repository and installs dependencies

set -e  # Exit on error

# Configuration
GIT_REPO_URL="${GIT_REPO_URL:-}"  # Set this environment variable or modify here
PROJECT_DIR="${PROJECT_DIR:-$HOME/post_generation}"

echo "🚀 Starting deployment of Post Generation project..."

# Check if GIT_REPO_URL is set
if [ -z "$GIT_REPO_URL" ]; then
    echo "❌ Error: GIT_REPO_URL environment variable is not set"
    echo "   Please set it before running this script:"
    echo "   export GIT_REPO_URL='https://github.com/yourusername/post_generation.git'"
    exit 1
fi

# Ensure uv is in PATH
export PATH="$HOME/.cargo/bin:$PATH"

# Clone or update repository
if [ -d "$PROJECT_DIR" ]; then
    echo "📥 Updating existing repository..."
    cd "$PROJECT_DIR"
    git pull origin main || git pull origin master
else
    echo "📥 Cloning repository..."
    git clone "$GIT_REPO_URL" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# Install Python dependencies using uv
echo "📦 Installing Python dependencies..."
export PATH="$HOME/.cargo/bin:$PATH"
uv sync

echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Copy your configuration files to $PROJECT_DIR/.config/"
echo "2. Run: bash deploy/setup_systemd.sh"
echo "3. Start the service: sudo systemctl start post-generation"
