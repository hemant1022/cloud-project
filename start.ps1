<#
.SYNOPSIS
    Deploy the complete AWS/EKS inventory stack with one command.

.EXAMPLE
    .\start.ps1

.EXAMPLE
    .\start.ps1 -SkipMonitoring
#>
[CmdletBinding()]
param(
    [string]$Project = "cloud-project",
    [string]$Environment = "dev",
    [string]$Region = "us-east-1",
    [switch]$SkipMonitoring,
    [switch]$SkipImageBuild
)

$ErrorActionPreference = "Stop"

$arguments = @{
    Project     = $Project
    Environment = $Environment
    Region      = $Region
}
if ($SkipMonitoring) {
    $arguments.SkipMonitoring = $true
}
if ($SkipImageBuild) {
    $arguments.SkipImageBuild = $true
}

& (Join-Path $PSScriptRoot "scripts/deploy-all.ps1") @arguments
exit $LASTEXITCODE
