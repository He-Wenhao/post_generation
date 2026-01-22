#!/bin/bash
# Setup environment for Post Generation project on GCP VM

set -e  # Exit on error

echo "🔧 Setting up environment for Post Generation..."

# Detect user and home directory
if [ -z "$USER" ]; then
    USER=$(whoami)
fi
HOME_DIR=$(eval echo ~$USER)
PROJECT_DIR="$HOME_DIR/post_generation"

echo "📦 Installing system dependencies..."

# Update package list
sudo apt-get update -qq

# Install Python 3.8+ and pip
if ! command -v python3 &> /dev/null; then
    echo "Installing Python 3..."
    sudo apt-get install -y python3 python3-pip python3-venv
fi

# Install git if not present
if ! command -v git &> /dev/null; then
    echo "Installing Git..."
    sudo apt-get install -y git
fi

# Install curl for downloading uv
if ! command -v curl &> /dev/null; then
    echo "Installing curl..."
    sudo apt-get install -y curl
fi

# Install uv (Python package manager)
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    # Add to bashrc for persistence
    if ! grep -q 'export PATH="$HOME/.cargo/bin:$PATH"' ~/.bashrc; then
        echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
    fi
else
    echo "✓ uv is already installed"
fi

# Ensure uv is in PATH for current session
export PATH="$HOME/.cargo/bin:$PATH"

# Create log directory
echo "📁 Creating log directory..."
sudo mkdir -p /var/log/post-generation
sudo chown $USER:$USER /var/log/post-generation

echo "✅ Environment setup complete!"
echo ""
echo "Installed versions:"
python3 --version
git --version
uv --version || echo "uv version check (may need to reload shell)"
