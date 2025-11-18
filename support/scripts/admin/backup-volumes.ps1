#!/usr/bin/env pwsh
# Backup droplet volumes to local machine
param(
    [string]$DropletIP = "45.55.173.72",
    [string]$DropletPath = "/opt/Dev-Tools"
)

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backup_dir = "./backups/$timestamp"

New-Item -ItemType Directory -Force -Path $backup_dir | Out-Null

Write-Host "[BACKUP] Backing up droplet volumes to $backup_dir..."

# Run backup script on droplet
ssh root@$DropletIP "cd $DropletPath && ./support/scripts/data/backup_volumes.sh"

# Download backup files
scp "root@${DropletIP}:${DropletPath}/backups/latest/*.tar.gz" $backup_dir/

Write-Host "[SUCCESS] Backup complete: $backup_dir"
