# Deployment Scripts

This directory contains scripts for deploying the Post Generation project to a GCP VM instance.

## Scripts Overview

### `deploy_from_local.sh` / `deploy_from_local.ps1` (Recommended)
**Run this from your local machine** to deploy to the VM automatically.

This script:
- Uploads all deployment scripts to the VM
- Runs environment setup
- Clones/updates the repository
- Installs dependencies
- Sets up systemd service
- Generates configuration templates

**Usage (Linux/macOS):**
```bash
export GIT_REPO_URL="https://github.com/yourusername/post_generation.git"
bash deploy/deploy_from_local.sh
```

**Usage (Windows PowerShell):**
```powershell
$env:GIT_REPO_URL = "https://github.com/yourusername/post_generation.git"
.\deploy\deploy_from_local.ps1
```

### `setup_environment.sh`
Installs system dependencies on the VM:
- Python 3.8+
- Git
- uv (Python package manager)
- Creates log directories

**Run on VM:**
```bash
bash deploy/setup_environment.sh
```

### `deploy.sh`
Clones or updates the Git repository and installs Python dependencies.

**Run on VM:**
```bash
export GIT_REPO_URL="https://github.com/yourusername/post_generation.git"
bash deploy/deploy.sh
```

### `config_template.sh`
Generates configuration file templates from `.example` files.

**Run on VM:**
```bash
bash deploy/config_template.sh
```

### `setup_systemd.sh`
Sets up the systemd service for long-running Telegram bot.

**Run on VM:**
```bash
bash deploy/setup_systemd.sh
```

### `post-generation.service`
Systemd service file template. This is automatically installed by `setup_systemd.sh`.

## Deployment Workflow

### Automated (Recommended)
1. From your local machine, run:
   - **Linux/macOS:** `bash deploy/deploy_from_local.sh`
   - **Windows:** `.\deploy\deploy_from_local.ps1`
2. Upload your configuration files:
   - **Windows PowerShell:**
     ```powershell
     Get-ChildItem .config\*.json -Exclude *.example | ForEach-Object {
         $targetPath = "/home/hewenhao/post_generation/.config/$($_.Name)"
         gcloud compute scp --zone=asia-southeast1-a $_.FullName "sundai-vm:$targetPath"
     }
     ```
   - **Linux/macOS:**
     ```bash
     gcloud compute scp --zone=asia-southeast1-a .config/* sundai-vm:/home/hewenhao/post_generation/.config/
     ```
3. Start the service:
   ```bash
   gcloud compute ssh sundai-vm --zone=asia-southeast1-a --command="sudo systemctl start post-generation"
   ```

### Manual
1. SSH into VM: `gcloud compute ssh sundai-vm --zone=asia-southeast1-a`
2. Run scripts in order:
   - `bash deploy/setup_environment.sh`
   - `bash deploy/deploy.sh` (set GIT_REPO_URL first)
   - `bash deploy/config_template.sh`
   - Edit configuration files
   - `bash deploy/setup_systemd.sh`
   - `sudo systemctl start post-generation`

## Service Management

```bash
# Start
sudo systemctl start post-generation

# Stop
sudo systemctl stop post-generation

# Restart
sudo systemctl restart post-generation

# Status
sudo systemctl status post-generation

# Logs
sudo journalctl -u post-generation -f
```

## Configuration

After deployment, upload your configuration files to the VM:

**Windows PowerShell:**
```powershell
Get-ChildItem .config\*.json -Exclude *.example | ForEach-Object {
    $targetPath = "/home/hewenhao/post_generation/.config/$($_.Name)"
    gcloud compute scp --zone=asia-southeast1-a $_.FullName "sundai-vm:$targetPath"
}
```

**Linux/macOS:**
```bash
gcloud compute scp --zone=asia-southeast1-a .config/* sundai-vm:/home/hewenhao/post_generation/.config/
```

Or edit these files directly on the VM:
- `~/post_generation/.config/notion_config.json`
- `~/post_generation/.config/openrouter_config.json`
- `~/post_generation/.config/mastodon_config.json`
- `~/post_generation/.config/telegram_config.json`
- `~/post_generation/.config/workflow_config.json`

Make sure to set `"telegram_trigger": "post_mastodon"` (or your trigger message) in `workflow_config.json` for Telegram-triggered mode.
