#!/bin/bash
# Main deployment script for Post Generation project
# This script clones/updates the repository and installs dependencies

set -e  # Exit on error

# Configuration
GIT_REPO_URL="${GIT_REPO_URL:-}"  # Set this environment variable or modify here
PROJECT_DIR="${PROJECT_DIR:-$HOME/post_generation}"

echo "🚀 Starting deployment of Post Generation project..."
echo "   GIT_REPO_URL: ${GIT_REPO_URL:0:50}..."  # Show first 50 chars
echo "   PROJECT_DIR: $PROJECT_DIR"

# Check if GIT_REPO_URL is set
if [ -z "$GIT_REPO_URL" ]; then
    echo "❌ Error: GIT_REPO_URL environment variable is not set"
    echo "   Please set it before running this script:"
    echo "   export GIT_REPO_URL='https://github.com/yourusername/post_generation.git'"
    exit 1
fi

# Ensure uv is in PATH (check both common locations)
if [ -f "$HOME/.local/bin/uv" ]; then
    export PATH="$HOME/.local/bin:$PATH"
elif [ -f "$HOME/.cargo/bin/uv" ]; then
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Clone or update repository
if [ -d "$PROJECT_DIR" ]; then
    echo "📥 Updating existing repository..."
    cd "$PROJECT_DIR"
    if [ -d ".git" ]; then
        git pull origin main || git pull origin master || {
            echo "⚠️  Git pull failed, trying to reset..."
            git fetch origin
            git reset --hard origin/main || git reset --hard origin/master
        }
    else
        echo "⚠️  Directory exists but is not a git repository. Removing and cloning fresh..."
        cd "$HOME"
        rm -rf "$PROJECT_DIR"
        git clone "$GIT_REPO_URL" "$PROJECT_DIR"
        cd "$PROJECT_DIR"
    fi
else
    echo "📥 Cloning repository..."
    echo "   Repository: $GIT_REPO_URL"
    echo "   Target: $PROJECT_DIR"
    if ! git clone "$GIT_REPO_URL" "$PROJECT_DIR"; then
        echo "❌ Error: Failed to clone repository"
        echo "   Please check:"
        echo "   1. GIT_REPO_URL is correct: $GIT_REPO_URL"
        echo "   2. Repository is accessible (public or you have access)"
        echo "   3. Git is installed: $(which git)"
        exit 1
    fi
    cd "$PROJECT_DIR"
fi

# Verify clone was successful
if [ ! -f "pyproject.toml" ] && [ ! -f "src/post_workflow.py" ]; then
    echo "❌ Error: Repository cloned but expected files not found"
    echo "   Directory contents:"
    ls -la "$PROJECT_DIR" | head -20
    exit 1
fi

echo "✅ Repository cloned/updated successfully"

# Install Python dependencies using uv
echo "📦 Installing Python dependencies..."
# Ensure uv is in PATH
if [ -f "$HOME/.local/bin/uv" ]; then
    export PATH="$HOME/.local/bin:$PATH"
    uv sync
elif [ -f "$HOME/.cargo/bin/uv" ]; then
    export PATH="$HOME/.cargo/bin:$PATH"
    uv sync
else
    echo "❌ Error: uv not found. Please run setup_environment.sh first"
    exit 1
fi

echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Copy your configuration files to $PROJECT_DIR/.config/"
echo "2. Run: bash deploy/setup_systemd.sh"
echo "3. Start the service: sudo systemctl start post-generation"
