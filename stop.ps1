<#
.SYNOPSIS
    Destroy the AWS/EKS inventory stack with one command.

.DESCRIPTION
    Deletes the Kubernetes workloads, EKS environment, ECR repository, and
    Terraform state backend. Use -KeepState or -KeepImages to retain them.

.EXAMPLE
    .\stop.ps1

.EXAMPLE
    .\stop.ps1 -Force -KeepImages

.EXAMPLE
    .\stop.ps1 -DryRun
#>
[CmdletBinding()]
param(
    [string]$Project = "cloud-project",
    [string]$Environment = "dev",
    [string]$Region = "us-east-1",
    [switch]$Force,
    [switch]$KeepState,
    [switch]$KeepImages,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$arguments = @{
    Project          = $Project
    Environment      = $Environment
    Region           = $Region
    IncludeBootstrap = (-not $KeepState)
    DeleteEcr        = (-not $KeepImages)
}
if ($Force) {
    $arguments.Force = $true
}
if ($DryRun) {
    $arguments.DryRun = $true
}

& (Join-Path $PSScriptRoot "scripts/destroy-all.ps1") @arguments
exit $LASTEXITCODE
