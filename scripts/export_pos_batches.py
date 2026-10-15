"""Split clean POS CSVs into outlet-daily batches and inject known data issues.

Expected project layout:
    project/
      data/reference/
      data/pos_exports/
      scripts/export_pos_batches.py

Only the generated incoming/ and manifests/ output is rebuilt on each run.
The quarantine/ directory is left untouched because the ETL pipeline may use it.
"""

import csv
import json
import random
import shutil
from collections import defaultdict
from pathlib import Path


# ============================================================
# 1. CONFIGURATION
# ============================================================

SEED = 99
ANOMALY_RATE = 0.02  # 2% of original transaction IDs receive one injected issue.

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE_DIR = BASE_DIR / "data" / "reference"
EXPORT_DIR = BASE_DIR / "data" / "pos_exports"
INCOMING_DIR = EXPORT_DIR / "incoming"
QUARANTINE_DIR = EXPORT_DIR / "quarantine"
MANIFEST_DIR = EXPORT_DIR / "manifests"
rng = random.Random(SEED)

FILE_NAMES = {
    "transactions": "transactions.csv",
    "items": "transaction_items.csv",
    "payments": "payments.csv",
}


def read_csv(path):
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ============================================================
# 2. LOAD AND CHECK SOURCE DATA
# ============================================================

def load_source_data():
    transactions = read_csv(SOURCE_DIR / "transactions.csv")
    items = read_csv(SOURCE_DIR / "transaction_items.csv")
    payments = read_csv(SOURCE_DIR / "payments.csv")
    products = read_csv(SOURCE_DIR / "products.csv")

    transaction_ids = [row["transaction_id"] for row in transactions]
    if len(transaction_ids) != len(set(transaction_ids)):
        raise ValueError("Reference transactions.csv has duplicate transaction_id values.")

    transaction_lookup = {row["transaction_id"]: row for row in transactions}
    for table_name, rows in (("transaction_items.csv", items), ("payments.csv", payments)):
        for row in rows:
            if row["transaction_id"] not in transaction_lookup:
                raise ValueError(
                    f"{table_name} references unknown transaction_id "
                    f"{row['transaction_id']}"
                )

    valid_product_ids = {row["product_id"] for row in products}
    if not valid_product_ids:
        raise ValueError("products.csv has no product records.")

    return transactions, items, payments, valid_product_ids


# ============================================================
# 3. GROUP RECORDS INTO OUTLET-DAILY BATCHES
# ============================================================

def group_by_batch(transactions, items, payments):
    transaction_lookup = {row["transaction_id"]: row for row in transactions}
    batches = defaultdict(lambda: {"transactions": [], "items": [], "payments": []})

    for row in transactions:
        batch_date = row["transaction_time"][:10]
        batches[(row["outlet_id"], batch_date)]["transactions"].append(dict(row))

    for row in items:
        transaction = transaction_lookup[row["transaction_id"]]
        batch_date = transaction["transaction_time"][:10]
        key = (transaction["outlet_id"], batch_date)
        batches[key]["items"].append(dict(row))

    for row in payments:
        transaction = transaction_lookup[row["transaction_id"]]
        batch_date = transaction["transaction_time"][:10]
        key = (transaction["outlet_id"], batch_date)
        batches[key]["payments"].append(dict(row))

    return batches


# ============================================================
# 4. CONTROLLED ANOMALY INJECTION
# ============================================================

def inject_anomalies(batches, valid_product_ids):
    original_transaction_ids = [
        row["transaction_id"]
        for batch in batches.values()
        for row in batch["transactions"]
    ]
    target_count = round(len(original_transaction_ids) * ANOMALY_RATE)
    selected_ids = set(rng.sample(original_transaction_ids, target_count))

    anomaly_types = [
        "PAYMENT_MISMATCH",
        "INVALID_PRODUCT_ID",
        "INVALID_QUANTITY",
        "DUPLICATE_TRANSACTION",
    ]
    invalid_product_id = "P999999"
    while invalid_product_id in valid_product_ids:
        invalid_product_id += "X"

    ground_truth = []

    for (outlet_id, batch_date), batch in batches.items():
        # Iterate over a snapshot. Otherwise, a newly appended duplicate could be
        # processed again and create duplicates indefinitely.
        for transaction in list(batch["transactions"]):
            transaction_id = transaction["transaction_id"]
            if transaction_id not in selected_ids:
                continue

            anomaly_type = rng.choice(anomaly_types)
            ground_truth.append({
                "transaction_id": transaction_id,
                "outlet_id": outlet_id,
                "batch_date": batch_date,
                "anomaly_type": anomaly_type,
            })

            if anomaly_type == "PAYMENT_MISMATCH":
                payment = next(
                    row for row in batch["payments"]
                    if row["transaction_id"] == transaction_id
                )
                payment["paid_amount"] = str(int(payment["paid_amount"]) + 5000)

            elif anomaly_type == "INVALID_PRODUCT_ID":
                item = next(
                    row for row in batch["items"]
                    if row["transaction_id"] == transaction_id
                )
                item["product_id"] = invalid_product_id

            elif anomaly_type == "INVALID_QUANTITY":
                item = next(
                    row for row in batch["items"]
                    if row["transaction_id"] == transaction_id
                )
                item["quantity"] = "-1"

            elif anomaly_type == "DUPLICATE_TRANSACTION":
                batch["transactions"].append(dict(transaction))

    return ground_truth


# ============================================================
# 5. EXPORT BATCH FILES AND MANIFESTS
# ============================================================

def export_batches(batches):
    manifest = []
    fieldnames = {
        "transactions": ["transaction_id", "outlet_id", "transaction_time", "order_type", "total_amount"],
        "items": ["transaction_id", "item_id", "product_id", "quantity", "unit_price", "discount_amount", "line_total", "line_cost"],
        "payments": ["payment_id", "transaction_id", "payment_method", "paid_amount"],
    }

    for (outlet_id, batch_date), batch in sorted(batches.items()):
        batch_dir = INCOMING_DIR / f"outlet_{outlet_id}" / batch_date

        for key, filename in FILE_NAMES.items():
            output_path = batch_dir / filename
            rows = batch[key]
            write_csv(output_path, fieldnames[key], rows)
            manifest.append({
                "outlet_id": outlet_id,
                "batch_date": batch_date,
                "file_name": filename,
                "record_count": len(rows),
                "file_path": str(output_path.relative_to(BASE_DIR)),
            })

    write_csv(
        MANIFEST_DIR / "batch_manifest.csv",
        ["outlet_id", "batch_date", "file_name", "record_count", "file_path"],
        manifest,
    )
    return manifest


def main():
    # Avoid stale batches if the number of outlets or date range changes.
    for directory in (INCOMING_DIR, MANIFEST_DIR):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    transactions, items, payments, valid_product_ids = load_source_data()
    batches = group_by_batch(transactions, items, payments)
    ground_truth = inject_anomalies(batches, valid_product_ids)
    manifest = export_batches(batches)

    write_csv(
        MANIFEST_DIR / "ground_truth_anomalies.csv",
        ["transaction_id", "outlet_id", "batch_date", "anomaly_type"],
        ground_truth,
    )

    anomaly_types = [
        "PAYMENT_MISMATCH",
        "INVALID_PRODUCT_ID",
        "INVALID_QUANTITY",
        "DUPLICATE_TRANSACTION",
    ]
    summary = {
        "source_transactions": len(transactions),
        "source_items": len(items),
        "source_payments": len(payments),
        "batches": len(batches),
        "exported_files": len(manifest),
        "target_anomaly_rate": ANOMALY_RATE,
        "injected_anomalies": len(ground_truth),
        "anomaly_types": {
            anomaly_type: sum(row["anomaly_type"] == anomaly_type for row in ground_truth)
            for anomaly_type in anomaly_types
        },
    }
    with (MANIFEST_DIR / "run_summary.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    print("Export completed.")
    print(json.dumps(summary, indent=2))
    print(f"Incoming directory: {INCOMING_DIR}")
    print(f"Manifest directory: {MANIFEST_DIR}")


if __name__ == "__main__":
    main()
