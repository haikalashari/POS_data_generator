# Simplified POS Synthetic Data

## Business case

A small cafe chain needs a daily ETL process for sales reporting and data-quality checks. The dataset supports reporting sales and gross profit by outlet, product/category, date, order type, and payment method, while the export step injects a small, known set of data-quality problems for pipeline testing.

This is intentionally a simple first version, not a full payment-processing simulation.

## Business rules

1. There are 10 outlets across five cities, 30 products, and 30 days of sales.
2. Each transaction is a completed sale and has one or more transaction-item rows.
3. Each transaction has exactly one payment. Split tender, partial payment, refunds, and cancelled orders are out of scope for this version.
4. The payment method is stored only in `payments.csv`, not in `transactions.csv`.
5. `transactions.total_amount` equals the sum of its `transaction_items.line_total` values. This is intentional: it gives the ETL a header total to reconcile against item details.
6. `payments.paid_amount` equals `transactions.total_amount` for clean source data. This is also intentional and supports a payment reconciliation check.
7. `products.unit_price` and `products.unit_cost` are current/reference values. The `transaction_items.unit_price` and `transaction_items.line_cost` are snapshots used for historical sales and margin analysis; do not remove them just because the same kind of value exists in the product master.
8. `status` and `payment_status` are omitted in this version because every generated order is completed and every payment is paid. A constant field offers no status analysis. Add them back only when the generator models meaningful state variation.

## CSV data contract

### `outlets.csv`
- `outlet_id`: unique outlet identifier
- `outlet_name`: outlet display name
- `city`: outlet city

### `products.csv`
- `product_id`: unique product identifier
- `product_name`: menu name (one record per menu product; no artificial variants)
- `category`: product category
- `unit_price`: reference selling price
- `unit_cost`: reference unit cost

### `transactions.csv` — one row per transaction
- `transaction_id`
- `outlet_id`
- `transaction_time`
- `order_type`
- `total_amount`

### `transaction_items.csv` — one row per item line
- `transaction_id`
- `item_id`
- `product_id`
- `quantity`
- `unit_price`
- `discount_amount`
- `line_total`
- `line_cost`

### `payments.csv` — one row per payment
- `payment_id`
- `transaction_id`
- `payment_method`
- `paid_amount`

## Dataset scale

- 10 outlets
- 30 products
- 30 calendar days
- 50 transactions per outlet per day
- 15,000 transactions
- 15,000 payments
- Approximately 37,000 item rows (the exact count is deterministic with the configured seed)

## Run order

Run from a project where both scripts are in `scripts/`:

```bash
python scripts/generate_pos_data.py
python scripts/export_pos_batches.py
```

The first script writes clean reference files to `data/reference/`.
The second script splits these data into one outlet-day batch, writes files into `data/pos_exports/incoming/`, and writes manifests into `data/pos_exports/manifests/`.

## Injected data-quality issues

The export script deliberately injects issues into about 2% of transaction IDs, with one issue type per selected transaction:

- `PAYMENT_MISMATCH`: adds 5,000 to the payment amount
- `INVALID_PRODUCT_ID`: assigns an item a product ID absent from `products.csv`
- `INVALID_QUANTITY`: sets an item quantity to -1
- `DUPLICATE_TRANSACTION`: duplicates the transaction header row

`ground_truth_anomalies.csv` records the intended issue for checking the validation pipeline. These issues are injected into exported batches only; `data/reference/` remains clean. The script recreates `incoming/` and `manifests/` on each run to prevent stale batch files. It does not delete `quarantine/`.

## Deliberate limitations

- No cancelled or refunded orders
- No pending/failed payments
- No split payments
- No product price history table
- One payment method per transaction

These limitations keep the initial business case coherent. They can be added later as separate requirements instead of generating fields that are present but never vary.
