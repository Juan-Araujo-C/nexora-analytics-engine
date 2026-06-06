import pandas as pd
import io
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Security
from sqlalchemy.orm import Session
from . import models
from .database import engine, get_db
from datetime import datetime
from sqlalchemy import func
import csv
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
import os

# Instructs SQLAlchemy to create all defined schema tables in the PostgreSQL container if they don't exist
try:
    models.Base.metadata.create_all(bind=engine)
except Exception:
    pass

# Initialize the core FastAPI application instance
app = FastAPI(title="E-commerce Behavioral Analytics Engine", version="1.0.0")

# --- SECURITY CONFIGURATION ---
# In a real production environment, this would be hidden in an .env file
NEXORA_API_KEY = os.getenv("NEXORA_API_KEY")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    Validates the API Key sent in the request headers.
    Rejects the request if the key is missing, empty, or invalid.
    """
    # Security check: Ensure BOTH that a key was provided by the user
    # AND that it matches the server's expected key
    if api_key_header and NEXORA_API_KEY and api_key_header == NEXORA_API_KEY:
        return api_key_header
    
    # If the user sends nothing, or sends the wrong key, block them
    raise HTTPException(
        status_code=403,
        detail="Access Denied. Invalid or missing API Key"
    )


@app.get("/")
def read_root():
    """
    Performs a basic system health check
    Confirms the API service status and initial database connection availability
    """
    return {
        "status": "active",
        "service": "Behavioral Analytics Engine",
        "database": "connected" 
    }

@app.post("/upload-transactions/")
async def upload_transactions(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    ETL Endpoint to ingest historical transaction data via CSV
    Extracts the file, transforms the data via Pandas, and loads it into PostgreSQL
    """
    # Security check: Ensure the uploaded file is a CSV
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    try:
        # EXTRACT: Read the uploaded file bytes from the network
        contents = await file.read()

        # TRANSFORM: Convert the raw bytes into a Pandas DataFrame for vectorized processing
        df = pd.read_csv(io.BytesIO(contents))

        # --- 1. Process Unique Customers ---
        # Extract unique customer IDs from the DataFrame (e.g., 'USER_001')
        unique_customers = df['customer_id'].unique()

        # Query the database to find which customers alredy exist to prevent duplicates
        existing_customers = db.query(models.Customer.customer_id).all()
        existing_customer_ids = {c[0] for c in existing_customers}

        # Create a list of new Customer objects that need to be added
        new_customers = []
        for cust_id in unique_customers:
            if cust_id not in existing_customer_ids:
                new_customers.append(models.Customer(customer_id=cust_id))

        # LOAD: Save new customers to the database in bulk (faster than one by one)
        if new_customers:
            db.bulk_save_objects(new_customers)
            db.commit()
        
        # --- 2. Map Customers for Foreign Keys ---
        # We need the internal integer ID (Primary Key) to link transactions properly
        all_customers = db.query(models.Customer).all()
        customer_map = {c.customer_id: c.id for c in all_customers}

        # --- 3. Process Transactions ---
        transactions_to_insert = []
        for index, row in df.iterrows():
            # Convert the Pandas string date into a standard Python datetime object
            invoice_date = pd.to_datetime(row['invoice_date']).to_pydatetime()

            # Instantiate the ORM model for the transaction
            txn = models.Transaction(
                invoice_id=row['invoice_id'],
                invoice_date=invoice_date,
                amount=float(row['amount']),
                status=row['status'],
                customer_pk=customer_map[row['customer_id']] # Liking the Foreign Key
            )
            transactions_to_insert.append(txn)

        # LOAD: Save all 2500 transactions to PostgreSQL at once
        db.bulk_save_objects(transactions_to_insert)
        db.commit()

        return {
            "message": "File processed successfully",
            "new_customers_created": len(new_customers),
            "transactions_processed": len(transactions_to_insert)
        }
    
    except Exception as e:
        # If anything fails, rollback the transaction so the database doesn't get corrupted
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error ocurred: {str(e)}")
    
@app.post("/calculate-rfm/")
def calculate_rfm(db: Session = Depends(get_db)):
    """
    Core analytical engine endpoint
    Calculates Recency, Frequency and Monetary (RFM) scores using Pandas
    and assigns a behavioral segment label to each customer
    """

    # 1. EXTRACT: Fetch only completed transactions from the database into a Pandas DataFrame
    query = db.query(
        models.Transaction.customer_pk,
        models.Transaction.invoice_date,
        models.Transaction.amount
    ).filter(models.Transaction.status == 'completed').statement

    df = pd.read_sql(query, db.bind)

    if df.empty:
        raise HTTPException(status_code=400, detail="No data available for analysis")
    
    # 2. TRANSFORM: Calculate raw RFM metrics
    # Set a simulation 'today' date as the latest transaction + 1 day
    analysis_date = df['invoice_date'].max() + pd.Timedelta(days=1)

    rfm = df.groupby('customer_pk').agg({
        'invoice_date': lambda date: (analysis_date - date.max()).days, # Recency: Days since last purchase 
        'customer_pk': 'count',  # Frequency: Total purchases
        'amount': 'sum' # Monetary: Total spent
    }).rename(columns={
        'invoice_date': 'recency',
        'customer_pk': 'frequency',
        'amount': 'monetary'
    }).reset_index()

    # 3. TRANSFORM: Calculate RFM Scores (1 to 5) using statistical quantiles (qcut)
    # Lower recency days = higher score
    rfm['r_score'] = pd.qcut(rfm['recency'], 5, labels=[5, 4, 3, 2, 1])
    # Higher frequency/monetary = higher score. Using rank avoid duplicate edge errors
    rfm['f_score'] = pd.qcut(rfm['frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
    rfm['m_score'] = pd.qcut(rfm['monetary'], 5, labels=[1, 2, 3, 4, 5])

    # 4. TRANSFORM: Determine Behavioral Segment Label
    def assign_segment(row):
        r, f, m = row['r_score'], row['f_score'], row['m_score']

        if r == 5 and f == 5 and m == 5:
            return "Champions"
        elif r >= 4 and f >= 4:
            return "Loyal Customers"
        elif r >= 3 and f <= 3:
            return "Needs Attention"
        elif r <= 2 and f >= 3:
            return "At Risk"
        elif r <= 2 and f <= 2:
            return "Hibernating"
        else:
            return 'Potential Loyalists'

    # Apply the logic row by row
    rfm['segment_label'] = rfm.apply(assign_segment, axis=1)
    # Create a concatenated string for exact cell matching (e.g., '554')
    rfm['rfm_cell'] = rfm['r_score'].astype(str) + rfm['f_score'].astype(str) + rfm['m_score'].astype(str)

   # 5. LOAD: Save data back into PostgreSQL
   # Clear old segments first to avoid duplicates if run multiple times
    db.query(models.CustomerSegment).delete()

    segments_to_insert = []
    for _, row in rfm.iterrows():
        segment = models.CustomerSegment(
            customer_pk=row['customer_pk'],
            recency_score=int(row['r_score']),
            frequency_score=int(row['f_score']),
            monetary_score=int(row['m_score']),
            rfm_cell=row['rfm_cell'],
            segment_label=row['segment_label'],
            updated_at=datetime.utcnow()
        )
        segments_to_insert.append(segment)

    db.bulk_save_objects(segments_to_insert)
    db.commit()

    return {
        "message": "RFM Analysis completed successfully",
        "segments_calculated": len(segments_to_insert)
    }


@app.get("/analytics/summary/")
def get_analytics_summary(db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    """
    Nexora Dashboard Core: Provides a high level executive summary of customer segments
    Groups the database by behavioral labels and returns the exact count for each.
    Secured via API Key.
    """
    # 1. Query the database to count customers grouped by their segment label
    segment_counts = db.query(
        models.CustomerSegment.segment_label,
        func.count(models.CustomerSegment.id)
    ).group_by(models.CustomerSegment.segment_label).all()

    # If the database is empty, return a clean warning
    if not segment_counts:
        raise HTTPException(status_code=404, detail="No analytics data found. Please run the RFM calculation first")
    
    # 2. Format the raw database result into a clean Python dictionary
    summary = {label: count for label, count in segment_counts}

    # 3. Calculate total customers analyzed
    total_customers = sum(summary.values())

    # 4. Return the JSON payload for the Nexora frontend
    return {
        "platform": "Nexora Analytics Engine",
        "total_customers_analyzed": total_customers,
        "segment_breakdown": summary
    }


@app.get("/segments/{segment_name}")
def get_customers_by_segment(segment_name: str, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    """
    Returns a list of all customers belonging to a specific behavioral segment
    Useful for extracting targeted email list.
    Secured via API Key.
    """
    # Query to join Customer and CustomerSegment tables and filter by the label
    results = db.query(
        models.Customer.customer_id,
        models.CustomerSegment.recency_score,
        models.CustomerSegment.frequency_score,
        models.CustomerSegment.monetary_score
    ).join(
        models.CustomerSegment, models.Customer.id == models.CustomerSegment.customer_pk
    ).filter(
        models.CustomerSegment.segment_label == segment_name
    ).all()

    if not results:
        raise HTTPException(status_code=404, detail=f"No customers found for segment: {segment_name}")
    
    # Format the data into a clean list
    customers = [
        {
            "customer_id": r.customer_id,
            "r_score": r.recency_score,
            "f_score": r.frequency_score,
            "m_score": r.monetary_score
        }
        for r in results
    ]

    return {
        "segment": segment_name,
        "total_customers": len(customers),
        "customers": customers
    }

@app.get("/segments/{segment_name}/export")
def export_segment_to_csv(segment_name: str, db: Session = Depends(get_db)):
    """
    Nexora Action Engine: Exports a segment list as a downloadable CSV
    Ready to be imported into ad networks (Meta Ads) or email marketing platforms
    """

    # 1. Fetch the exact same data as the normal segment search
    results = db.query(
        models.Customer.customer_id,
        models.CustomerSegment.recency_score,
        models.CustomerSegment.frequency_score,
        models.CustomerSegment.monetary_score
    ).join(
        models.CustomerSegment, models.Customer.id == models.CustomerSegment.customer_pk
    ).filter(
        models.CustomerSegment.segment_label == segment_name
    ).all()

    if not results:
        raise HTTPException(status_code=404, detail=f"No customers found for segment: {segment_name}")
    
    # 2. Create an in-memory text buffer to hold the CSV data
    output = io.StringIO()
    writer = csv.writer(output)

    # 3. Write the CSV headers
    writer.writerow(["Customer ID", "Recency Score", "Frequency Score", "Monetary Score", "Segment"])

    # 4. Loop through the results and write each row
    for r in results:
        writer.writerow([r.customer_id, r.recency_score, r.frequency_score, r.monetary_score, segment_name])

    # 5. Reset the buffer's "cursor" back to the beginning of the file
    output.seek(0)

    # 6. Format a clean filename using the segment name (e.g, 'nexora_champions_list.csv')
    clean_filename = f"nexora_{segment_name.lower().replace(' ','_')}_list.csv"

    # 7. Stream the file directly to the user's browser for download
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={clean_filename}"}
    )


@app.get("/customers/{customer_id}")
def get_customer_details(customer_id: str, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    """
    Noxora Deep Dive: Returns the full history of a specific customer
    """
    # Find the customer
    customer_data = db.query(models.Customer).filter(models.Customer.customer_id == customer_id).first()

    if not customer_data:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Get all their transactions
    transactions = db.query(models.Transaction).filter(models.Transaction.customer_pk == customer_data.id).all()

    return {
        "customer_id": customer_data.customer_id,
        "transactions": [
            {"invoice_id": t.invoice_id, "amount": float(t.amount), "date": t.invoice_date}
            for t in transactions
        ]
    }

@app.get("/analytics/segments/{segment_name}")
def get_customers_by_segment(segment_name: str, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    """
    Retrieves a comprehensive list of customers associated with a specific RFM segment.
    Requires joining the Customer and CustomerSegment tables to resolve the segment_label.
    """
    # Perform an inner join to filter customers based on their assigned segment label
    customers = db.query(models.Customer)\
                  .join(models.CustomerSegment)\
                  .filter(models.CustomerSegment.segment_label == segment_name)\
                  .all()
    
    return {
        "segment": segment_name,
        "total_count": len(customers),
        "customers": [
            {
                "customer_id": c.customer_id,
                # Safely extract RFM scores navigating through the bi-directional relationship
                "recency": c.rfm_segments[0].recency_score if c.rfm_segments else 0,
                "frequency": c.rfm_segments[0].frequency_score if c.rfm_segments else 0,
                "monetary": float(c.rfm_segments[0].monetary_score) if c.rfm_segments else 0.0
            } for c in customers
        ]
    }