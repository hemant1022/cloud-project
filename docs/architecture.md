# Architecture

## Application (three tiers)

```mermaid
flowchart LR
    User([Browser]) -->|HTTP| FE[Frontend<br/>React + nginx]
    FE -->|REST /api| BE[Backend<br/>FastAPI]
    BE -->|SQL 5432| DB[(PostgreSQL<br/>PVC)]
```

## AWS / Delivery

```mermaid
flowchart TB
    subgraph GitHub
        SRC[App repo]
        CI[GitHub Actions]
    end
    subgraph AWS
        ECR[(Amazon ECR)]
        subgraph VPC
            subgraph Public
                NAT[NAT Gateway]
                LB[Load Balancer]
            end
            subgraph EKS["EKS Cluster"]
                ARGO[ArgoCD]
                FE[frontend]
                BE[backend]
                PG[(postgres)]
                MON[Prometheus + Grafana]
            end
        end
        S3[(S3 state)]
        DDB[(DynamoDB lock)]
    end
    SRC --> CI --> ECR
    CI -->|bump image tag| SRC
    ARGO -->|sync| EKS
    ECR -->|pull| EKS
    Terraform[Terraform] --> S3
    Terraform --> DDB
    Terraform --> VPC
    LB --> FE --> BE --> PG
    MON -.scrapes.- EKS
```

## Request Flow

1. Browser hits the Ingress/LoadBalancer.
2. nginx serves the React build; `/api` is proxied to the backend Service.
3. FastAPI queries PostgreSQL over the cluster network.
4. Prometheus scrapes kube-state-metrics, node-exporter, and app metrics; Grafana visualizes.

## Environments

| Env  | Terraform path   | Kustomize overlay  | Notes                       |
| ---- | ---------------- | ------------------ | --------------------------- |
| dev  | `infra/envs/dev` | `k8s/overlays/dev` | t3.medium x2, single NAT    |
| prod | `infra/envs/prod`| `k8s/overlays/prod`| larger nodes, HA, more AZs  |
