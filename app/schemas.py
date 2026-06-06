from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

# ---------------------------------------------
# TRANSACTION SCHEMAS
# ---------------------------------------------

class TransactionBase(BaseModel):
    """
    Base properties shared across all Transaction schemas
    """
    invoice_id: str
    invoice_date: datetime
    amount: float
    status: str

class TransactionCreate(TransactionBase):
    """
    Schema for validating incoming transaction data (e.g, from a CSV)
    Notice we expect a string 'customer_id' from the raw data, not the internal integer PK
    """
    customer_id: str

class TransactionResponse(TransactionBase):
    """
    Schema for returining transaction data to the client
    Includes database-generated IDs
    """
    id: int
    customer_pk: int

    # This tells Pydantic to read data even if it's not a strict dict (allows reading ORM objects)
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------
# CUSTOMER SEGMENT SCHEMAS
# ---------------------------------------------

class CustomerSegmentBase(BaseModel):
    """
    Base properties for the RFM calculated segments
    """
    recency_score: int
    frequency_score: int
    monetary_score: int
    rfm_cell: str
    segment_label: str
    updated_at: datetime

class CustomerSegmentResponse(CustomerSegmentBase):
    id: int
    customer_pk: int

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------
# CUSTOMER SCHEMAS
# ---------------------------------------------

class CustomerBase(BaseModel):
    """
    Core customer identifying data
    """
    customer_id: str
    email: Optional[str] = None

class CustomerResponse(CustomerBase):
    """
    Comprehensive customer profile, including nested relationships
    for their transaction history and behavioral segments
    """
    id: int
    created_at: Optional[datetime] = None

    # Nested relationships
    transaction: List[TransactionResponse] = []
    rfm_segments: List[CustomerSegmentResponse] = []

    model_config = ConfigDict(from_attributes=True)