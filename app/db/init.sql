-- Inventory Management — schema + seed
-- Executed automatically by the Postgres container on first start.

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(16) NOT NULL DEFAULT 'viewer'
                  CHECK (role IN ('admin', 'manager', 'viewer')),
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(120) UNIQUE NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS suppliers (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(160) UNIQUE NOT NULL,
    contact_name VARCHAR(120),
    email        VARCHAR(200),
    phone        VARCHAR(40),
    country      VARCHAR(80),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS products (
    id             SERIAL PRIMARY KEY,
    sku            VARCHAR(64) UNIQUE NOT NULL,
    name           VARCHAR(200) NOT NULL,
    description    TEXT,
    category_id    INT REFERENCES categories(id) ON DELETE SET NULL,
    supplier_id    INT REFERENCES suppliers(id) ON DELETE SET NULL,
    unit_price     NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (unit_price >= 0),
    cost_price     NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (cost_price >= 0),
    stock_quantity INT NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    reorder_level  INT NOT NULL DEFAULT 10 CHECK (reorder_level >= 0),
    created_by     INT REFERENCES users(id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products (category_id);
CREATE INDEX IF NOT EXISTS idx_products_supplier ON products (supplier_id);
CREATE INDEX IF NOT EXISTS idx_products_name ON products (lower(name));
CREATE INDEX IF NOT EXISTS idx_products_low_stock
    ON products (stock_quantity)
    WHERE stock_quantity <= reorder_level;

CREATE TABLE IF NOT EXISTS stock_movements (
    id         BIGSERIAL PRIMARY KEY,
    product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    change_qty INT NOT NULL,
    reason     VARCHAR(24) NOT NULL
               CHECK (reason IN ('RESTOCK', 'SALE', 'ADJUSTMENT', 'IMPORT', 'DELETE')),
    note       TEXT,
    created_by INT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_stock_movements_product ON stock_movements (product_id);

CREATE TABLE IF NOT EXISTS catalog_requests (
    id           SERIAL PRIMARY KEY,
    kind         VARCHAR(16) NOT NULL CHECK (kind IN ('category', 'supplier')),
    name         VARCHAR(160) NOT NULL,
    status       VARCHAR(16) NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending', 'approved', 'rejected')),
    requested_by INT REFERENCES users(id) ON DELETE SET NULL,
    reviewed_by  INT REFERENCES users(id) ON DELETE SET NULL,
    note         TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_at  TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_catalog_requests_pending
    ON catalog_requests (kind, lower(name))
    WHERE status = 'pending';

-- ---------------------------------------------------------------------------
-- Seed data
-- Files live in the container at /docker-entrypoint-initdb.d/seed/.
-- Replace products.csv with the output of scripts/seed/adapt_ccby_grocery.py.
-- ---------------------------------------------------------------------------

COPY categories (name, description)
    FROM '/docker-entrypoint-initdb.d/seed/categories.csv'
    WITH (FORMAT csv, HEADER true);

COPY suppliers (name, contact_name, email, phone, country)
    FROM '/docker-entrypoint-initdb.d/seed/suppliers.csv'
    WITH (FORMAT csv, HEADER true);

CREATE TEMP TABLE products_stage (
    sku            VARCHAR(64),
    name           VARCHAR(200),
    description    TEXT,
    category       VARCHAR(120),
    supplier       VARCHAR(160),
    unit_price     NUMERIC(12, 2),
    cost_price     NUMERIC(12, 2),
    stock_quantity INT,
    reorder_level  INT
);

COPY products_stage (sku, name, description, category, supplier, unit_price,
                     cost_price, stock_quantity, reorder_level)
    FROM '/docker-entrypoint-initdb.d/seed/products.csv'
    WITH (FORMAT csv, HEADER true);

INSERT INTO products (
    sku, name, description, category_id, supplier_id,
    unit_price, cost_price, stock_quantity, reorder_level
)
SELECT
    s.sku,
    s.name,
    s.description,
    c.id,
    sup.id,
    s.unit_price,
    s.cost_price,
    s.stock_quantity,
    s.reorder_level
FROM products_stage s
LEFT JOIN categories c ON lower(c.name) = lower(trim(s.category))
LEFT JOIN suppliers sup ON lower(sup.name) = lower(trim(s.supplier))
ON CONFLICT (sku) DO NOTHING;

DROP TABLE products_stage;
