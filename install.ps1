#Requires -Version 5.1
<#
.SYNOPSIS
    claude-ecom Installer for Windows
.DESCRIPTION
    Installs claude-ecom skill files into ~/.claude/skills/
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
$SkillDir   = Join-Path $env:USERPROFILE ".claude\skills\ecom"
# TODO: Replace with actual repo URL once created
$RepoUrl    = "https://github.com/takechanman1228/claude-ecom"

# ── Banner ─────────────────────────────────────────────────────
Write-Host ""
Write-Host ([char]0x2550 * 40)
Write-Host "   claude-ecom - Installer"
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
$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("claude-ecom-" + [guid]::NewGuid().ToString("N").Substring(0, 8))

Write-Host "[..] Downloading claude-ecom..."
try {
    git clone --depth 1 $RepoUrl "$TempDir\claude-ecom" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "clone failed" }
} catch {
    Write-Host "Error: Failed to clone from $RepoUrl" -ForegroundColor Red
    Write-Host "  If the repository hasn't been created yet, update REPO_URL in this script." -ForegroundColor Red
    exit 1
} finally {
    $cleanupBlock = {
        if (Test-Path $TempDir) {
            Remove-Item -Recurse -Force $TempDir -ErrorAction SilentlyContinue
        }
    }
    Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action $cleanupBlock | Out-Null
}

$CloneRoot = Join-Path $TempDir "claude-ecom"

# ── Copy skill + references ───────────────────────────────────
Write-Host "[..] Installing skill files..."
Copy-Item (Join-Path $CloneRoot "skills\ecom\SKILL.md") -Destination (Join-Path $SkillDir "SKILL.md") -Force
Copy-Item (Join-Path $CloneRoot "skills\ecom\references\*.md") -Destination (Join-Path $SkillDir "references") -Force

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
Write-Host "[ok] claude-ecom installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "  Installed:"
Write-Host "    - 1 skill (ecom)"
Write-Host "    - 16 reference files"
Write-Host ""
Write-Host "  Usage:"
Write-Host "    1. Start Claude Code:  claude"
Write-Host "    2. Run commands:       /ecom audit"
Write-Host "                           /ecom review"
Write-Host ""
if ($WithCLI) {
    Write-Host "  CLI installed. Run: ecom audit orders.csv"
} else {
    Write-Host "  To also install the Python CLI: .\install.ps1 -WithCLI"
}
Write-Host ""
Write-Host "  To uninstall: .\uninstall.ps1"
