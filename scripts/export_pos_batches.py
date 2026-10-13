
import csv
import random
import json
from collections import defaultdict
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

SEED = 99
ANOMALY_RATE = 0.02

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


# ============================================================
# CSV HELPERS
# ============================================================

def read_csv(path):
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        return

    with path.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


# ============================================================
# LOAD BASELINE DATA
# ============================================================

def load_source_data():
    transactions = read_csv(SOURCE_DIR / "transactions.csv")
    items = read_csv(SOURCE_DIR / "transaction_items.csv")
    payments = read_csv(SOURCE_DIR / "payments.csv")
    products = read_csv(SOURCE_DIR / "products.csv")

    valid_product_ids = {
        row["product_id"] for row in products
    }

    return transactions, items, payments, valid_product_ids


# ============================================================
# GROUP RECORDS INTO OUTLET-DAILY BATCHES
# ============================================================

def group_by_batch(transactions, items, payments):
    transaction_lookup = {
        row["transaction_id"]: row for row in transactions
    }

    batches = defaultdict(
        lambda: {
            "transactions": [],
            "items": [],
            "payments": [],
        }
    )

    for row in transactions:
        batch_date = row["transaction_time"][:10]
        key = (row["outlet_id"], batch_date)
        batches[key]["transactions"].append(dict(row))

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
# CONTROLLED ANOMALY INJECTION
# ============================================================

def inject_anomalies(batches, valid_product_ids):
    all_transaction_ids = [
        row["transaction_id"]
        for batch in batches.values()
        for row in batch["transactions"]
    ]

    target_count = round(
        len(all_transaction_ids) * ANOMALY_RATE
    )

    selected_ids = set(
        rng.sample(all_transaction_ids, target_count)
    )

    anomaly_types = [
        "PAYMENT_MISMATCH",
        "INVALID_PRODUCT_ID",
        "INVALID_QUANTITY",
        "DUPLICATE_TRANSACTION",
    ]

    ground_truth = []

    for (outlet_id, batch_date), batch in batches.items():
        for transaction in batch["transactions"]:
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
                for payment in batch["payments"]:
                    if payment["transaction_id"] == transaction_id:
                        payment["paid_amount"] = str(
                            int(payment["paid_amount"]) + 5000
                        )
                        break

            elif anomaly_type == "INVALID_PRODUCT_ID":
                for item in batch["items"]:
                    if item["transaction_id"] == transaction_id:
                        item["product_id"] = "P999999"
                        break

            elif anomaly_type == "INVALID_QUANTITY":
                for item in batch["items"]:
                    if item["transaction_id"] == transaction_id:
                        item["quantity"] = "-1"
                        break

            elif anomaly_type == "DUPLICATE_TRANSACTION":
                original = next(
                    row for row in batch["transactions"]
                    if row["transaction_id"] == transaction_id
                )
                batch["transactions"].append(dict(original))

    return ground_truth


# ============================================================
# EXPORT BATCH FILES
# ============================================================

def export_batches(batches):
    manifest = []

    for (outlet_id, batch_date), batch in sorted(batches.items()):
        batch_dir = (
            INCOMING_DIR
            / f"outlet_{outlet_id}"
            / batch_date
        )

        for key, filename in FILE_NAMES.items():
            output_path = batch_dir / filename
            rows = batch[key]
            write_csv(output_path, rows)

            manifest.append({
                "outlet_id": outlet_id,
                "batch_date": batch_date,
                "file_name": filename,
                "record_count": len(rows),
                "file_path": str(output_path.relative_to(BASE_DIR)),
            })

    write_csv(
        MANIFEST_DIR / "batch_manifest.csv",
        manifest,
    )

    return manifest


# ============================================================
# MAIN
# ============================================================

def main():
    for directory in [
        INCOMING_DIR,
        QUARANTINE_DIR,
        MANIFEST_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    transactions, items, payments, valid_product_ids = (
        load_source_data()
    )

    batches = group_by_batch(
        transactions,
        items,
        payments,
    )

    ground_truth = inject_anomalies(
        batches,
        valid_product_ids,
    )

    manifest = export_batches(batches)

    write_csv(
        MANIFEST_DIR / "ground_truth_anomalies.csv",
        ground_truth,
    )

    summary = {
        "source_transactions": len(transactions),
        "source_items": len(items),
        "source_payments": len(payments),
        "batches": len(batches),
        "exported_files": len(manifest),
        "target_anomaly_rate": ANOMALY_RATE,
        "injected_anomalies": len(ground_truth),
        "anomaly_types": {
            anomaly_type: sum(
                row["anomaly_type"] == anomaly_type
                for row in ground_truth
            )
            for anomaly_type in [
                "PAYMENT_MISMATCH",
                "INVALID_PRODUCT_ID",
                "INVALID_QUANTITY",
                "DUPLICATE_TRANSACTION",
            ]
        },
    }

    with (MANIFEST_DIR / "run_summary.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(summary, file, indent=2)

    print("Export completed.")
    print(json.dumps(summary, indent=2))
    print(f"\nIncoming directory: {INCOMING_DIR}")
    print(f"Manifest directory: {MANIFEST_DIR}")


if __name__ == "__main__":
    main()
