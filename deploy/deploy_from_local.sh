#!/bin/bash
# Local deployment helper script
# This script runs on your local machine to deploy to GCP VM

set -e  # Exit on error

# Configuration
VM_NAME="${VM_NAME:-sundai-vm}"
VM_ZONE="${VM_ZONE:-asia-southeast1-a}"
GCP_PROJECT="${GCP_PROJECT:-alien-hour-485119-k1}"
GIT_REPO_URL="${GIT_REPO_URL:-}"  # Set this or it will try to detect from git remote

echo "🚀 Deploying Post Generation to GCP VM..."
echo "   VM: $VM_NAME"
echo "   Zone: $VM_ZONE"
echo "   Project: $GCP_PROJECT"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "   Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set GCP project
echo "📌 Setting GCP project..."
gcloud config set project "$GCP_PROJECT"

# Detect Git repository URL if not set
if [ -z "$GIT_REPO_URL" ]; then
    if [ -d ".git" ]; then
        GIT_REPO_URL=$(git remote get-url origin 2>/dev/null || echo "")
        if [ -z "$GIT_REPO_URL" ]; then
            echo "❌ Error: Could not detect Git repository URL"
            echo "   Please set GIT_REPO_URL environment variable:"
            echo "   export GIT_REPO_URL='https://github.com/yourusername/post_generation.git'"
            exit 1
        fi
        echo "📦 Detected Git repository: $GIT_REPO_URL"
    else
        echo "❌ Error: GIT_REPO_URL not set and not in a git repository"
        echo "   Please set GIT_REPO_URL environment variable"
        exit 1
    fi
fi

# Upload deployment scripts to VM
echo "📤 Uploading deployment scripts to VM..."
gcloud compute scp --zone="$VM_ZONE" \
    deploy/setup_environment.sh \
    deploy/deploy.sh \
    deploy/setup_systemd.sh \
    deploy/config_template.sh \
    deploy/post-generation.service \
    "$VM_NAME":~/deploy_scripts/ || {
    echo "Creating deploy_scripts directory on VM..."
    gcloud compute ssh "$VM_NAME" --zone="$VM_ZONE" --command="mkdir -p ~/deploy_scripts"
    gcloud compute scp --zone="$VM_ZONE" \
        deploy/setup_environment.sh \
        deploy/deploy.sh \
        deploy/setup_systemd.sh \
        deploy/config_template.sh \
        deploy/post-generation.service \
        "$VM_NAME":~/deploy_scripts/
}

# Make scripts executable
echo "🔧 Making scripts executable on VM..."
gcloud compute ssh "$VM_NAME" --zone="$VM_ZONE" --command="chmod +x ~/deploy_scripts/*.sh"

# Run setup_environment.sh
echo "🔧 Running environment setup on VM..."
gcloud compute ssh "$VM_NAME" --zone="$VM_ZONE" --command="
    export PATH=\"\$HOME/.cargo/bin:\$PATH\"
    bash ~/deploy_scripts/setup_environment.sh
"

# Run deploy.sh with GIT_REPO_URL
echo "📥 Running deployment script on VM..."
gcloud compute ssh "$VM_NAME" --zone="$VM_ZONE" --command="
    export GIT_REPO_URL='$GIT_REPO_URL'
    export PATH=\"\$HOME/.cargo/bin:\$PATH\"
    bash ~/deploy_scripts/deploy.sh
"

# Copy deployment scripts to project directory
echo "📋 Copying deployment scripts to project directory..."
gcloud compute ssh "$VM_NAME" --zone="$VM_ZONE" --command="
    cp -r ~/deploy_scripts/* ~/post_generation/deploy/ 2>/dev/null || true
"

# Run config_template.sh
echo "📝 Generating configuration templates..."
gcloud compute ssh "$VM_NAME" --zone="$VM_ZONE" --command="
    cd ~/post_generation
    bash deploy/config_template.sh
"

# Setup systemd service
echo "⚙️  Setting up systemd service..."
gcloud compute ssh "$VM_NAME" --zone="$VM_ZONE" --command="
    cd ~/post_generation
    bash deploy/setup_systemd.sh
"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "⚠️  Important next steps:"
echo "1. Upload your configuration files to the VM:"
echo "   gcloud compute scp --zone=$VM_ZONE .config/* $VM_NAME:~/post_generation/.config/"
echo ""
echo "2. Start the service:"
echo "   gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command='sudo systemctl start post-generation'"
echo ""
echo "3. Check service status:"
echo "   gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command='sudo systemctl status post-generation'"
echo ""
echo "4. View logs:"
echo "   gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command='sudo journalctl -u post-generation -f'"
