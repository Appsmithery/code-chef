param(
    [string]$Version = "latest"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repo = "digitalocean/doctl"
$apiBase = "https://api.github.com/repos/$repo/releases"
$releaseUri = if ($Version -eq "latest") {
    "$apiBase/latest"
} else {
    "$apiBase/tags/$Version"
}

Write-Host "Fetching doctl release metadata from $releaseUri ..."
$release = Invoke-RestMethod -Uri $releaseUri

$asset = $release.assets | Where-Object { $_.name -match "windows-amd64\.zip$" } | Select-Object -First 1
if (-not $asset) {
    throw "Unable to locate a Windows AMD64 zip asset in release '$($release.tag_name)'."
}

$targetDir = Join-Path -Path (Resolve-Path "$PSScriptRoot/..") -ChildPath ".bin/doctl"
if (-not (Test-Path $targetDir)) {
    Write-Host "Creating target directory $targetDir"
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
}

$tempZip = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "doctl-$([System.Guid]::NewGuid()).zip")
$tempExtract = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "doctl-$([System.Guid]::NewGuid())")

Write-Host "Downloading $($asset.name) ..."
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $tempZip

Write-Host "Extracting archive ..."
Expand-Archive -Path $tempZip -DestinationPath $tempExtract -Force

$doctlExe = Get-ChildItem -Path $tempExtract -Filter "doctl.exe" -Recurse | Select-Object -First 1
if (-not $doctlExe) {
    throw "doctl.exe not found inside $tempExtract"
}

$destinationExe = Join-Path $targetDir "doctl.exe"
Copy-Item -Path $doctlExe.FullName -Destination $destinationExe -Force

Remove-Item $tempZip -Force
Remove-Item $tempExtract -Force -Recurse

if (-not ($env:PATH -split ';' | Where-Object { $_ -ieq $targetDir })) {
    $env:PATH = "$targetDir;$env:PATH"
}

Write-Host "Installed doctl $($release.tag_name) to $destinationExe"
Write-Host "Current session PATH updated. Run 'doctl version' to verify installation."
