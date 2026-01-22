# PowerShell deployment script for Post Generation to GCP VM
# This script runs on your local Windows machine to deploy to GCP VM

$ErrorActionPreference = "Stop"

# Configuration
$VM_NAME = if ($env:VM_NAME) { $env:VM_NAME } else { "sundai-vm" }
$VM_ZONE = if ($env:VM_ZONE) { $env:VM_ZONE } else { "asia-southeast1-a" }
$GCP_PROJECT = if ($env:GCP_PROJECT) { $env:GCP_PROJECT } else { "alien-hour-485119-k1" }
$GIT_REPO_URL = $env:GIT_REPO_URL

Write-Host "🚀 Deploying Post Generation to GCP VM..." -ForegroundColor Cyan
Write-Host "   VM: $VM_NAME"
Write-Host "   Zone: $VM_ZONE"
Write-Host "   Project: $GCP_PROJECT"
Write-Host ""

# Check if gcloud is installed
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Error: gcloud CLI is not installed" -ForegroundColor Red
    Write-Host "   Install it from: https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
    exit 1
}

# Set GCP project
Write-Host "📌 Setting GCP project..." -ForegroundColor Cyan
gcloud config set project $GCP_PROJECT

# Detect Git repository URL if not set
if (-not $GIT_REPO_URL) {
    if (Test-Path ".git") {
        $GIT_REPO_URL = git remote get-url origin 2>$null
        if (-not $GIT_REPO_URL) {
            Write-Host "❌ Error: Could not detect Git repository URL" -ForegroundColor Red
            Write-Host "   Please set GIT_REPO_URL environment variable:" -ForegroundColor Yellow
            Write-Host "   `$env:GIT_REPO_URL='https://github.com/yourusername/post_generation.git'" -ForegroundColor Yellow
            exit 1
        }
        Write-Host "📦 Detected Git repository: $GIT_REPO_URL" -ForegroundColor Green
    } else {
        Write-Host "❌ Error: GIT_REPO_URL not set and not in a git repository" -ForegroundColor Red
        Write-Host "   Please set GIT_REPO_URL environment variable" -ForegroundColor Yellow
        exit 1
    }
}

# Upload deployment scripts to VM
Write-Host "📤 Uploading deployment scripts to VM..." -ForegroundColor Cyan
$deployScripts = @(
    "deploy/setup_environment.sh",
    "deploy/deploy.sh",
    "deploy/setup_systemd.sh",
    "deploy/config_template.sh",
    "deploy/post-generation.service"
)

try {
    gcloud compute scp --zone=$VM_ZONE $deployScripts "$VM_NAME`:~/deploy_scripts/" 2>&1 | Out-Null
} catch {
    Write-Host "Creating deploy_scripts directory on VM..." -ForegroundColor Yellow
    gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="mkdir -p ~/deploy_scripts"
    gcloud compute scp --zone=$VM_ZONE $deployScripts "$VM_NAME`:~/deploy_scripts/"
}

# Make scripts executable
Write-Host "🔧 Making scripts executable on VM..." -ForegroundColor Cyan
gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="chmod +x ~/deploy_scripts/*.sh"

# Run setup_environment.sh
Write-Host "🔧 Running environment setup on VM..." -ForegroundColor Cyan
$envSetupCmd = "bash ~/deploy_scripts/setup_environment.sh 2>&1"
gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command=$envSetupCmd

# Run deploy.sh with GIT_REPO_URL
Write-Host "📥 Running deployment script on VM..." -ForegroundColor Cyan
Write-Host "   Git Repository: $GIT_REPO_URL" -ForegroundColor Gray

# Escape single quotes in GIT_REPO_URL for bash
$escapedRepoUrl = $GIT_REPO_URL.Replace("'", "'\''")

$deployCmd = "export GIT_REPO_URL='$escapedRepoUrl'; if [ -f `$HOME/.local/bin/uv ]; then export PATH=`$HOME/.local/bin:`$PATH; elif [ -f `$HOME/.cargo/bin/uv ]; then export PATH=`$HOME/.cargo/bin:`$PATH; fi; echo 'Starting deployment with GIT_REPO_URL: '`$GIT_REPO_URL; bash ~/deploy_scripts/deploy.sh 2>&1"

$deployOutput = gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command=$deployCmd 2>&1
Write-Host $deployOutput

# Check if deployment was successful
$checkDeploy = gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="if [ -f ~/post_generation/pyproject.toml ] || [ -f ~/post_generation/src/post_workflow.py ]; then echo 'SUCCESS'; else echo 'FAILED - Directory is empty or missing files'; ls -la ~/post_generation 2>&1 | head -10; fi" 2>&1
Write-Host ""
if ($checkDeploy -match "SUCCESS") {
    Write-Host "✅ Deployment verified: Files found in post_generation directory" -ForegroundColor Green
} else {
    Write-Host "❌ Deployment may have failed. Checking..." -ForegroundColor Red
    Write-Host $checkDeploy
    Write-Host ""
    Write-Host "Please run the diagnostic script:" -ForegroundColor Yellow
    Write-Host "   .\deploy\diagnose_deployment.ps1" -ForegroundColor Cyan
    exit 1
}

# Copy deployment scripts to project directory
Write-Host "📋 Copying deployment scripts to project directory..." -ForegroundColor Cyan
gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="cp -r ~/deploy_scripts/* ~/post_generation/deploy/ 2>/dev/null || true"

# Run config_template.sh
Write-Host "📝 Generating configuration templates..." -ForegroundColor Cyan
gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="cd ~/post_generation && bash deploy/config_template.sh"

# Setup systemd service
Write-Host "⚙️  Setting up systemd service..." -ForegroundColor Cyan
gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="cd ~/post_generation && bash deploy/setup_systemd.sh"

Write-Host ""
Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "⚠️  Important next steps:" -ForegroundColor Yellow
Write-Host "1. Upload your configuration files to the VM:" -ForegroundColor Yellow
Write-Host "   Get-ChildItem .config\*.json -Exclude *.example | ForEach-Object {" -ForegroundColor Cyan
Write-Host "     `$targetPath = `/home/hewenhao/post_generation/.config/`$(`$_.Name)" -ForegroundColor Cyan
Write-Host "     gcloud compute scp --zone=$VM_ZONE `$_.FullName `"$VM_NAME`:`$targetPath`"" -ForegroundColor Cyan
Write-Host "   }" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Or use absolute path:" -ForegroundColor Gray
Write-Host "   gcloud compute scp --zone=$VM_ZONE .config\notion_config.json $VM_NAME`:/home/hewenhao/post_generation/.config/" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Start the service:"
Write-Host "   gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command='sudo systemctl start post-generation'" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Check service status:"
Write-Host "   gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command='sudo systemctl status post-generation'" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. View logs:"
Write-Host "   gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command='sudo journalctl -u post-generation -f'" -ForegroundColor Cyan
