# Sync NassilaT training pieces to/from Vast for S14 contrastive eval.
#
# Usage:
#   .\scripts\vast_s14_contrastive_sync.ps1 -SshHost ssh.vast.ai -SshPort 12345 -Direction up
#   .\scripts\vast_s14_contrastive_sync.ps1 -SshHost ssh.vast.ai -SshPort 12345 -Direction down
#
param(
    [Parameter(Mandatory = $true)]
    [string]$SshHost,

    [Parameter(Mandatory = $true)]
    [int]$SshPort,

    [ValidateSet("up", "down")]
    [string]$Direction = "up",

    [string]$RemotePath = "/workspace/nassila-s14/training",
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
    Write-Host "Uploading eval kit -> ${sshTarget}:${RemotePath}"
    Fix-LineEndings (Join-Path $LocalPath "scripts")
    ssh -p $SshPort $sshTarget "mkdir -p $RemotePath/data $RemotePath/outputs $RemotePath/reports $RemotePath/scripts"
    scp -P $SshPort `
        "$LocalPath\scripts\run_l3_eval_batch.py" `
        "$LocalPath\scripts\evaluate_outputs.py" `
        "$LocalPath\scripts\json_repair.py" `
        "$LocalPath\scripts\lmstudio_smoke_test.py" `
        "$LocalPath\scripts\validate_dataset.py" `
        "$LocalPath\scripts\corpus_utils.py" `
        "$LocalPath\scripts\run_s14_contrastive_vast.sh" `
        "${sshTarget}:${RemotePath}/scripts/"
    scp -P $SshPort `
        "$LocalPath\data\eval_holdout_body_contrastive_frozen_v2.jsonl" `
        "${sshTarget}:${RemotePath}/data/"
    if (Test-Path "$LocalPath\requirements.txt") {
        scp -P $SshPort "$LocalPath\requirements.txt" "${sshTarget}:${RemotePath}/"
    }
    Write-Host "Done. SSH in and run:"
    Write-Host "  cd $RemotePath && bash scripts/run_s14_contrastive_vast.sh"
} else {
    $localReports = Join-Path $LocalPath "reports"
    New-Item -ItemType Directory -Force -Path $localReports | Out-Null
    Write-Host "Downloading S14 contrastive artifacts from ${sshTarget}:${RemotePath}"
    scp -P $SshPort `
        "${sshTarget}:${RemotePath}/reports/tier3_body_contrastive_frozen_v2_predictions_s14_vast.jsonl" `
        "${sshTarget}:${RemotePath}/reports/tier3_body_contrastive_frozen_v2_s14_vast_eval.json" `
        $localReports
    Write-Host "Done. Destroy the Vast instance when satisfied."
    Write-Host "Local score (if eval json missing):"
    Write-Host "  python scripts/evaluate_outputs.py --eval data/eval_holdout_body_contrastive_frozen_v2.jsonl --predictions reports/tier3_body_contrastive_frozen_v2_predictions_s14_vast.jsonl --report reports/tier3_body_contrastive_frozen_v2_s14_eval.json --repair"
}
