"""
Data Generator — Product Reviews (Flat File)
Generates a realistic product_reviews.csv for the landing layer.
This simulates an external flat file source (e.g., from a review aggregator).
Run: python generate_reviews.py
Output: ../configs/product_reviews.csv (to be uploaded to ADLS landing container)
"""

import csv
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
Faker.seed(77)
random.seed(77)

NUM_REVIEWS = 5000
OUTPUT_FILE = "../configs/product_reviews.csv"

# Products from both stores
STORE_A_PRODUCTS = [f"PROD-A-{i:05d}" for i in range(1, 501)]
STORE_B_PRODUCTS = [f"PB-{i:05d}" for i in range(1, 401)]
ALL_PRODUCTS = STORE_A_PRODUCTS + STORE_B_PRODUCTS

STORE_A_CUSTOMERS = [f"CUST-A-{i:05d}" for i in range(1, 2001)]
STORE_B_CUSTOMERS = [f"CB-{i:05d}" for i in range(1, 1501)]
ALL_CUSTOMERS = STORE_A_CUSTOMERS + STORE_B_CUSTOMERS

REVIEW_TEMPLATES = [
    "Great product, exactly what I needed!",
    "Quality could be better for the price.",
    "Arrived on time and works perfectly.",
    "Not as described, very disappointed.",
    "Excellent value for money, highly recommend!",
    "Average product, nothing special.",
    "Absolutely love it! Will buy again.",
    "Broke after two weeks, terrible quality.",
    "Good but shipping was too slow.",
    "Perfect gift, the recipient loved it!",
    "Decent product for everyday use.",
    "Exceeded my expectations in every way.",
    "Would not recommend, poor build quality.",
    "Best purchase I've made this year!",
    "Okay for the price, gets the job done.",
]


def random_date(start_year=2024, end_year=2025):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))


def generate():
    rows = []
    for i in range(1, NUM_REVIEWS + 1):
        product = random.choice(ALL_PRODUCTS)
        datasource = "store-a" if product.startswith("PROD-A") else "store-b"
        customer_pool = STORE_A_CUSTOMERS if datasource == "store-a" else STORE_B_CUSTOMERS
        customer = random.choice(customer_pool)

        rows.append({
            "ReviewID": f"REV-{i:06d}",
            "ProductID": product,
            "CustomerID": customer,
            "Rating": random.randint(1, 5),
            "ReviewText": random.choice(REVIEW_TEMPLATES),
            "ReviewDate": random_date().strftime("%Y-%m-%d"),
            "datasource": datasource,
        })

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Product reviews generated: {OUTPUT_FILE}")
    print(f"   Total reviews: {NUM_REVIEWS}")


if __name__ == "__main__":
    generate()
