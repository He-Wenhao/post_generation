#!/bin/bash
# Setup systemd service for Post Generation

set -e  # Exit on error

# Detect user and home directory
if [ -z "$USER" ]; then
    USER=$(whoami)
fi
HOME_DIR=$(eval echo ~$USER)
PROJECT_DIR="$HOME_DIR/post_generation"
SERVICE_FILE="post-generation.service"
DEPLOY_DIR="$PROJECT_DIR/deploy"

echo "⚙️  Setting up systemd service for Post Generation..."

# Check if project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Error: Project directory not found: $PROJECT_DIR"
    echo "   Please run deploy.sh first to clone the repository"
    exit 1
fi

# Check if service file exists
if [ ! -f "$DEPLOY_DIR/$SERVICE_FILE" ]; then
    echo "❌ Error: Service file not found: $DEPLOY_DIR/$SERVICE_FILE"
    exit 1
fi

# Determine uv path (check both common locations)
UV_PATH=""
if [ -f "$HOME_DIR/.local/bin/uv" ]; then
    UV_PATH="$HOME_DIR/.local/bin/uv"
elif [ -f "$HOME_DIR/.cargo/bin/uv" ]; then
    UV_PATH="$HOME_DIR/.cargo/bin/uv"
else
    echo "⚠️  Warning: uv not found in common locations, using ~/.local/bin/uv as default"
    UV_PATH="$HOME_DIR/.local/bin/uv"
fi

# Create systemd service file with user and home directory substituted
echo "📝 Creating systemd service file..."
echo "   Using uv at: $UV_PATH"
sudo tee /etc/systemd/system/post-generation.service > /dev/null <<EOF
[Unit]
Description=Post Generation Telegram Bot Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$HOME_DIR/.local/bin:$HOME_DIR/.cargo/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$UV_PATH run python src/post_workflow.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/post-generation/service.log
StandardError=append:/var/log/post-generation/error.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service to start on boot
echo "🔌 Enabling service to start on boot..."
sudo systemctl enable post-generation.service

echo "✅ Systemd service setup complete!"
echo ""
echo "Service management commands:"
echo "  Start:   sudo systemctl start post-generation"
echo "  Stop:    sudo systemctl stop post-generation"
echo "  Restart: sudo systemctl restart post-generation"
echo "  Status:  sudo systemctl status post-generation"
echo "  Logs:    sudo journalctl -u post-generation -f"
echo ""
echo "⚠️  Note: Make sure your configuration files are set up in $PROJECT_DIR/.config/ before starting the service"
