import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_ecommerce_dataset(num_customers=200, num_transactions=2500):
    """
    Generates synthetic transactional historical logs to feed the analytical ETL pipeline
    Models specific behavioral archetypes (VIP, Dormant, Occasional) to enable pattern testing
    """
    print("Initialing synthetic data generation process...")

    customers = [f"USER_{str(i).zfill(4)}" for i in range(1, num_customers + 1)]
    start_date = datetime(2025, 6, 1)
    raw_records = []

    # Isolate specific user groups to enforce distinct behavioral clusters
    vip_group = customers[:20]
    dormant_group = customers[20:50]

    for index in range(num_transactions):
        invoice_id = f"INV-{10000 + index}"
        probability = random.random()

        if probability < 0.3:
            customer_id = random.choice(vip_group)
            amount = round(random.uniform(80.0, 350.0), 2)
            extra_days = random.randint(0, 365)
        elif probability < 0.5:
            customer_id = random.choice(dormant_group)
            amount = round(random.uniform(30.0, 150.0), 2)
            extra_days = random.randint(0, 120)
        else:
            customer_id = random.choice(customers)
            amount = round(random.uniform(10.0, 120.0), 2)
            extra_days = random.randint(0, 365)

        invoice_date = start_date + timedelta(days=extra_days, hours=random.randint(0, 23), minutes=random.randint(0, 59))

        raw_records.append({
            "invoice_id": invoice_id,
            "customer_id": customer_id,
            "invoice_date": invoice_date,
            "amount": amount,
            "status": "completed" if random.random() > 0.3 else "cancelled"
        })

    # Construct DataFrame, sort chronologically and persist to local storage
    dataset_frame = pd.DataFrame(raw_records)
    dataset_frame = dataset_frame.sort_values(by="invoice_date").reset_index(drop=True)
    dataset_frame.to_csv("historical_transactions.csv", index=False)

    print("Dataset generation completed. Target file 'historical_transactions.csv' persisted successfully")

if __name__ == "__main__":
    generate_ecommerce_dataset()