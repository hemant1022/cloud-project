# Architecture

## Application

```mermaid
flowchart LR
    User([Browser]) -->|HTTPS| FE[Frontend<br/>React + nginx]
    FE -->|REST /api| BE[Backend<br/>FastAPI + JWT]
    BE -->|SQL| DB[(PostgreSQL)]
    BE -->|writes| LOGS[(logs/<br/>combined + per run)]
```

## Data Model

```mermaid
erDiagram
    USERS ||--o{ PRODUCTS : creates
    CATEGORIES ||--o{ PRODUCTS : classifies
    SUPPLIERS ||--o{ PRODUCTS : supplies
    PRODUCTS ||--o{ STOCK_MOVEMENTS : records
    USERS ||--o{ CATALOG_REQUESTS : requests
    USERS ||--o{ CATALOG_REQUESTS : reviews

    USERS {
        int id PK
        string email
        string password_hash
        string role
        bool is_active
    }
    CATEGORIES {
        int id PK
        string name
        text description
    }
    SUPPLIERS {
        int id PK
        string name
        string contact_name
        string email
        string country
    }
    PRODUCTS {
        int id PK
        string sku
        string name
        int category_id FK
        int supplier_id FK
        numeric unit_price
        numeric cost_price
        int stock_quantity
        int reorder_level
    }
    STOCK_MOVEMENTS {
        int id PK
        int product_id FK
        int change_qty
        string reason
        int created_by FK
    }
    CATALOG_REQUESTS {
        int id PK
        string kind
        string name
        string status
        int requested_by FK
        int reviewed_by FK
    }
```

Derived values (never stored): `inventory_value = unit_price * stock_quantity`,
`is_low_stock = stock_quantity <= reorder_level`, `deficit = reorder_level - stock_quantity`.

## API Surface

| Area | Endpoints |
| --- | --- |
| Auth | `/api/auth/login`, `/api/auth/me`, `/api/auth/users` (admin) |
| Products | `/api/products` (search, filters, pagination), `/api/products/{id}/adjust` |
| Catalog | `/api/categories`, `/api/suppliers` (writes = admin) |
| Alerts | `/api/alerts/low-stock`, `/api/alerts/summary` |
| Stats | `/api/stats/summary` |
| Import | `/api/import/template`, `/api/import` |
| Approvals | `/api/catalog-requests`, `/{id}/approve`, `/{id}/reject` |

## Auth and Approval Flow

```mermaid
sequenceDiagram
    participant M as Manager
    participant A as Admin
    participant API as FastAPI
    participant DB as PostgreSQL

    M->>API: POST /api/import (CSV)
    API->>DB: validate rows
    API->>DB: create catalog_request (unknown category/supplier)
    API-->>M: failed rows + requests_created
    A->>API: POST /catalog-requests/{id}/approve
    API->>DB: create category/supplier
    M->>API: re-upload CSV
    API->>DB: upsert products
    API-->>M: inserted/updated summary
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
            NAT[NAT Gateway]
            LB[Load Balancer]
            subgraph EKS["EKS Cluster"]
                ARGO[ArgoCD]
                FEP[frontend pods]
                BEP[backend pods]
                PG[(postgres)]
                MON[Prometheus + Grafana]
            end
        end
        S3[(S3 state)]
        DDB[(DynamoDB lock)]
    end
    SRC --> CI --> ECR
    CI -->|bump image tag| SRC
    ARGO -->|sync k8s/| EKS
    ECR -->|pull images| EKS
    Terraform[Terraform] --> S3
    Terraform --> DDB
    Terraform --> VPC
    LB --> FEP --> BEP --> PG
    MON -.scrapes.- EKS
```

## Environments

| Env  | Terraform path    | Kustomize overlay  | Notes |
| ---- | ----------------- | ------------------ | ----- |
| dev  | `infra/envs/dev`  | `k8s/overlays/dev` | t3.small x2, single NAT |
| prod | `infra/envs/prod` | `k8s/overlays/prod`| larger nodes, HA, more AZs |
