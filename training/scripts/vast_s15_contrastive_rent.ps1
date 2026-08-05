# Search Vast offers and print rent instructions for S15 dual-branch audit.
#
# Requires: vastai CLI (pip install vastai) + vastai login
#
# Usage:
#   .\scripts\vast_s15_contrastive_rent.ps1
#   .\scripts\vast_s15_contrastive_rent.ps1 -OfferId 12345678
#
param(
    [int]$OfferId = 0,
    [int]$MinGpuRamGb = 22,
    [int]$MinDiskGb = 40
)

$ErrorActionPreference = "Stop"

Write-Host "=== S15 contrastive Vast dual-branch audit — instance search ===" -ForegroundColor Cyan
Write-Host "Filter: GPU RAM >= ${MinGpuRamGb} GB, disk >= ${MinDiskGb} GB — prefer RTX 4090"
Write-Host "Workload: eval_holdout_body_contrastive_frozen_v2.jsonl (308 rows x2 branches)"
Write-Host ""

$query = "gpu_ram>=$MinGpuRamGb num_gpus=1 disk_space>=$MinDiskGb rented=False"
vastai search offers $query

if ($OfferId -gt 0) {
    Write-Host ""
    Write-Host "To rent offer $OfferId (after vastai login):" -ForegroundColor Yellow
    Write-Host "  vastai create instance $OfferId --image ubuntu:22.04 --disk 60 --ssh"
    Write-Host ""
    Write-Host "Then:" -ForegroundColor Yellow
    Write-Host "  vastai show instances"
    Write-Host "  .\scripts\vast_s15_contrastive_sync.ps1 -SshHost <host> -SshPort <port> -Direction up"
    Write-Host "  ssh -p <port> root@<host> 'cd /workspace/nassila-s15/training && bash scripts/run_s15_contrastive_vast.sh'"
} else {
    Write-Host ""
    Write-Host "Pick an offer ID (RTX 4090 24GB preferred)." -ForegroundColor Yellow
    Write-Host "Re-run: .\scripts\vast_s15_contrastive_rent.ps1 -OfferId <id>"
    Write-Host ""
    Write-Host "Login first if needed: vastai login"
}

Write-Host ""
Write-Host "Walkthrough: training/S14_CONTRASTIVE_VAST.md (same pattern, s15 paths)"
