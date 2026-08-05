# Sync NassilaT pieces to/from Vast for S15 dual-branch contrastive audit.
#
# Usage:
#   .\scripts\vast_s15_contrastive_sync.ps1 -SshHost ssh.vast.ai -SshPort 12345 -Direction up
#   .\scripts\vast_s15_contrastive_sync.ps1 -SshHost ssh.vast.ai -SshPort 12345 -Direction down
#
param(
    [Parameter(Mandatory = $true)]
    [string]$SshHost,

    [Parameter(Mandatory = $true)]
    [int]$SshPort,

    [ValidateSet("up", "down")]
    [string]$Direction = "up",

    [string]$RemotePath = "/workspace/nassila-s15/training",
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
    Write-Host "Uploading S15 eval kit -> ${sshTarget}:${RemotePath}"
    Fix-LineEndings (Join-Path $LocalPath "scripts")
    ssh -p $SshPort $sshTarget "mkdir -p $RemotePath/data $RemotePath/outputs $RemotePath/reports $RemotePath/scripts"
    scp -P $SshPort `
        "$LocalPath\scripts\run_l3_eval_batch.py" `
        "$LocalPath\scripts\evaluate_outputs.py" `
        "$LocalPath\scripts\json_repair.py" `
        "$LocalPath\scripts\lmstudio_smoke_test.py" `
        "$LocalPath\scripts\validate_dataset.py" `
        "$LocalPath\scripts\corpus_utils.py" `
        "$LocalPath\scripts\run_s15_contrastive_vast.sh" `
        "${sshTarget}:${RemotePath}/scripts/"
    scp -P $SshPort `
        "$LocalPath\data\eval_holdout_body_contrastive_frozen_v2.jsonl" `
        "${sshTarget}:${RemotePath}/data/"
    if (Test-Path "$LocalPath\requirements.txt") {
        scp -P $SshPort "$LocalPath\requirements.txt" "${sshTarget}:${RemotePath}/"
    }
    Write-Host "Done. SSH in and run:"
    Write-Host "  cd $RemotePath && bash scripts/run_s15_contrastive_vast.sh"
} else {
    $localReports = Join-Path $LocalPath "reports"
    New-Item -ItemType Directory -Force -Path $localReports | Out-Null
    Write-Host "Downloading S15 dual-branch artifacts from ${sshTarget}:${RemotePath}"
    scp -P $SshPort `
        "${sshTarget}:${RemotePath}/reports/s15_contrastive_v2_vast_fast_predictions.jsonl" `
        "${sshTarget}:${RemotePath}/reports/s15_contrastive_v2_vast_fast_eval.json" `
        "${sshTarget}:${RemotePath}/reports/s15_contrastive_v2_vast_claim_predictions.jsonl" `
        "${sshTarget}:${RemotePath}/reports/s15_contrastive_v2_vast_claim_eval.json" `
        $localReports
    Write-Host "Done. Destroy the Vast instance when satisfied."
}
