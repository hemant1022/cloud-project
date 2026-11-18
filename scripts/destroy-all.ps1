<#
.SYNOPSIS
    Destroy the inventory stack and its AWS resources.

.DESCRIPTION
    Deletes the ArgoCD applications, releases Kubernetes load balancers and
    monitoring resources, runs terraform destroy for the dev environment, and
    optionally removes the ECR repository and Terraform state backend.

.PARAMETER Project
    Project name used in AWS resource names. Default: cloud-project.

.PARAMETER Environment
    Environment suffix used in the cluster name. Default: dev.

.PARAMETER Region
    AWS region. Default: us-east-1.

.PARAMETER Force
    Skip the interactive confirmation prompt.

.PARAMETER IncludeBootstrap
    Also delete the Terraform S3 state bucket and DynamoDB lock table.

.PARAMETER DeleteEcr
    Also delete the ECR repository and all of its images.

.PARAMETER DryRun
    Show what would be deleted without changing anything.

.EXAMPLE
    .\scripts\destroy-all.ps1

.EXAMPLE
    .\scripts\destroy-all.ps1 -Force -IncludeBootstrap -DeleteEcr
#>
[CmdletBinding()]
param(
    [string]$Project = "cloud-project",
    [string]$Environment = "dev",
    [string]$Region = "us-east-1",
    [switch]$Force,
    [switch]$IncludeBootstrap,
    [switch]$DeleteEcr,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Split-Path -Parent $PSScriptRoot
$TfDir = Join-Path $RepoRoot "infra/envs/dev"
$BootstrapDir = Join-Path $RepoRoot "infra/bootstrap"
$ClusterName = "$Project-$Environment"
$InventoryNamespace = "inventory"
$MonitoringNamespace = "monitoring"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Info([string]$Message) {
    Write-Host "    $Message" -ForegroundColor DarkGray
}

function Assert-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command: $Name"
    }
}

function Invoke-TerraformInit([string]$Directory) {
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        terraform "-chdir=$Directory" init -input=false
        if ($LASTEXITCODE -eq 0) {
            return
        }
        if ($attempt -lt 3) {
            Write-Warning "terraform init failed on attempt $attempt of 3; retrying in 10 seconds."
            Start-Sleep -Seconds 10
        }
    }
    throw "terraform init failed in $Directory"
}

function Test-ClusterExists {
    aws eks describe-cluster --name $ClusterName --region $Region --query "cluster.status" --output text 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Uninstall-HelmRelease([string]$Namespace, [string]$Name) {
    helm status $Name -n $Namespace 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Info "Helm release $Name not found in $Namespace."
        return
    }

    Write-Info "Uninstalling Helm release $Name from $Namespace..."
    helm uninstall $Name -n $Namespace --wait --timeout 10m 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Unable to fully uninstall Helm release $Name; continuing."
    }
}

function Remove-KubernetesResources {
    if (-not (Test-ClusterExists)) {
        Write-Info "EKS cluster not found; skipping Kubernetes cleanup."
        return
    }

    Write-Step "Deleting ArgoCD applications"
    aws eks update-kubeconfig --name $ClusterName --region $Region | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Unable to update kubeconfig; skipping Kubernetes cleanup."
        return
    }

    kubectl -n argocd delete application inventory-apps --ignore-not-found --wait=true --timeout=120s 2>$null | Out-Null
    kubectl -n argocd delete application inventory-dev --ignore-not-found --wait=true --timeout=180s 2>$null | Out-Null

    Write-Step "Waiting for the application load balancer to be released"
    for ($i = 0; $i -lt 60; $i++) {
        $ingressName = kubectl -n $InventoryNamespace get ingress inventory --ignore-not-found -o name 2>$null
        if (-not $ingressName) {
            Write-Info "Application ingress is gone."
            break
        }
        Start-Sleep -Seconds 5
    }

    Write-Step "Uninstalling Helm releases"
    if (Get-Command helm -ErrorAction SilentlyContinue) {
        Uninstall-HelmRelease -Namespace $MonitoringNamespace -Name "monitoring"
        Uninstall-HelmRelease -Namespace "kube-system" -Name "aws-load-balancer-controller"
    }
    else {
        Write-Warning "helm not found; skipping Helm release cleanup."
    }
}

function Get-ClusterLoadBalancerArns {
    $raw = aws elbv2 describe-load-balancers --region $Region --query "LoadBalancers[].LoadBalancerArn" --output text 2>$null
    $arns = @($raw -split '\s+' | Where-Object { $_ -match '^arn:aws:elasticloadbalancing:' })

    $result = @()
    foreach ($arn in $arns) {
        $tagValue = aws elbv2 describe-tags --resource-arns $arn --region $Region --query "TagDescriptions[0].Tags[?Key=='elbv2.k8s.aws/cluster'].Value" --output text 2>$null
        if ($tagValue -and $tagValue.Trim() -eq $ClusterName) {
            $result += $arn
        }
    }
    return $result
}

function Remove-OrphanLoadBalancers {
    Write-Step "Removing leftover load balancers for $ClusterName"
    $arns = @(Get-ClusterLoadBalancerArns)
    if ($arns.Count -eq 0) {
        Write-Info "No leftover load balancers found."
        return
    }

    foreach ($arn in $arns) {
        Write-Info "Deleting $arn"
        aws elbv2 delete-load-balancer --load-balancer-arn $arn --region $Region 2>$null | Out-Null
    }

    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 5
        $remaining = @(Get-ClusterLoadBalancerArns)
        if ($remaining.Count -eq 0) {
            Write-Info "Load balancers deleted."
            return
        }
    }
    Write-Warning "Some load balancers are still deleting: $($remaining -join ', ')"
}

function Remove-OrphanSecurityGroups {
    Write-Step "Removing leftover load-balancer security groups"
    for ($attempt = 0; $attempt -lt 3; $attempt++) {
        $raw = aws ec2 describe-security-groups --region $Region --filters "Name=tag:elbv2.k8s.aws/cluster,Values=$ClusterName" --query "SecurityGroups[].GroupId" --output text 2>$null
        $groupIds = @($raw -split '\s+' | Where-Object { $_ -match '^sg-' })
        if ($groupIds.Count -eq 0) {
            Write-Info "No leftover load-balancer security groups found."
            return
        }

        foreach ($groupId in $groupIds) {
            aws ec2 delete-security-group --group-id $groupId --region $Region 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Info "Deleted security group $groupId"
            }
        }
        Start-Sleep -Seconds 5
    }
    Write-Warning "Some load-balancer security groups may remain."
}

function Destroy-Environment {
    Write-Step "Destroying Terraform environment"
    Invoke-TerraformInit -Directory $TfDir

    terraform "-chdir=$TfDir" destroy -auto-approve -input=false
    if ($LASTEXITCODE -eq 0) {
        Write-Info "Environment destroyed."
        return
    }

    Write-Warning "First destroy attempt failed; cleaning up leftovers and retrying."
    Remove-OrphanLoadBalancers
    Remove-OrphanSecurityGroups
    Start-Sleep -Seconds 20

    terraform "-chdir=$TfDir" destroy -auto-approve -input=false
    if ($LASTEXITCODE -ne 0) {
        throw "terraform destroy failed. Review the errors above and re-run this script."
    }
    Write-Info "Environment destroyed."
}

function Remove-OrphanVolumes {
    Write-Step "Removing leftover EBS volumes for $ClusterName"
    for ($attempt = 0; $attempt -lt 24; $attempt++) {
        $raw = aws ec2 describe-volumes --region $Region --filters "Name=tag:ebs.csi.aws.com/cluster-name,Values=$ClusterName" "Name=status,Values=available" --query "Volumes[].VolumeId" --output text 2>$null
        $volumeIds = @($raw -split '\s+' | Where-Object { $_ -match '^vol-' })
        if ($volumeIds.Count -eq 0) {
            Write-Info "No leftover available EBS volumes found."
            return
        }

        foreach ($volumeId in $volumeIds) {
            aws ec2 delete-volume --volume-id $volumeId --region $Region 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Info "Deleted volume $volumeId"
            }
        }
        Start-Sleep -Seconds 5
    }
    Write-Warning "Some EBS volumes are still attached or deleting."
}

function Empty-S3Bucket([string]$Bucket) {
    aws s3api head-bucket --bucket $Bucket 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Info "Bucket $Bucket not found."
        return
    }

    Write-Info "Deleting all object versions in $Bucket..."
    $deleteFile = Join-Path $env:TEMP "s3-delete-$PID.json"
    try {
        while ($true) {
            $json = aws s3api list-object-versions --bucket $Bucket --max-items 1000 --output json 2>$null
            if ($LASTEXITCODE -ne 0) {
                throw "Unable to list versions in $Bucket"
            }
            if (-not $json -or $json.Trim() -eq "None") {
                break
            }

            $response = $json | ConvertFrom-Json
            $objects = @()
            if ($response.PSObject.Properties.Name -contains "Versions") {
                foreach ($version in @($response.Versions)) {
                    $objects += [pscustomobject]@{ Key = $version.Key; VersionId = $version.VersionId }
                }
            }
            if ($response.PSObject.Properties.Name -contains "DeleteMarkers") {
                foreach ($marker in @($response.DeleteMarkers)) {
                    $objects += [pscustomobject]@{ Key = $marker.Key; VersionId = $marker.VersionId }
                }
            }
            if ($objects.Count -eq 0) {
                break
            }

            $payload = @{ Objects = $objects; Quiet = $true } | ConvertTo-Json -Depth 5 -Compress
            [System.IO.File]::WriteAllText($deleteFile, $payload)

            aws s3api delete-objects --bucket $Bucket --delete "file://$deleteFile" 2>$null | Out-Null
            if ($LASTEXITCODE -ne 0) {
                throw "Unable to delete object versions from $Bucket"
            }
        }
    }
    finally {
        Remove-Item -LiteralPath $deleteFile -Force -ErrorAction SilentlyContinue
    }
}

function Remove-StateBackend {
    Write-Step "Destroying Terraform state backend"
    $bootstrapState = Join-Path $BootstrapDir "terraform.tfstate"
    $bucketName = "$Project-tfstate-$script:AccountId"
    $tableName = "$Project-tfstate-lock"

    Empty-S3Bucket -Bucket $bucketName

    if (Test-Path -LiteralPath $bootstrapState) {
        Invoke-TerraformInit -Directory $BootstrapDir
        terraform "-chdir=$BootstrapDir" destroy -auto-approve -input=false
        if ($LASTEXITCODE -eq 0) {
            Write-Info "State backend destroyed."
            return
        }
        Write-Warning "Terraform could not destroy the state backend; deleting remaining resources directly."
    }

    aws s3api head-bucket --bucket $bucketName 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        aws s3api delete-bucket --bucket $bucketName --region $Region 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Info "Deleted S3 bucket $bucketName"
        }
    }

    aws dynamodb describe-table --table-name $tableName --region $Region 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        aws dynamodb delete-table --table-name $tableName --region $Region 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Info "Deleted DynamoDB table $tableName"
        }
    }
}

function Get-EcrRepositoryName {
    $kustomizationPath = Join-Path $RepoRoot "k8s/overlays/dev/kustomization.yaml"
    if (Test-Path -LiteralPath $kustomizationPath) {
        $kustomization = Get-Content -LiteralPath $kustomizationPath -Raw
        $match = [regex]::Match($kustomization, 'newName:\s*(\S+)')
        if ($match.Success) {
            $parts = $match.Groups[1].Value -split '/', 2
            if ($parts.Count -eq 2) {
                return $parts[1]
            }
        }
    }
    return "tier3app"
}

function Remove-EcrRepository {
    $repository = Get-EcrRepositoryName
    Write-Step "Deleting ECR repository $repository"
    aws ecr describe-repositories --repository-names $repository --region $Region 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Info "ECR repository $repository not found."
        return
    }

    aws ecr delete-repository --repository-name $repository --force --region $Region 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to delete ECR repository $repository"
    }
    Write-Info "ECR repository deleted."
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

foreach ($command in @("aws", "terraform")) {
    Assert-Command $command
}

$script:AccountId = (aws sts get-caller-identity --query Account --output text).Trim()
if ($LASTEXITCODE -ne 0 -or -not $script:AccountId) {
    throw "Unable to read the current AWS account. Check your AWS credentials."
}

Write-Host ""
Write-Host "This will permanently delete:" -ForegroundColor Yellow
Write-Host "  - ArgoCD applications and Kubernetes workloads in $ClusterName"
Write-Host "  - The EKS cluster, VPC, node groups, and related IAM resources"
if ($DeleteEcr) {
    Write-Host "  - ECR repository $(Get-EcrRepositoryName) and all images"
}
if ($IncludeBootstrap) {
    Write-Host "  - Terraform state bucket $Project-tfstate-$script:AccountId and lock table $Project-tfstate-lock"
}
Write-Host ""

if ($DryRun) {
    Write-Step "Dry-run check"
    Write-Info "Cluster exists: $(Test-ClusterExists)"
    Write-Info "Load balancers tagged for ${ClusterName}: $(@(Get-ClusterLoadBalancerArns).Count)"
    if ($DeleteEcr) {
        $repository = Get-EcrRepositoryName
        aws ecr describe-repositories --repository-names $repository --region $Region 2>$null | Out-Null
        Write-Info "ECR repository $repository exists: $($LASTEXITCODE -eq 0)"
    }
    if ($IncludeBootstrap) {
        $bucketName = "$Project-tfstate-$script:AccountId"
        aws s3api head-bucket --bucket $bucketName 2>$null | Out-Null
        Write-Info "State bucket $bucketName exists: $($LASTEXITCODE -eq 0)"
        aws dynamodb describe-table --table-name "$Project-tfstate-lock" --region $Region 2>$null | Out-Null
        Write-Info "Lock table $Project-tfstate-lock exists: $($LASTEXITCODE -eq 0)"
    }
    Write-Host ""
    Write-Host "Dry run complete. Nothing was deleted." -ForegroundColor Green
    return
}

if (-not $Force) {
    $answer = Read-Host "Type 'destroy' to continue"
    if ($answer -ne "destroy") {
        Write-Host "Aborted." -ForegroundColor Yellow
        return
    }
}

if (Get-Command kubectl -ErrorAction SilentlyContinue) {
    Remove-KubernetesResources
}
else {
    Write-Warning "kubectl not found; skipping Kubernetes cleanup."
}

Remove-OrphanLoadBalancers
Remove-OrphanSecurityGroups
Destroy-Environment
Remove-OrphanVolumes

if ($DeleteEcr) {
    Remove-EcrRepository
}
if ($IncludeBootstrap) {
    Remove-StateBackend
}

Write-Host ""
Write-Host "Teardown complete." -ForegroundColor Green
if (-not $IncludeBootstrap) {
    Write-Host "Terraform state backend was kept. Re-run with -IncludeBootstrap to delete it."
}
if (-not $DeleteEcr) {
    Write-Host "ECR images were kept. Re-run with -DeleteEcr to delete them."
}
