# Laptop smoke test wrapper — one Sanad GGUF via LM Studio.
# Usage:
#   .\scripts\run_laptop_smoke.ps1 -Model "model-id-from-lm-studio" -Arm e4b
#   .\scripts\run_laptop_smoke.ps1 -Model "model-id-from-lm-studio" -Arm 12b

param(
    [Parameter(Mandatory = $true)]
    [string]$Model,

    [Parameter(Mandatory = $true)]
    [ValidateSet("e4b", "12b")]
    [string]$Arm,

    [string]$BaseUrl = "http://localhost:1234"
)

$ErrorActionPreference = "Stop"
$TrainingDir = Split-Path $PSScriptRoot -Parent
Set-Location $TrainingDir

$SmokeIds = @("h-001", "eval-004", "h-045", "h-088")
$PredOut = Join-Path $TrainingDir "outputs\laptop_smoke_$Arm.jsonl"
$ReportOut = Join-Path $TrainingDir "outputs\laptop_smoke_${Arm}_report.json"

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Error "Missing venv. Run: python -m venv .venv; .\.venv\Scripts\activate; pip install -r requirements.txt"
}
$Python = ".\.venv\Scripts\python.exe"

Write-Host "=== Laptop smoke: $Arm ===" -ForegroundColor Cyan
Write-Host "Model: $Model"
Write-Host "Server: $BaseUrl"
Write-Host ""

Write-Host "[1/3] Ping..." -ForegroundColor Yellow
& $Python scripts/lmstudio_smoke_test.py `
    --base-url $BaseUrl `
    --model $Model `
    --task ping
if ($LASTEXITCODE -ne 0) {
    Write-Error "Ping failed. Is LM Studio server running with this model loaded?"
}

Write-Host ""
Write-Host "[2/3] Batch eval (4 rows)..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path (Split-Path $PredOut) | Out-Null
& $Python scripts/run_l3_eval_batch.py `
    --base-url $BaseUrl `
    --model $Model `
    --data data/eval_samples.jsonl data/eval_holdout_90.jsonl `
    --id $SmokeIds `
    --chat-template --retry 1 --repair `
    --out $PredOut
if ($LASTEXITCODE -ne 0) {
    Write-Error "Batch eval failed."
}

Write-Host ""
Write-Host "[3/3] Score smoke rows..." -ForegroundColor Yellow
& $Python scripts/score_laptop_smoke.py `
    --predictions $PredOut `
    --report $ReportOut
$ScoreExit = $LASTEXITCODE

Write-Host ""
if ($ScoreExit -eq 0) {
    Write-Host "RESULT: PASS ($Arm)" -ForegroundColor Green
    Write-Host "Record in outputs/LAPTOP_SMOKE_SIGNOFF.md"
} else {
    Write-Host "RESULT: FAIL ($Arm)" -ForegroundColor Red
    Write-Host "See $PredOut and $ReportOut"
}
exit $ScoreExit
