from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Customer(Base):
    """
    Represents an e-commerce customer entity within the system
    Acts as the parent entity for transactional data and computed metrics
    """
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime, nullable=True)

    # Bidirectional relationships mapped to child tables
    transactions = relationship("Transaction", back_populates="customer")
    rfm_segments = relationship("CustomerSegment", back_populates="customer")
    
class Transaction(Base):
    """
    Stores historical transactional records ingested from external data sources.
    Tracks core purchasing variables required for behavioral cohort analysis.
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(String, unique=True, index=True, nullable=False)
    invoice_date = Column(DateTime, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    status = Column(String, default="completed")

    # Foreign key constraint establishing the relationship with the customers table
    customer_pk = Column(Integer, ForeignKey("customers.id"), nullable=False)
    customer = relationship("Customer", back_populates="transactions")

class CustomerSegment(Base):
    """
    Holds the computed scores from the Recency, Frequency, Monetary (RFM) segmentation engine
    Allows for decoupled reading of optimized labels without recalculating raw data
    """
    __tablename__ = "customer_segments"

    id = Column(Integer, primary_key=True, index=True)
    recency_score = Column(Integer, nullable=False)
    frequency_score = Column(Integer, nullable=False)
    monetary_score = Column(Integer, nullable=False)
    rfm_cell = Column(String, nullable=False)
    segment_label = Column(String, nullable=False, index=True)
    updated_at = Column(DateTime, nullable=False)

    # Foreign key constraint establishing the relationship with the customers table
    customer_pk = Column(Integer, ForeignKey("customers.id"), nullable=False)
    customer = relationship("Customer", back_populates="rfm_segments")