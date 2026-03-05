#Requires -Version 5.1
<#
.SYNOPSIS
    ecom-analytics Uninstaller for Windows
.DESCRIPTION
    Removes all ecom-analytics skill files from ~/.claude/skills/
.EXAMPLE
    .\uninstall.ps1
#>

$ErrorActionPreference = "Stop"

$SkillDir = Join-Path $env:USERPROFILE ".claude\skills\ecom-analytics"

$SubSkills = @(
    "ecom-audit"
    "ecom-cohort"
    "ecom-context"
    "ecom-conversion"
    "ecom-experiment"
    "ecom-inventory"
    "ecom-pricing"
    "ecom-product"
    "ecom-quickwins"
    "ecom-revenue"
)

Write-Host "This will remove ecom-analytics skills from ~\.claude\skills\"
Write-Host ""
Write-Host "  Directories to remove:"
Write-Host "    - $SkillDir"
foreach ($s in $SubSkills) {
    Write-Host "    - $(Join-Path $env:USERPROFILE ".claude\skills\$s")"
}
Write-Host ""

$confirm = Read-Host "Continue? [y/N]"
if ($confirm -notmatch "^[Yy]$") {
    Write-Host "Cancelled."
    exit 0
}

if (Test-Path $SkillDir) {
    Remove-Item -Recurse -Force $SkillDir
}
foreach ($s in $SubSkills) {
    $path = Join-Path $env:USERPROFILE ".claude\skills\$s"
    if (Test-Path $path) {
        Remove-Item -Recurse -Force $path
    }
}

Write-Host ""
Write-Host "[ok] ecom-analytics uninstalled." -ForegroundColor Green
