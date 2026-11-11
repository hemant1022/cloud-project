<#
.SYNOPSIS
    Run a command and capture its output in a per-stack log file.

.DESCRIPTION
    Wraps any command so that every run is logged under logs/<Stack>/ with a
    timestamped filename. Keeps docker, terraform, ci, argocd, and monitoring
    logs isolated from each other.

.EXAMPLE
    .\scripts\run-logged.ps1 -Stack terraform -Phase 02 -Action plan `
        -Command "terraform -chdir=infra/envs/dev plan"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('backend', 'frontend', 'docker', 'terraform', 'ci', 'argocd', 'monitoring')]
    [string]$Stack,

    [Parameter(Mandatory = $true)]
    [string]$Phase,

    [Parameter(Mandatory = $true)]
    [string]$Action,

    [Parameter(Mandatory = $true)]
    [string]$Command
)

$ErrorActionPreference = 'Continue'

$repoRoot = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $repoRoot (Join-Path 'logs' $Stack)
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$logPath = Join-Path $logDir ("{0}-{1}-{2}.log" -f $Phase, $Action, $timestamp)

$header = @(
    '==================== RUN LOG ===================='
    "Timestamp : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
    "User      : $env:USERNAME"
    "Host      : $env:COMPUTERNAME"
    "Stack     : $Stack"
    "Phase     : $Phase"
    "Action    : $Action"
    "Directory : $(Get-Location)"
    "Command   : $Command"
    "Log file  : $logPath"
    '================================================='
    ''
) -join [Environment]::NewLine

$header | Tee-Object -FilePath $logPath
$started = Get-Date

Invoke-Expression $Command 2>&1 | Tee-Object -FilePath $logPath -Append

$exitCode = $LASTEXITCODE
if ($null -eq $exitCode) {
    $exitCode = if ($?) { 0 } else { 1 }
}

$duration = (Get-Date) - $started
$footer = @(
    ''
    '==================== SUMMARY ===================='
    "Started  : $($started.ToString('yyyy-MM-dd HH:mm:ss'))"
    "Duration : $([int]$duration.TotalSeconds)s"
    "ExitCode : $exitCode"
    '================================================='
) -join [Environment]::NewLine

$footer | Tee-Object -FilePath $logPath -Append

exit $exitCode
