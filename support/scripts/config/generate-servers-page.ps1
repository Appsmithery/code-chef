# Generate servers.html from actual MCP server definitions on droplet

$ErrorActionPreference = "Continue"
$DROPLET = "do-codechef-droplet"  # SSH config alias for root@45.55.173.72

Write-Host "Fetching server list from droplet ($DROPLET)..."
$serverDirs = ssh $DROPLET "ls -1 /opt/central-mcp-gateway/servers/ | grep -v -E '(README|client|index)'" | Where-Object { $_ -and $_.Trim() }

Write-Host "Found $($serverDirs.Count) server directories"

$servers = @()

foreach ($dir in $serverDirs) {
    $dir = $dir.Trim()
    Write-Host "Processing: $dir"
    
    # Read index.ts to get SERVER_INFO
    $indexPath = "/opt/central-mcp-gateway/servers/$dir/index.ts"
    $indexContent = ssh $DROPLET "cat $indexPath 2>/dev/null" | Out-String
    
    # Extract SERVER_INFO block
    if ($indexContent -match "SERVER_INFO\s*=\s*\{([^\}]+)\}") {
        $serverBlock = $matches[1]
        
        # Parse name
        $name = ""
        if ($serverBlock -match "name:\s*'([^']+)'") {
            $name = $matches[1]
        }
        
        # Parse toolCount  
        $toolCount = 0
        if ($serverBlock -match "toolCount:\s*(\d+)") {
            $toolCount = [int]$matches[1]
        }
        
        Write-Host "  - Name: $name, Tools: $toolCount"
        
        $servers += @{
            name = $name
            displayName = $name.ToUpper()[0] + $name.Substring(1) -replace "-", " " -replace "_", " "
            toolCount = $toolCount
            icon = "tool"
            category = "MCP Server"
            protocol = "MCP 1.0"
        }
    }
    else {
        Write-Host "  - No SERVER_INFO found" -ForegroundColor Yellow
    }
}

Write-Host "`nFound $($servers.Count) servers"
$servers | ConvertTo-Json -Depth 5 | Out-File "d:\INFRA\Dev-Tools\Dev-Tools\context\mcp-server-data.json" -Encoding utf8
Write-Host "Saved to context/mcp-server-data.json"
$servers | Format-Table name, toolCount
