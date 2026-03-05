#Requires -Version 5.1
<#
.SYNOPSIS
    ecom-analytics Installer for Windows
.DESCRIPTION
    Installs ecom-analytics skill files into ~/.claude/skills/
.PARAMETER WithCLI
    Also install the Python CLI package via pip
.EXAMPLE
    .\install.ps1
    .\install.ps1 -WithCLI
#>

param(
    [switch]$WithCLI
)

$ErrorActionPreference = "Stop"

# ── Configuration ──────────────────────────────────────────────
$SkillDir   = Join-Path $env:USERPROFILE ".claude\skills\ecom-analytics"
# TODO: Replace with actual repo URL once created
$RepoUrl    = "https://github.com/<user>/ecom-analytics"

# ── Banner ─────────────────────────────────────────────────────
Write-Host ""
Write-Host ([char]0x2550 * 40)
Write-Host "   ecom-analytics - Installer"
Write-Host "   EC Data Analytics Skill"
Write-Host ([char]0x2550 * 40)
Write-Host ""

# ── Prerequisites ──────────────────────────────────────────────
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Error: git is required but not installed." -ForegroundColor Red
    exit 1
}
Write-Host "[ok] Git detected"

# ── Create directories ─────────────────────────────────────────
New-Item -ItemType Directory -Path (Join-Path $SkillDir "references") -Force | Out-Null

# ── Clone to temp dir ──────────────────────────────────────────
$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("ecom-analytics-" + [guid]::NewGuid().ToString("N").Substring(0, 8))

Write-Host "[..] Downloading ecom-analytics..."
try {
    git clone --depth 1 $RepoUrl "$TempDir\ecom-analytics" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "clone failed" }
} catch {
    Write-Host "Error: Failed to clone from $RepoUrl" -ForegroundColor Red
    Write-Host "  If the repository hasn't been created yet, update REPO_URL in this script." -ForegroundColor Red
    exit 1
} finally {
    # Register cleanup — runs whether we succeed or fail later
    $cleanupBlock = {
        if (Test-Path $TempDir) {
            Remove-Item -Recurse -Force $TempDir -ErrorAction SilentlyContinue
        }
    }
    Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action $cleanupBlock | Out-Null
}

$CloneRoot = Join-Path $TempDir "ecom-analytics"

# ── Copy main skill + references ───────────────────────────────
Write-Host "[..] Installing skill files..."
Copy-Item (Join-Path $CloneRoot "skills\ecom-analytics\SKILL.md") -Destination (Join-Path $SkillDir "SKILL.md") -Force
Copy-Item (Join-Path $CloneRoot "skills\ecom-analytics\references\*.md") -Destination (Join-Path $SkillDir "references") -Force

# ── Copy sub-skills ────────────────────────────────────────────
Write-Host "[..] Installing sub-skills..."
$SubSkillsRoot = Join-Path $CloneRoot "skills"
Get-ChildItem -Path $SubSkillsRoot -Directory -Filter "ecom-*" | ForEach-Object {
    $skillName = $_.Name
    # Skip the main orchestrator (already copied)
    if ($skillName -eq "ecom-analytics") { return }

    $target = Join-Path $env:USERPROFILE ".claude\skills\$skillName"
    New-Item -ItemType Directory -Path $target -Force | Out-Null
    Copy-Item (Join-Path $_.FullName "SKILL.md") -Destination (Join-Path $target "SKILL.md") -Force
}

# ── Optional: install Python CLI ───────────────────────────────
if ($WithCLI) {
    Write-Host "[..] Installing Python CLI..."
    if (-not (Get-Command pip -ErrorAction SilentlyContinue)) {
        Write-Host "Error: pip is required for -WithCLI." -ForegroundColor Red
        exit 1
    }
    pip install $CloneRoot --quiet
}

# ── Cleanup temp dir now ───────────────────────────────────────
if (Test-Path $TempDir) {
    Remove-Item -Recurse -Force $TempDir -ErrorAction SilentlyContinue
}

# ── Summary ────────────────────────────────────────────────────
Write-Host ""
Write-Host "[ok] ecom-analytics installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "  Installed:"
Write-Host "    - 1 main skill (ecom-analytics orchestrator)"
Write-Host "    - 11 sub-skills"
Write-Host "    - 11 reference files"
Write-Host ""
Write-Host "  Usage:"
Write-Host "    1. Start Claude Code:  claude"
Write-Host "    2. Run commands:       /ecom-analytics audit"
Write-Host "                           /ecom-analytics revenue"
Write-Host "                           /ecom-analytics cohort"
Write-Host ""
if ($WithCLI) {
    Write-Host "  CLI installed. Run: ecom-analytics audit orders.csv"
} else {
    Write-Host "  To also install the Python CLI: .\install.ps1 -WithCLI"
}
Write-Host ""
Write-Host "  To uninstall: .\uninstall.ps1"
