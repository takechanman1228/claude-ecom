#Requires -Version 5.1
<#
.SYNOPSIS
    claude-ecom Installer for Windows
.DESCRIPTION
    Installs claude-ecom skill files and Python CLI into ~/.claude/skills/ecom/
    Creates a private venv — no global packages are modified.
.EXAMPLE
    .\install.ps1
#>

$ErrorActionPreference = "Stop"

# ── Configuration ──────────────────────────────────────────────
$SkillDir   = Join-Path $env:USERPROFILE ".claude\skills\ecom"
$VenvDir    = Join-Path $SkillDir ".venv"
$RepoUrl    = "https://github.com/takechanman1228/claude-ecom"

# ── Banner ─────────────────────────────────────────────────────
Write-Host ""
Write-Host ([char]0x2550 * 40)
Write-Host "   claude-ecom - Installer"
Write-Host "   Ecom Data Analytics Skill"
Write-Host ([char]0x2550 * 40)
Write-Host ""

# ── Prerequisites ──────────────────────────────────────────────
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Error: git is required but not installed." -ForegroundColor Red
    exit 1
}
Write-Host "[ok] Git detected"

# Check Python 3
$pythonCmd = $null
foreach ($cmd in @("python3", "python")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $ver = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($ver -and [version]$ver -ge [version]"3.10") {
            $pythonCmd = $cmd
            break
        }
    }
}
if (-not $pythonCmd) {
    Write-Host "Error: Python 3.10+ is required but not found." -ForegroundColor Red
    Write-Host "  Install from https://python.org" -ForegroundColor Red
    exit 1
}
Write-Host "[ok] Python $ver ($pythonCmd)"

# Check venv module
& $pythonCmd -c "import venv" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Python venv module is required but not available." -ForegroundColor Red
    exit 1
}

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

# ── Create private venv and install Python CLI ─────────────────
Write-Host "[..] Creating Python environment..."
& $pythonCmd -m venv $VenvDir

$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"

Write-Host "[..] Installing Python CLI (this may take a minute)..."
& $VenvPip install --upgrade pip --quiet 2>$null
& $VenvPip install $CloneRoot --quiet

# ── Create wrapper script ──────────────────────────────────────
$BinDir = Join-Path $SkillDir "bin"
New-Item -ItemType Directory -Path $BinDir -Force | Out-Null

$WrapperPath = Join-Path $BinDir "ecom.cmd"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
Set-Content -Path $WrapperPath -Value "@echo off`r`n`"$VenvPython`" -m claude_ecom.cli %*"

# Also create a bash wrapper for Git Bash / WSL
$BashWrapperPath = Join-Path $BinDir "ecom"
Set-Content -Path $BashWrapperPath -Value "#!/usr/bin/env bash`nexec `"`$(dirname `"`$0`")/../.venv/Scripts/python.exe`" -m claude_ecom.cli `"`$@`""

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
Write-Host "    - 6 reference files"
Write-Host "    - Python CLI (in private venv)"
Write-Host ""
Write-Host "  Usage:"
Write-Host "    1. Start Claude Code:  claude"
Write-Host "    2. Run command:        /ecom review"
Write-Host ""
Write-Host "  CLI: ~\.claude\skills\ecom\bin\ecom.cmd review orders.csv"
Write-Host ""
Write-Host "  To uninstall: .\uninstall.ps1"
