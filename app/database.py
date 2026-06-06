import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Retrieve the database URL from environment variables, defaulting to the local Docker setup
# The 'db' hostname matches the database service name defined in docker-compose.yml
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+psycopg://postgres:analytics_password@db:5432/analytics_saas"
)

# Initialize the SQLAlchemy engine for PostgreSQL connection managment
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create a configured "Session" class to handle data operations and transactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Definde the base class for ORM models to inherit from
Base = declarative_base()

def get_db():
    """
    Dependency function to provide a database session per API request.
    Ensures the database session is safely closed after the request lifecycle ends
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()