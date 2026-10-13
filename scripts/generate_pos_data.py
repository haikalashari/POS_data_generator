
import csv
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path


# ============================================================
# 1. CONFIGURATION
# ============================================================

SEED = 42

OUTLET_COUNT = 30
DAYS = 30
TRANSACTIONS_PER_OUTLET_PER_DAY = 250

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

OUTLET_PREFIX = [
    "Kopi Pagi",
    "Kopi Sudut",
    "Kedai Rasa",
    "Ruang Seduh",
    "Dapur Kita",
]

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

# Repeat and vary menu entries to create 100 products.
PRODUCTS = []

for i in range(100):
    base_name, category, base_price, base_cost = MENU[i % len(MENU)]

    variation = i // len(MENU)
    price = base_price + (variation * 1000)
    cost = base_cost + (variation * 300)

    PRODUCTS.append({
        "product_id": f"P{i + 1:03d}",
        "product_name": (
            base_name if variation == 0
            else f"{base_name} - Variant {variation + 1}"
        ),
        "category": category,
        "unit_price": price,
        "unit_cost": cost,
    })


def generate_outlets():
    outlets = []

    for i in range(OUTLET_COUNT):
        outlet_id = f"O{i + 1:03d}"
        prefix = OUTLET_PREFIX[i % len(OUTLET_PREFIX)]

        outlets.append({
            "outlet_id": outlet_id,
            "outlet_name": f"{prefix} {i + 1:02d}",
            "city": CITIES[i % len(CITIES)],
        })

    return outlets


# ============================================================
# 3. CSV HELPER
# ============================================================

def write_csv(file_path, fieldnames, rows):
    """Write dictionaries to a CSV file."""
    with file_path.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ============================================================
# 4. TRANSACTION GENERATOR
# ============================================================

def random_transaction_time(transaction_date):
    """
    Generate a transaction time between 08:00 and 22:59.
    Lunch and evening hours are more likely to be busy.
    """
    hour_weights = [
        1, 1, 2, 3, 4, 5,  # 08:00-13:59
        3, 2, 2, 3, 5, 5,  # 14:00-19:59
        4, 3, 2,            # 20:00-22:59
    ]

    hour = rng.choices(
        population=list(range(8, 23)),
        weights=hour_weights,
        k=1,
    )[0]

    minute = rng.randint(0, 59)
    second = rng.randint(0, 59)

    return datetime.combine(
        transaction_date,
        time(hour, minute, second),
    )


def generate_data(outlets):
    transactions = []
    transaction_items = []
    payments = []

    transaction_number = 1
    item_number = 1
    payment_number = 1

    payment_methods = ["QRIS", "Cash", "Debit", "E-Wallet"]
    payment_weights = [50, 20, 15, 15]

    for day_offset in range(DAYS):
        transaction_date = START_DATE + timedelta(days=day_offset)

        for outlet in outlets:
            for _ in range(TRANSACTIONS_PER_OUTLET_PER_DAY):

                transaction_id = f"T{transaction_number:08d}"
                transaction_number += 1

                transaction_time = random_transaction_time(
                    transaction_date
                )

                order_type = rng.choices(
                    ["Dine-in", "Takeaway"],
                    weights=[45, 55],
                    k=1,
                )[0]

                payment_method = rng.choices(
                    payment_methods,
                    weights=payment_weights,
                    k=1,
                )[0]

                # One order contains between 1 and 4 different items.
                number_of_items = rng.randint(1, 4)

                selected_products = rng.sample(
                    PRODUCTS,
                    number_of_items,
                )

                transaction_total = 0
                transaction_cost = 0

                for product in selected_products:
                    quantity = rng.randint(1, 3)
                    unit_price = product["unit_price"]
                    unit_cost = product["unit_cost"]

                    gross_amount = quantity * unit_price

                    # Normal discount: 0%, 5%, or 10%.
                    discount_rate = rng.choice([0, 0, 0, 5, 10])
                    discount_amount = (
                        gross_amount * discount_rate // 100
                    )

                    line_total = gross_amount - discount_amount
                    line_cost = quantity * unit_cost

                    transaction_total += line_total
                    transaction_cost += line_cost

                    transaction_items.append({
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

                transactions.append({
                    "transaction_id": transaction_id,
                    "outlet_id": outlet["outlet_id"],
                    "transaction_time": transaction_time.isoformat(
                        sep=" "
                    ),
                    "order_type": order_type,
                    "payment_method": payment_method,
                    "status": "COMPLETED",
                    "total_amount": transaction_total,
                })

                payments.append({
                    "payment_id": f"PAY{payment_number:08d}",
                    "transaction_id": transaction_id,
                    "payment_method": payment_method,
                    "paid_amount": transaction_total,
                    "payment_status": "PAID",
                })

                payment_number += 1

    return transactions, transaction_items, payments


# ============================================================
# 5. VALIDATION
# ============================================================

def validate_data(transactions, transaction_items, payments):
    transaction_totals = {
        row["transaction_id"]: row["total_amount"]
        for row in transactions
    }

    item_totals = {}

    for row in transaction_items:
        transaction_id = row["transaction_id"]

        item_totals[transaction_id] = (
            item_totals.get(transaction_id, 0)
            + row["line_total"]
        )

    payment_totals = {
        row["transaction_id"]: row["paid_amount"]
        for row in payments
    }

    assert len(transaction_totals) == len(transactions), (
        "Duplicate transaction IDs found."
    )

    assert set(transaction_totals) == set(item_totals), (
        "Transactions and items do not match."
    )

    assert set(transaction_totals) == set(payment_totals), (
        "Transactions and payments do not match."
    )

    for transaction_id, total in transaction_totals.items():
        assert total == item_totals[transaction_id], (
            f"Item total mismatch: {transaction_id}"
        )

        assert total == payment_totals[transaction_id], (
            f"Payment mismatch: {transaction_id}"
        )

    print("Validation passed:")
    print("- Transaction IDs are unique.")
    print("- Every transaction has item records.")
    print("- Every transaction has a payment record.")
    print("- Transaction totals match item totals.")
    print("- Transaction totals match payment amounts.")


# ============================================================
# 6. MAIN
# ============================================================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    outlets = generate_outlets()

    write_csv(
        OUTPUT_DIR / "outlets.csv",
        ["outlet_id", "outlet_name", "city"],
        outlets,
    )

    write_csv(
        OUTPUT_DIR / "products.csv",
        [
            "product_id",
            "product_name",
            "category",
            "unit_price",
            "unit_cost",
        ],
        PRODUCTS,
    )

    transactions, items, payments = generate_data(outlets)

    write_csv(
        OUTPUT_DIR / "transactions.csv",
        [
            "transaction_id",
            "outlet_id",
            "transaction_time",
            "order_type",
            "payment_method",
            "status",
            "total_amount",
        ],
        transactions,
    )

    write_csv(
        OUTPUT_DIR / "transaction_items.csv",
        [
            "transaction_id",
            "item_id",
            "product_id",
            "quantity",
            "unit_price",
            "discount_amount",
            "line_total",
            "line_cost",
        ],
        items,
    )

    write_csv(
        OUTPUT_DIR / "payments.csv",
        [
            "payment_id",
            "transaction_id",
            "payment_method",
            "paid_amount",
            "payment_status",
        ],
        payments,
    )

    validate_data(transactions, items, payments)

    print("\nGeneration completed.")
    print(f"Outlets: {len(outlets):,}")
    print(f"Products: {len(PRODUCTS):,}")
    print(f"Transactions: {len(transactions):,}")
    print(f"Transaction items: {len(items):,}")
    print(f"Payments: {len(payments):,}")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
