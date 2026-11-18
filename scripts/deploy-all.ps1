<#
.SYNOPSIS
    Deploy the complete inventory stack from a clean AWS account.

.DESCRIPTION
    Idempotently provisions the Terraform state backend, VPC/EKS cluster, AWS Load
    Balancer Controller, ECR images, application secret, ArgoCD, the app-of-apps,
    and the kube-prometheus-stack monitoring release.

.PARAMETER Project
    Project name used in AWS resource names. Default: cloud-project.

.PARAMETER Environment
    Environment suffix used in the cluster name. Default: dev.

.PARAMETER Region
    AWS region. Default: us-east-1.

.PARAMETER SkipMonitoring
    Skip the kube-prometheus-stack installation and Grafana resources.

.PARAMETER SkipImageBuild
    Fail instead of building/pushing images when ECR tags are missing.

.EXAMPLE
    .\scripts\deploy-all.ps1

.EXAMPLE
    .\scripts\deploy-all.ps1 -SkipMonitoring
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

function Assert-LastExitCode([string]$Message) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Message (exit code $LASTEXITCODE)"
    }
}

function Invoke-Probe([scriptblock]$Script) {
    $previous = $ErrorActionPreference
    $output = @()
    $exitCode = 1
    $ErrorActionPreference = "SilentlyContinue"
    try {
        $output = & $Script 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previous
    }
    return [pscustomobject]@{
        ExitCode = $exitCode
        Output   = ($output -join [Environment]::NewLine)
    }
}

function New-RandomPassword([int]$Length) {
    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    $bytes = New-Object byte[] $Length
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return -join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })
}

function Invoke-Terraform([string[]]$TerraformArgs, [string]$Description) {
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        & terraform @TerraformArgs
        if ($LASTEXITCODE -eq 0) {
            return
        }
        if ($attempt -lt 3) {
            Write-Warning "$Description failed on attempt $attempt of 3; retrying in 10 seconds."
            Start-Sleep -Seconds 10
        }
    }
    throw "$Description (exit code $LASTEXITCODE)"
}

function Get-K8sSecretValue([string]$Namespace, [string]$Name, [string]$Key) {
    $probe = Invoke-Probe { kubectl -n $Namespace get secret $Name -o "jsonpath={.data.$Key}" }
    if ($probe.ExitCode -ne 0) {
        return $null
    }
    $encoded = $probe.Output.Trim()
    if (-not $encoded) {
        return $null
    }
    return [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($encoded))
}

function Ensure-Bootstrap {
    Write-Step "Checking Terraform state backend"

    $accountId = (aws sts get-caller-identity --query Account --output text).Trim()
    Assert-LastExitCode "Unable to read the current AWS account. Check your AWS credentials."
    $bucket = "$Project-tfstate-$accountId"
    $table = "$Project-tfstate-lock"

    $bucketProbe = Invoke-Probe { aws s3api head-bucket --bucket $bucket }
    $bucketExists = ($bucketProbe.ExitCode -eq 0)
    $tableProbe = Invoke-Probe { aws dynamodb describe-table --table-name $table --region $Region --query "Table.TableStatus" --output text }
    $tableExists = ($tableProbe.ExitCode -eq 0)

    if ($bucketExists -and $tableExists) {
        Write-Info "State bucket and lock table already exist."
        return
    }
    if ($bucketExists -or $tableExists) {
        throw "Terraform state backend is partially present. Restore both $bucket and $table before deploying."
    }

    Invoke-Terraform -TerraformArgs @("-chdir=$BootstrapDir", "init", "-input=false") -Description "terraform init failed in infra/bootstrap"
    Invoke-Terraform -TerraformArgs @("-chdir=$BootstrapDir", "apply", "-auto-approve", "-input=false") -Description "terraform apply failed in infra/bootstrap"
}

function Ensure-KubectlAccess {
    Write-Step "Connecting to EKS cluster $ClusterName"
    aws eks update-kubeconfig --name $ClusterName --region $Region
    Assert-LastExitCode "aws eks update-kubeconfig failed"

    $nodesProbe = Invoke-Probe { kubectl get nodes }
    if ($nodesProbe.ExitCode -eq 0) {
        return
    }

    Write-Info "Granting the current AWS identity cluster access..."
    $principal = (aws sts get-caller-identity --query Arn --output text).Trim()
    if ($principal -match '^arn:aws:sts::(\d+):assumed-role/([^/]+)/') {
        $principal = "arn:aws:iam::$($matches[1]):role/$($matches[2])"
    }

    $accessProbe = Invoke-Probe { aws eks describe-access-entry --cluster-name $ClusterName --principal-arn $principal --region $Region }
    if ($accessProbe.ExitCode -ne 0) {
        aws eks create-access-entry --cluster-name $ClusterName --principal-arn $principal --region $Region | Out-Null
        Assert-LastExitCode "Unable to create an EKS access entry for $principal"
    }

    $policyArn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
    $associated = aws eks list-associated-access-policies --cluster-name $ClusterName --principal-arn $principal --region $Region --query "associatedAccessPolicies[?policyArn=='$policyArn'].policyArn" --output text
    if (-not $associated) {
        aws eks associate-access-policy --cluster-name $ClusterName --principal-arn $principal --policy-arn $policyArn --access-scope type=cluster --region $Region | Out-Null
        Assert-LastExitCode "Unable to associate the EKS cluster admin policy"
    }

    aws eks update-kubeconfig --name $ClusterName --region $Region
    Assert-LastExitCode "aws eks update-kubeconfig failed"
    kubectl get nodes | Out-Null
    Assert-LastExitCode "kubectl cannot reach the EKS cluster"
}

function Wait-ForNodes {
    $nodeGroup = (aws eks list-nodegroups --cluster-name $ClusterName --region $Region --query "nodegroups[0]" --output text).Trim()
    $desired = 1
    if ($nodeGroup -and $nodeGroup -ne "None") {
        $desiredText = aws eks describe-nodegroup --cluster-name $ClusterName --nodegroup-name $nodeGroup --region $Region --query "nodegroup.scalingConfig.desiredSize" --output text
        if ($LASTEXITCODE -eq 0 -and $desiredText) {
            $desired = [int]$desiredText
        }
    }

    Write-Step "Waiting for $desired Ready node(s)"
    for ($i = 0; $i -lt 120; $i++) {
        $nodeProbe = Invoke-Probe { kubectl get nodes --no-headers }
        $nodes = @()
        if ($nodeProbe.ExitCode -eq 0 -and $nodeProbe.Output) {
            $nodes = @($nodeProbe.Output -split "`r?`n" | Where-Object { $_.Trim() })
        }
        $ready = @($nodes | Where-Object { $_ -match '\sReady\s' })
        if ($nodes.Count -ge $desired -and $ready.Count -eq $nodes.Count) {
            Write-Info "$($nodes.Count) node(s) Ready."
            return
        }
        Start-Sleep -Seconds 10
    }
    throw "Timed out waiting for $desired Ready nodes"
}

function Install-LoadBalancerController {
    Write-Step "Installing AWS Load Balancer Controller"
    $null = Invoke-Probe { helm repo add eks https://aws.github.io/eks-charts }
    $null = Invoke-Probe { helm repo update }

    $roleArn = (terraform "-chdir=$TfDir" output -raw lb_controller_role_arn).Trim()
    $vpcId = (terraform "-chdir=$TfDir" output -raw vpc_id).Trim()
    $valuesPath = Join-Path $env:TEMP "lbc-values-$PID.yaml"
    $values = @"
clusterName: $ClusterName
region: $Region
vpcId: $vpcId
serviceAccount:
  create: true
  name: aws-load-balancer-controller
  annotations:
    eks.amazonaws.com/role-arn: $roleArn
"@
    [System.IO.File]::WriteAllText($valuesPath, $values, (New-Object System.Text.UTF8Encoding($false)))

    try {
        helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller `
            --namespace kube-system --version 3.6.3 -f $valuesPath --wait --timeout 10m
        Assert-LastExitCode "Helm install failed for the AWS Load Balancer Controller"
    }
    finally {
        Remove-Item -LiteralPath $valuesPath -Force -ErrorAction SilentlyContinue
    }

    kubectl -n kube-system rollout status deployment/aws-load-balancer-controller --timeout=10m
    Assert-LastExitCode "AWS Load Balancer Controller did not become ready"
}

function Get-DevImageSpecs {
    $kustomizationPath = Join-Path $RepoRoot "k8s/overlays/dev/kustomization.yaml"
    $kustomization = Get-Content -LiteralPath $kustomizationPath -Raw
    $newName = [regex]::Match($kustomization, 'newName:\s*(\S+)')
    if (-not $newName.Success) {
        throw "Could not find an ECR image name in k8s/overlays/dev/kustomization.yaml"
    }

    $registry = $newName.Groups[1].Value.Split('/')[0]
    $repository = $newName.Groups[1].Value.Split('/')[1]
    $backendTag = [regex]::Match($kustomization, 'newTag:\s*(backend-\S+)').Groups[1].Value
    $frontendTag = [regex]::Match($kustomization, 'newTag:\s*(frontend-\S+)').Groups[1].Value

    if (-not $backendTag -or -not $frontendTag) {
        throw "Could not resolve backend/frontend image tags from k8s/overlays/dev/kustomization.yaml"
    }

    return [pscustomobject]@{
        Specs = @(
            [pscustomobject]@{ Context = "app/backend"; Tag = $backendTag; BuildArgs = @() },
            [pscustomobject]@{ Context = "app/frontend"; Tag = $frontendTag; BuildArgs = @("--build-arg", "VITE_API_BASE_URL=/api") }
        )
        Registry = $registry
        Repository = $repository
    }
}

function Ensure-Images {
    Write-Step "Checking application images in ECR"
    $imageSpec = Get-DevImageSpecs
    $specs = $imageSpec.Specs
    $registry = $imageSpec.Registry
    $repository = $imageSpec.Repository

    $repoProbe = Invoke-Probe { aws ecr describe-repositories --repository-names $repository --region $Region }
    if ($repoProbe.ExitCode -ne 0) {
        Write-Info "Creating ECR repository $repository"
        aws ecr create-repository --repository-name $repository --region $Region --image-scanning-configuration scanOnPush=true | Out-Null
        Assert-LastExitCode "Unable to create ECR repository $repository"
    }

    $missing = @()
    foreach ($spec in $specs) {
        $imageProbe = Invoke-Probe { aws ecr describe-images --repository-name $repository --image-ids "imageTag=$($spec.Tag)" --region $Region }
        if ($imageProbe.ExitCode -ne 0) {
            $missing += $spec
        }
    }

    if ($missing.Count -eq 0) {
        Write-Info "All application image tags already exist."
        return
    }

    if ($SkipImageBuild) {
        throw "Missing ECR images: $($missing.Tag -join ', '). Re-run without -SkipImageBuild or push the images through CI."
    }

    Assert-Command docker
    $dockerProbe = Invoke-Probe { docker version }
    if ($dockerProbe.ExitCode -ne 0) {
        throw "Docker is not running or not installed"
    }

    Write-Step "Building and pushing $($missing.Count) missing image(s)"
    aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $registry
    Assert-LastExitCode "Docker login to ECR failed"

    foreach ($spec in $missing) {
        $image = "${registry}/${repository}:$($spec.Tag)"
        $arguments = @("build") + $spec.BuildArgs + @("-t", $image, (Join-Path $RepoRoot $spec.Context))
        Write-Info "docker $($arguments -join ' ')"
        & docker @arguments
        Assert-LastExitCode "Docker build failed for $($spec.Context)"
        docker push $image
        Assert-LastExitCode "Docker push failed for $image"
    }
}

function Ensure-InventorySecret {
    Write-Step "Ensuring application secret"
    kubectl create namespace $InventoryNamespace --dry-run=client -o yaml | kubectl apply -f - | Out-Null
    Assert-LastExitCode "Unable to create namespace $InventoryNamespace"

    $existingProbe = Invoke-Probe { kubectl -n $InventoryNamespace get secret inventory-secrets --ignore-not-found -o name }
    $existing = if ($existingProbe.ExitCode -eq 0) { $existingProbe.Output.Trim() } else { $null }
    if ($existing) {
        Write-Info "inventory-secrets already exists; leaving it unchanged."
        return
    }

    $postgresPassword = New-RandomPassword 24
    $jwtSecret = New-RandomPassword 48
    $adminPassword = New-RandomPassword 24
    $databaseUrl = "postgresql+psycopg2://inventory:$postgresPassword@db:5432/inventory"

    kubectl -n $InventoryNamespace create secret generic inventory-secrets `
        --from-literal="POSTGRES_PASSWORD=$postgresPassword" `
        --from-literal="DATABASE_URL=$databaseUrl" `
        --from-literal="JWT_SECRET=$jwtSecret" `
        --from-literal="ADMIN_EMAIL=admin@inventory.local" `
        --from-literal="ADMIN_PASSWORD=$adminPassword" `
        --dry-run=client -o yaml | kubectl apply -f - | Out-Null
    Assert-LastExitCode "Unable to create inventory-secrets"
    Write-Info "Created inventory-secrets with generated credentials."
}

function Ensure-ArgoCD {
    Write-Step "Installing ArgoCD"
    kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f - | Out-Null
    Assert-LastExitCode "Unable to create namespace argocd"

    kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
    Assert-LastExitCode "Unable to install ArgoCD"

    kubectl -n argocd wait --for=condition=Available deployment --all --timeout=10m
    Assert-LastExitCode "ArgoCD deployments did not become available"
    kubectl -n argocd rollout status statefulset/argocd-application-controller --timeout=10m
    Assert-LastExitCode "ArgoCD application controller did not become ready"

    Write-Step "Registering the app-of-apps"
    kubectl apply -f (Join-Path $RepoRoot "k8s/argocd/app-of-apps.yaml")
    Assert-LastExitCode "Unable to apply the ArgoCD app-of-apps"

    for ($i = 0; $i -lt 60; $i++) {
        $appProbe = Invoke-Probe { kubectl -n argocd get application inventory-dev --ignore-not-found -o name }
        $application = if ($appProbe.ExitCode -eq 0) { $appProbe.Output.Trim() } else { $null }
        if ($application) {
            break
        }
        Start-Sleep -Seconds 5
    }

    Write-Step "Waiting for inventory-dev to become Synced/Healthy"
    for ($i = 0; $i -lt 90; $i++) {
        $syncProbe = Invoke-Probe { kubectl -n argocd get application inventory-dev -o "jsonpath={.status.sync.status}" }
        $healthProbe = Invoke-Probe { kubectl -n argocd get application inventory-dev -o "jsonpath={.status.health.status}" }
        $sync = if ($syncProbe.ExitCode -eq 0) { $syncProbe.Output.Trim() } else { $null }
        $health = if ($healthProbe.ExitCode -eq 0) { $healthProbe.Output.Trim() } else { $null }
        if ($sync -eq "Synced" -and $health -eq "Healthy") {
            Write-Info "inventory-dev is Synced/Healthy."
            return
        }
        if (($i % 6) -eq 0) {
            Write-Info "status: $sync/$health"
        }
        Start-Sleep -Seconds 10
    }
    throw "inventory-dev did not reach Synced/Healthy within 15 minutes"
}

function Ensure-Monitoring {
    if ($SkipMonitoring) {
        Write-Step "Skipping monitoring (-SkipMonitoring)"
        return
    }

    Write-Step "Installing kube-prometheus-stack"
    $null = Invoke-Probe { helm repo add prometheus-community https://prometheus-community.github.io/helm-charts }
    $null = Invoke-Probe { helm repo update }

    kubectl create namespace $MonitoringNamespace --dry-run=client -o yaml | kubectl apply -f - | Out-Null
    Assert-LastExitCode "Unable to create namespace $MonitoringNamespace"

    $secretProbe = Invoke-Probe { kubectl -n $MonitoringNamespace get secret grafana-admin --ignore-not-found -o name }
    $existingSecret = if ($secretProbe.ExitCode -eq 0) { $secretProbe.Output.Trim() } else { $null }
    if (-not $existingSecret) {
        $grafanaPassword = New-RandomPassword 24
        kubectl -n $MonitoringNamespace create secret generic grafana-admin `
            --from-literal="admin-user=admin" `
            --from-literal="admin-password=$grafanaPassword" `
            --dry-run=client -o yaml | kubectl apply -f - | Out-Null
        Assert-LastExitCode "Unable to create the Grafana admin secret"
    }

    $crdsPath = Join-Path $env:TEMP "kube-prometheus-stack-crds-$PID.yaml"
    try {
        $crds = & helm show crds prometheus-community/kube-prometheus-stack --version 93.3.0
        Assert-LastExitCode "Unable to read kube-prometheus-stack CRDs"
        [System.IO.File]::WriteAllText($crdsPath, ($crds -join [Environment]::NewLine), (New-Object System.Text.UTF8Encoding($false)))
        kubectl apply --server-side --force-conflicts -f $crdsPath
        Assert-LastExitCode "Unable to apply kube-prometheus-stack CRDs"
    }
    finally {
        Remove-Item -LiteralPath $crdsPath -Force -ErrorAction SilentlyContinue
    }

    helm upgrade --install monitoring prometheus-community/kube-prometheus-stack `
        --namespace $MonitoringNamespace --version 93.3.0 `
        --values (Join-Path $RepoRoot "monitoring/prometheus/values.yaml") `
        --skip-crds --wait --timeout 15m
    Assert-LastExitCode "Helm install failed for kube-prometheus-stack"

    Write-Step "Applying ServiceMonitor, alerts, and dashboard"
    kubectl apply -f (Join-Path $RepoRoot "monitoring/prometheus/servicemonitor.yaml")
    Assert-LastExitCode "Unable to apply the backend ServiceMonitor"
    kubectl apply -f (Join-Path $RepoRoot "monitoring/prometheus/inventory-alerts.yaml")
    Assert-LastExitCode "Unable to apply the alert rules"
    kubectl apply -k (Join-Path $RepoRoot "monitoring/grafana/dashboards")
    Assert-LastExitCode "Unable to apply the Grafana dashboard"
}

function Get-IngressHost {
    Write-Step "Waiting for the application load balancer"
    for ($i = 0; $i -lt 60; $i++) {
        $hostProbe = Invoke-Probe { kubectl -n $InventoryNamespace get ingress inventory -o "jsonpath={.status.loadBalancer.ingress[0].hostname}" }
        $hostName = if ($hostProbe.ExitCode -eq 0) { $hostProbe.Output.Trim() } else { $null }
        if ($hostName) {
            return $hostName
        }
        Start-Sleep -Seconds 10
    }
    return $null
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

foreach ($command in @("aws", "terraform", "kubectl", "helm")) {
    Assert-Command $command
}

Ensure-Bootstrap

Write-Step "Applying Terraform infrastructure"
Invoke-Terraform -TerraformArgs @("-chdir=$TfDir", "init", "-input=false") -Description "terraform init failed in infra/envs/dev"
Invoke-Terraform -TerraformArgs @("-chdir=$TfDir", "apply", "-auto-approve", "-input=false") -Description "terraform apply failed in infra/envs/dev"

Ensure-KubectlAccess
Wait-ForNodes
kubectl -n kube-system rollout status deployment/ebs-csi-controller --timeout=10m
Assert-LastExitCode "EBS CSI controller did not become ready"

Install-LoadBalancerController
Ensure-Images
Ensure-InventorySecret
Ensure-ArgoCD
Ensure-Monitoring

$ingressHost = Get-IngressHost
$adminEmail = Get-K8sSecretValue -Namespace $InventoryNamespace -Name "inventory-secrets" -Key "ADMIN_EMAIL"
$adminPassword = Get-K8sSecretValue -Namespace $InventoryNamespace -Name "inventory-secrets" -Key "ADMIN_PASSWORD"
$argocdPassword = Get-K8sSecretValue -Namespace "argocd" -Name "argocd-initial-admin-secret" -Key "password"
$grafanaPassword = Get-K8sSecretValue -Namespace $MonitoringNamespace -Name "grafana-admin" -Key "admin-password"

Write-Host ""
Write-Host "Deployment complete." -ForegroundColor Green
if ($ingressHost) {
    Write-Host "Frontend:       http://$ingressHost"
} else {
    Write-Host "Frontend:       ingress hostname not ready yet; run: kubectl -n inventory get ingress inventory"
}
Write-Host "Admin email:    $adminEmail"
Write-Host "Admin password: $adminPassword"
Write-Host ""
Write-Host "ArgoCD:  kubectl -n argocd port-forward svc/argocd-server 8080:443"
if ($argocdPassword) {
    Write-Host "         https://localhost:8080  user=admin  password=$argocdPassword"
}
if (-not $SkipMonitoring) {
    Write-Host "Grafana: kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80"
    Write-Host "         http://localhost:3000  user=admin"
    if ($grafanaPassword) {
        Write-Host "         password=$grafanaPassword"
    }
    Write-Host "Prometheus: kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090"
}
