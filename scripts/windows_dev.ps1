# PowerShell equivalent of the most common Makefile targets for Windows-native contributors.
# Prefer WSL2 + `make` where possible — see CONTRIBUTING.md.
#
# Usage:
#   .\scripts\windows_dev.ps1 setup
#   .\scripts\windows_dev.ps1 verify
#   .\scripts\windows_dev.ps1 lint
#   .\scripts\windows_dev.ps1 typecheck
#   .\scripts\windows_dev.ps1 test

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("setup", "verify", "lint", "typecheck", "test", "format", "help")]
    [string]$Target = "help"
)

$ErrorActionPreference = "Stop"

function Step($name, $cmd) {
    Write-Host "▶ $name" -ForegroundColor Cyan
    Invoke-Expression $cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ $name failed (exit $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host "✓ $name" -ForegroundColor Green
}

switch ($Target) {
    "setup" {
        Step "uv sync"        "uv sync --all-extras --all-packages"
        Step "pnpm install"   "pnpm install --frozen-lockfile"
        Step "pre-commit"     "uv run pre-commit install"
        Write-Host ""
        Write-Host "✓ setup complete. Try: .\scripts\windows_dev.ps1 verify"
    }
    "lint" {
        Step "ruff check"  "uv run ruff check ."
        Step "ruff format" "uv run ruff format --check ."
        Step "pnpm lint"   "pnpm -r lint"
    }
    "format" {
        Step "ruff format"   "uv run ruff format ."
        Step "ruff check --fix" "uv run ruff check . --fix"
        Step "pnpm format"   "pnpm -r format"
    }
    "typecheck" {
        Step "mypy" "uv run mypy packages/shared packages/sla packages/ml packages/content apps/api apps/worker"
        Step "tsc"  "pnpm -r typecheck"
    }
    "test" {
        Step "pytest"     "uv run pytest -x -q"
        Step "vitest"     "pnpm -r test"
    }
    "verify" {
        & $PSCommandPath lint
        & $PSCommandPath typecheck
        & $PSCommandPath test
        Write-Host ""
        Write-Host "✓ verify green" -ForegroundColor Green
    }
    default {
        Write-Host "Usage: .\scripts\windows_dev.ps1 <target>"
        Write-Host ""
        Write-Host "Targets: setup | lint | format | typecheck | test | verify"
        Write-Host ""
        Write-Host "Prefer the Makefile (WSL2 / Linux / macOS) when possible. The Makefile"
        Write-Host "is the source of truth; this script is a convenience for Windows-native"
        Write-Host "contributors. See CONTRIBUTING.md and RISK_REGISTER R-008."
    }
}
