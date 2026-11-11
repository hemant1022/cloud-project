# Seed Data

`app/db/seed/*.csv` is loaded automatically by Postgres on first container start
(`app/db/init.sql`). The committed CSV is a small placeholder.

## Generate the CC BY 4.0 seed

Requires Python 3.12 and no third-party packages.

```powershell
# 1. Download the dataset manually from Kaggle and save it under app/db/seed/raw/
#    https://www.kaggle.com/datasets/salahuddinahmedshuvo/grocery-inventory-and-sales-dataset

# 2. Adapt ~120 rows (guarantees low-stock and out-of-stock rows)
py -3.12 scripts\seed\adapt_ccby_grocery.py `
  --input app\db\seed\raw\Grocery_Inventory_and_Sales_Dataset.csv `
  --limit 120 --seed 42

# 3. Reset the database volume so init.sql reloads the seed
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d --build
```

Outputs: `categories.csv`, `suppliers.csv`, `products.csv`, and an updated
`ATTRIBUTION.md`-compatible log line. See `app/db/seed/ATTRIBUTION.md`.

## Expected source columns

`Product_ID`, `Product_Name`, `Category`, `Supplier_Name`, `Unit_Price`,
`Stock_Quantity`, `Reorder_Level`. Extra columns are ignored. Currency symbols
and thousands separators in prices are stripped.
