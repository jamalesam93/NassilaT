# Sync NassilaT training/ to/from a Vast instance for the Nanbeige probe.
#
# Usage:
#   .\scripts\vast_nanbeige_sync.ps1 -SshHost ssh.vast.ai -SshPort 12345 -Direction up
#   .\scripts\vast_nanbeige_sync.ps1 -SshHost ssh.vast.ai -SshPort 12345 -Direction down
#
param(
    [Parameter(Mandatory = $true)]
    [string]$SshHost,

    [Parameter(Mandatory = $true)]
    [int]$SshPort,

    [ValidateSet("up", "down")]
    [string]$Direction = "up",

    [string]$RemotePath = "/workspace/nassila-probe/training",
    [string]$LocalPath = (Split-Path $PSScriptRoot -Parent)
)

$ErrorActionPreference = "Stop"
$sshTarget = "root@$SshHost"

function Fix-LineEndings {
    param([string]$Dir)
    Get-ChildItem -Path $Dir -Recurse -Include *.sh,*.py | ForEach-Object {
        $c = [IO.File]::ReadAllText($_.FullName) -replace "`r`n", "`n"
        [IO.File]::WriteAllText($_.FullName, $c)
    }
}

if ($Direction -eq "up") {
    Write-Host "Uploading $LocalPath -> ${sshTarget}:${RemotePath}"
    Fix-LineEndings (Join-Path $LocalPath "scripts")
    ssh -p $SshPort $sshTarget "mkdir -p $RemotePath/data $RemotePath/outputs $RemotePath/reports"
    scp -P $SshPort -r "$LocalPath\scripts" "${sshTarget}:${RemotePath}/"
    scp -P $SshPort "$LocalPath\requirements.txt" "${sshTarget}:${RemotePath}/"
    scp -P $SshPort "$LocalPath\data\eval_samples.jsonl" "$LocalPath\data\eval_holdout_90.jsonl" "$LocalPath\data\eval_samples_extended.jsonl" "${sshTarget}:${RemotePath}/data/"
    Write-Host "Done. SSH in and run:"
    Write-Host "  cd $RemotePath && bash scripts/run_nanbeige_llamacpp_vast_probe.sh"
} else {
    $localOut = Join-Path $LocalPath "outputs"
    $localReports = Join-Path $LocalPath "reports"
    New-Item -ItemType Directory -Force -Path $localOut, $localReports | Out-Null
    Write-Host "Downloading probe artifacts from ${sshTarget}:${RemotePath}"
    scp -P $SshPort "${sshTarget}:${RemotePath}/outputs/nanbeige_zeroshot_*" $localOut
    scp -P $SshPort "${sshTarget}:${RemotePath}/reports/nanbeige_zeroshot_probe_2026-07.md" $localReports
    Write-Host "Done. Destroy the Vast instance when satisfied."
}
