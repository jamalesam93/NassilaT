# Verify local Sanad GGUFs match Hugging Face (size + SHA256 + README).
# Usage:
#   .\scripts\verify_hf_release.ps1
#   .\scripts\verify_hf_release.ps1 -E4bPath "D:\...\nassila-sanad-e4b-q6_k" -Path12b "D:\...\nassila-sanad-12b-q6_k"

param(
    [string]$E4bPath = "D:\LM_Studio_Models\lmstudio-community\nassila-sanad-e4b-q6_k",
    [string]$Path12b = "D:\LM_Studio_Models\lmstudio-community\nassila-sanad-12b-q6_k",
    [switch]$NoHash
)

$ErrorActionPreference = "Stop"
$TrainingDir = Split-Path $PSScriptRoot -Parent
Set-Location $TrainingDir

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Error "Missing venv. Run: python -m venv .venv; .\.venv\Scripts\activate; pip install -r requirements.txt"
}
$Python = ".\.venv\Scripts\python.exe"

$args = @(
    "scripts/verify_hf_release.py",
    "--e4b-path", $E4bPath,
    "--path-12b", $Path12b
)
if ($NoHash) { $args += "--no-hash" }

& $Python @args
exit $LASTEXITCODE
