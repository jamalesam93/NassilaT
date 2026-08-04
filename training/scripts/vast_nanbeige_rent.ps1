# Search Vast offers and print rent instructions for the Nanbeige probe.
#
# Requires: vastai CLI (pip install vastai) + vastai login
#
# Usage:
#   .\scripts\vast_nanbeige_rent.ps1
#   .\scripts\vast_nanbeige_rent.ps1 -OfferId 45767485
#
param(
    [int]$OfferId = 0,
    [int]$MinGpuRamGb = 22,
    [int]$MinDiskGb = 50
)

$ErrorActionPreference = "Stop"

Write-Host "=== Nanbeige Vast probe — instance search (llama.cpp path) ===" -ForegroundColor Cyan
Write-Host "Filter: GPU RAM >= ${MinGpuRamGb} GB, disk >= ${MinDiskGb} GB — prefer RTX 4090"
Write-Host ""

$query = "gpu_ram>=$MinGpuRamGb num_gpus=1 disk_space>=$MinDiskGb rented=False"
vastai search offers $query

if ($OfferId -gt 0) {
    Write-Host ""
    Write-Host "To rent offer $OfferId (after vastai login):" -ForegroundColor Yellow
    Write-Host "  vastai create instance $OfferId --image ubuntu:22.04 --disk 60"
    Write-Host ""
    Write-Host "Then sync and run:" -ForegroundColor Yellow
    Write-Host "  .\scripts\vast_nanbeige_sync.ps1 -SshHost <host> -SshPort <port> -Direction up"
    Write-Host "  ssh -p <port> root@<host> 'cd /workspace/nassila-probe/training && bash scripts/run_nanbeige_llamacpp_vast_probe.sh'"
} else {
    Write-Host ""
    Write-Host "Pick an offer ID (RTX 4090 24GB preferred; L4/A10 also OK)." -ForegroundColor Yellow
    Write-Host "Re-run: .\scripts\vast_nanbeige_rent.ps1 -OfferId <id>"
    Write-Host ""
    Write-Host "Login first if needed: vastai login"
}

Write-Host ""
Write-Host "Full walkthrough: training/NANBEIGE_VAST_PROBE.md"
