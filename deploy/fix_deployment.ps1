# Quick fix script to manually clone the repository on VM

$ErrorActionPreference = "Stop"

$VM_NAME = if ($env:VM_NAME) { $env:VM_NAME } else { "sundai-vm" }
$VM_ZONE = if ($env:VM_ZONE) { $env:VM_ZONE } else { "asia-southeast1-a" }
$GIT_REPO_URL = $env:GIT_REPO_URL

if (-not $GIT_REPO_URL) {
    Write-Host "❌ GIT_REPO_URL is not set!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please set it first:" -ForegroundColor Yellow
    Write-Host "   `$env:GIT_REPO_URL = 'https://github.com/He-Wenhao/post_generation.git'" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Or provide it now:" -ForegroundColor Yellow
    $GIT_REPO_URL = Read-Host "Enter Git repository URL"
    
    if (-not $GIT_REPO_URL) {
        Write-Host "❌ No URL provided. Exiting." -ForegroundColor Red
        exit 1
    }
}

Write-Host "🔧 Fixing deployment..." -ForegroundColor Cyan
Write-Host "   Repository: $GIT_REPO_URL" -ForegroundColor Gray
Write-Host ""

# Remove empty directory and clone fresh
Write-Host "1. Removing empty post_generation directory..." -ForegroundColor Yellow
gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="rm -rf ~/post_generation"

Write-Host "2. Cloning repository..." -ForegroundColor Yellow
$escapedRepoUrl = $GIT_REPO_URL.Replace("'", "'\''")
$cloneCmd = "export PATH=`$HOME/.cargo/bin:`$PATH; cd ~; echo 'Cloning repository...'; git clone '$escapedRepoUrl' ~/post_generation; cd ~/post_generation; echo 'Repository contents:'; ls -la | head -15"

$cloneOutput = gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command=$cloneCmd 2>&1
Write-Host $cloneOutput

Write-Host ""
Write-Host "3. Installing dependencies..." -ForegroundColor Yellow
$installCmd = "export PATH=`$HOME/.cargo/bin:`$PATH; cd ~/post_generation; uv sync"

$installOutput = gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command=$installCmd 2>&1
Write-Host $installOutput

Write-Host ""
Write-Host "4. Verifying deployment..." -ForegroundColor Yellow
$verifyCmd = "cd ~/post_generation; if [ -f pyproject.toml ] && [ -f src/post_workflow.py ]; then echo 'SUCCESS'; echo 'Files found:'; ls -la src/ | head -10; else echo 'FAILED'; ls -la; fi"

$verifyOutput = gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command=$verifyCmd 2>&1
Write-Host $verifyOutput

Write-Host ""
Write-Host "✅ Fix complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Upload configuration files" -ForegroundColor Cyan
Write-Host "2. Run: gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command='cd ~/post_generation && bash deploy/setup_systemd.sh'" -ForegroundColor Cyan
Write-Host "3. Start service: gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command='sudo systemctl start post-generation'" -ForegroundColor Cyan
