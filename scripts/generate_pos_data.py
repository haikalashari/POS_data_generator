"""Generate clean synthetic POS reference data for a small cafe chain.

Expected project layout:
    project/
      data/reference/
      scripts/generate_pos_data.py

Business assumptions:
- Every transaction represents a completed sale.
- Every transaction has one or more item rows.
- Every transaction has exactly one payment record.
- Payment method is stored only in payments.csv, not transactions.csv.
- Transaction total is the sum of item line totals; paid_amount matches it.
- Data-quality anomalies are injected later by export_pos_batches.py.
"""

import csv
import random
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path


# ============================================================
# 1. CONFIGURATION
# ============================================================

SEED = 42
OUTLET_COUNT = 10
DAYS = 30
TRANSACTIONS_PER_OUTLET_PER_DAY = 50
START_DATE = date(2026, 9, 1)

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "reference"
rng = random.Random(SEED)


# ============================================================
# 2. MASTER DATA
# ============================================================

CITIES = [
    "Pontianak",
    "Singkawang",
    "Mempawah",
    "Kubu Raya",
    "Sambas",
]

OUTLET_PREFIXES = [
    "Kopi Pagi",
    "Kopi Sudut",
    "Kedai Rasa",
    "Ruang Seduh",
    "Dapur Kita",
]

# Keep one record per real menu item. Do not create artificial variants.
MENU = [
    ("Espresso", "Coffee", 12000, 4000),
    ("Americano", "Coffee", 16000, 5000),
    ("Cafe Latte", "Coffee", 22000, 8000),
    ("Cappuccino", "Coffee", 22000, 7500),
    ("Caramel Latte", "Coffee", 26000, 9500),
    ("Vanilla Latte", "Coffee", 26000, 9000),
    ("Mocha", "Coffee", 25000, 9000),
    ("Kopi Susu Gula Aren", "Coffee", 20000, 7000),
    ("Cold Brew", "Coffee", 22000, 7500),
    ("Matcha Latte", "Non-Coffee", 25000, 9500),
    ("Chocolate", "Non-Coffee", 22000, 8000),
    ("Red Velvet", "Non-Coffee", 24000, 8500),
    ("Taro Latte", "Non-Coffee", 23000, 8000),
    ("Lemon Tea", "Tea", 15000, 4500),
    ("Peach Tea", "Tea", 18000, 5500),
    ("Lychee Tea", "Tea", 18000, 5500),
    ("Thai Tea", "Tea", 18000, 6000),
    ("Green Tea", "Tea", 16000, 5000),
    ("French Fries", "Snack", 18000, 7000),
    ("Chicken Nuggets", "Snack", 20000, 8500),
    ("Roti Bakar", "Snack", 18000, 6500),
    ("Pisang Goreng", "Snack", 16000, 5500),
    ("Donut", "Snack", 10000, 3500),
    ("Croissant", "Snack", 18000, 7500),
    ("Chicken Rice Bowl", "Meal", 30000, 14000),
    ("Beef Rice Bowl", "Meal", 38000, 19000),
    ("Chicken Sandwich", "Meal", 28000, 13000),
    ("Spaghetti Bolognese", "Meal", 35000, 16000),
    ("Fried Rice", "Meal", 28000, 12000),
    ("Chicken Burger", "Meal", 32000, 15000),
]

PAYMENT_METHODS = ["QRIS", "E-Wallet", "Cash", "Debit"]
PAYMENT_WEIGHTS = [50, 15, 20, 15]
ORDER_TYPES = ["Dine-in", "Takeaway"]
ORDER_TYPE_WEIGHTS = [45, 55]


def generate_outlets():
    return [
        {
            "outlet_id": f"O{i + 1:03d}",
            "outlet_name": f"{OUTLET_PREFIXES[i % len(OUTLET_PREFIXES)]} {i + 1:02d}",
            "city": CITIES[i % len(CITIES)],
        }
        for i in range(OUTLET_COUNT)
    ]


def generate_products():
    return [
        {
            "product_id": f"P{i + 1:03d}",
            "product_name": name,
            "category": category,
            "unit_price": price,
            "unit_cost": cost,
        }
        for i, (name, category, price, cost) in enumerate(MENU)
    ]


# ============================================================
# 3. CSV HELPERS
# ============================================================

def write_csv(file_path, fieldnames, rows):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def random_transaction_time(transaction_date):
    """Generate a time from 08:00 to 22:59, with busier meal periods."""
    hours = list(range(8, 23))
    hour_weights = [1, 1, 2, 3, 4, 5, 3, 2, 2, 3, 5, 5, 4, 3, 2]
    hour = rng.choices(hours, weights=hour_weights, k=1)[0]
    return datetime.combine(
        transaction_date,
        time(hour, rng.randint(0, 59), rng.randint(0, 59)),
    )


# ============================================================
# 4. TRANSACTION GENERATION
# ============================================================

def generate_data(outlets, products):
    transactions = []
    items = []
    payments = []

    transaction_number = 1
    item_number = 1
    payment_number = 1

    for day_offset in range(DAYS):
        transaction_date = START_DATE + timedelta(days=day_offset)

        for outlet in outlets:
            for _ in range(TRANSACTIONS_PER_OUTLET_PER_DAY):
                transaction_id = f"T{transaction_number:08d}"
                transaction_number += 1
                transaction_time = random_transaction_time(transaction_date)
                order_type = rng.choices(
                    ORDER_TYPES, weights=ORDER_TYPE_WEIGHTS, k=1
                )[0]

                # A transaction contains 1-4 distinct products.
                selected_products = rng.sample(products, rng.randint(1, 4))
                transaction_total = 0

                for product in selected_products:
                    quantity = rng.randint(1, 3)
                    unit_price = product["unit_price"]
                    unit_cost = product["unit_cost"]
                    gross_amount = quantity * unit_price
                    discount_rate = rng.choice([0, 0, 0, 5, 10])
                    discount_amount = gross_amount * discount_rate // 100
                    line_total = gross_amount - discount_amount
                    line_cost = quantity * unit_cost
                    transaction_total += line_total

                    items.append({
                        "transaction_id": transaction_id,
                        "item_id": f"I{item_number:09d}",
                        "product_id": product["product_id"],
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "discount_amount": discount_amount,
                        "line_total": line_total,
                        "line_cost": line_cost,
                    })
                    item_number += 1

                # This dataset covers completed sales only. Status columns are
                # omitted until the business case includes cancelled/pending sales.
                transactions.append({
                    "transaction_id": transaction_id,
                    "outlet_id": outlet["outlet_id"],
                    "transaction_time": transaction_time.isoformat(sep=" "),
                    "order_type": order_type,
                    "total_amount": transaction_total,
                })

                # One payment per transaction is an explicit simplification.
                payment_method = rng.choices(
                    PAYMENT_METHODS, weights=PAYMENT_WEIGHTS, k=1
                )[0]
                payments.append({
                    "payment_id": f"PAY{payment_number:08d}",
                    "transaction_id": transaction_id,
                    "payment_method": payment_method,
                    "paid_amount": transaction_total,
                })
                payment_number += 1

    return transactions, items, payments


# ============================================================
# 5. VALIDATE GENERATED DATA
# ============================================================

def validate_data(transactions, items, payments, products):
    transaction_ids = [row["transaction_id"] for row in transactions]
    item_ids = [row["item_id"] for row in items]
    payment_ids = [row["payment_id"] for row in payments]

    assert len(transaction_ids) == len(set(transaction_ids)), "Duplicate transaction_id."
    assert len(item_ids) == len(set(item_ids)), "Duplicate item_id."
    assert len(payment_ids) == len(set(payment_ids)), "Duplicate payment_id."

    transaction_by_id = {row["transaction_id"]: row for row in transactions}
    known_transaction_ids = set(transaction_by_id)
    known_product_ids = {row["product_id"] for row in products}
    item_counts = Counter(row["transaction_id"] for row in items)
    payment_counts = Counter(row["transaction_id"] for row in payments)
    item_totals = defaultdict(int)
    payment_by_transaction = {}

    for item in items:
        assert item["transaction_id"] in known_transaction_ids, "Item has unknown transaction_id."
        assert item["product_id"] in known_product_ids, "Item has unknown product_id."
        assert item["quantity"] > 0, "Item quantity must be positive."
        assert item["line_total"] == item["quantity"] * item["unit_price"] - item["discount_amount"]
        item_totals[item["transaction_id"]] += item["line_total"]

    for payment in payments:
        assert payment["transaction_id"] in known_transaction_ids, "Payment has unknown transaction_id."
        payment_by_transaction[payment["transaction_id"]] = payment

    assert set(item_counts) == known_transaction_ids, "Some transactions have no items."
    assert set(payment_counts) == known_transaction_ids, "Some transactions have no payment."
    assert all(count == 1 for count in payment_counts.values()), "Expected exactly one payment per transaction."

    for transaction_id, transaction in transaction_by_id.items():
        assert transaction["total_amount"] == item_totals[transaction_id], (
            f"Item totals do not match transaction total: {transaction_id}"
        )
        assert payment_by_transaction[transaction_id]["paid_amount"] == transaction["total_amount"], (
            f"Payment amount does not match transaction total: {transaction_id}"
        )


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outlets = generate_outlets()
    products = generate_products()
    transactions, items, payments = generate_data(outlets, products)
    validate_data(transactions, items, payments, products)

    write_csv(OUTPUT_DIR / "outlets.csv", ["outlet_id", "outlet_name", "city"], outlets)
    write_csv(
        OUTPUT_DIR / "products.csv",
        ["product_id", "product_name", "category", "unit_price", "unit_cost"],
        products,
    )
    write_csv(
        OUTPUT_DIR / "transactions.csv",
        ["transaction_id", "outlet_id", "transaction_time", "order_type", "total_amount"],
        transactions,
    )
    write_csv(
        OUTPUT_DIR / "transaction_items.csv",
        ["transaction_id", "item_id", "product_id", "quantity", "unit_price", "discount_amount", "line_total", "line_cost"],
        items,
    )
    write_csv(
        OUTPUT_DIR / "payments.csv",
        ["payment_id", "transaction_id", "payment_method", "paid_amount"],
        payments,
    )

    print("Generation completed and validation passed.")
    print(f"Outlets: {len(outlets):,}")
    print(f"Products: {len(products):,}")
    print(f"Transactions: {len(transactions):,}")
    print(f"Transaction items: {len(items):,}")
    print(f"Payments: {len(payments):,}")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
