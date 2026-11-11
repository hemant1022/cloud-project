# Seed Data Attribution

The committed `products.csv` in this folder is a small placeholder so the database
starts with demo data before the adapted dataset is generated. It is not derived
from the source dataset.

To regenerate the real seed from the licensed dataset:

1. Download **Grocery Inventory and Sales Dataset** by salahuddinahmedshuvo from Kaggle:
   https://www.kaggle.com/datasets/salahuddinahmedshuvo/grocery-inventory-and-sales-dataset
2. Place the CSV in `app/db/seed/raw/` (git-ignored).
3. Run:

   ```powershell
   py -3.12 scripts/seed/adapt_ccby_grocery.py `
     --input app/db/seed/raw/Grocery_Inventory_and_Sales_Dataset.csv `
     --limit 120 --seed 42
   ```

The generated `categories.csv`, `suppliers.csv`, and `products.csv` replace the
placeholders and are licensed as follows.

## License

- Dataset: *Grocery Inventory and Sales Dataset*
- Author: salahuddinahmedshuvo (Kaggle)
- License: Creative Commons Attribution 4.0 International (CC BY 4.0)
- License text: https://creativecommons.org/licenses/by/4.0/

Changes made: rows selected and subset, columns renamed to the application schema,
`cost_price` derived as approximately 72% of `unit_price`, and descriptions added.
Attribution must be preserved when redistributing the adapted data.
