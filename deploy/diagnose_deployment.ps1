# Diagnostic script to check deployment status on VM

$ErrorActionPreference = "Stop"

$VM_NAME = if ($env:VM_NAME) { $env:VM_NAME } else { "sundai-vm" }
$VM_ZONE = if ($env:VM_ZONE) { $env:VM_ZONE } else { "asia-southeast1-a" }

Write-Host "🔍 Diagnosing deployment on VM..." -ForegroundColor Cyan
Write-Host ""

# Check if post_generation directory exists
Write-Host "1. Checking if post_generation directory exists..." -ForegroundColor Yellow
$checkDir = gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="if [ -d ~/post_generation ]; then echo 'EXISTS'; ls -la ~/post_generation | head -10; else echo 'NOT_EXISTS'; fi" 2>&1
Write-Host $checkDir

Write-Host ""
Write-Host "2. Checking Git repository status..." -ForegroundColor Yellow
$gitStatus = gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="cd ~/post_generation 2>/dev/null && git remote -v 2>&1 || echo 'Not a git repository or directory does not exist'" 2>&1
Write-Host $gitStatus

Write-Host ""
Write-Host "3. Checking if uv is installed..." -ForegroundColor Yellow
$uvCheck = gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="export PATH=\"\$HOME/.cargo/bin:\$PATH\"; which uv || echo 'uv not found'; uv --version 2>&1 || echo 'uv not working'" 2>&1
Write-Host $uvCheck

Write-Host ""
Write-Host "4. Checking deploy_scripts directory..." -ForegroundColor Yellow
$deployScripts = gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="ls -la ~/deploy_scripts 2>&1 || echo 'deploy_scripts directory does not exist'" 2>&1
Write-Host $deployScripts

Write-Host ""
Write-Host "5. Checking recent command history (last 20 lines)..." -ForegroundColor Yellow
$history = gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="tail -20 ~/.bash_history 2>&1 || echo 'No history found'" 2>&1
Write-Host $history
