from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from .main import app, get_db
from .database import Base

# 1. Setup an in-memory SQLite database for testing purposes
# This ensures tests are isolated and don't affect the real PostgreSQL database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2. Create tables in the temporary database
Base.metadata.create_all(bind=engine)

# 3. Override the database dependency in FastAPI
# This tells the app to use our temporary test database instead of the real one
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# 4. Initialize the TestClient
client = TestClient(app)

# --- THE TESTS ---

def test_summary_unauthorized():
    """
    Verifies that the API correctly blocks unauthenticated requests to the analytics summary endpoint.
    Ensures a 403 Forbidden HTTP status code is returned when the X-API-Key header is omitted.
    """
    # Simulate a GET request without providing the required authorization headers
    response = client.get("/analytics/summary/")
    
    # Assert that the server strictly enforces authentication
    assert response.status_code == 403
    
# Validate the structure and content of the error payload
    assert response.json() == {"detail": "Access Denied. Invalid or missing API Key"}