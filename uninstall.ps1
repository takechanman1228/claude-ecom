#Requires -Version 5.1
<#
.SYNOPSIS
    claude-ecom Uninstaller for Windows
.DESCRIPTION
    Removes claude-ecom skill files from ~/.claude/skills/
.EXAMPLE
    .\uninstall.ps1
#>

$ErrorActionPreference = "Stop"

$SkillDir = Join-Path $env:USERPROFILE ".claude\skills\ecom"

Write-Host "This will remove claude-ecom skill from ~\.claude\skills\"
Write-Host ""
Write-Host "  Directory to remove:"
Write-Host "    - $SkillDir"
Write-Host ""

$confirm = Read-Host "Continue? [y/N]"
if ($confirm -notmatch "^[Yy]$") {
    Write-Host "Cancelled."
    exit 0
}

if (Test-Path $SkillDir) {
    Remove-Item -Recurse -Force $SkillDir
}

Write-Host ""
Write-Host "[ok] claude-ecom uninstalled." -ForegroundColor Green
