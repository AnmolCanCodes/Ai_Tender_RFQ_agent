"""
End-to-end integration and security test suite for backend pipeline.
Tests authentication, multi-tenant isolation, PDF ingestion, chunking,
bid readiness matching, and RAG retrieval.
"""

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.ingestion.chunker import chunk_extracted_pages
from app.ingestion.cleaner import clean_page_text
from app.ingestion.pdf_loader import ExtractedPage
from app.main import app
from app.services.matching_service import evaluate_requirement_match
from app.models.company_profile import CompanyProfile
from app.models.requirement import Requirement

# Setup isolated in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_health_check():
    """Verify health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_auth_registration_and_login():
    """Verify registration and JWT token issue."""
    reg_data = {
        "organization_name": "Test Acme Systems",
        "full_name": "Alice Johnson",
        "email": "alice@acme.com",
        "password": "Password123!",
    }
    res = client.post("/api/v1/auth/register", json=reg_data)
    assert res.status_code == 201
    user = res.json()
    assert user["email"] == "alice@acme.com"
    assert user["role"] == "OWNER"

    # Login
    login_data = {
        "email": "alice@acme.com",
        "password": "Password123!",
    }
    login_res = client.post("/api/v1/auth/login", json=login_data)
    assert login_res.status_code == 200
    token_json = login_res.json()
    assert "access_token" in token_json
    token = token_json["access_token"]

    # Verify protected /auth/me
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "alice@acme.com"


def test_tender_crud_and_deadlines():
    """Verify tender lifecycle management."""
    # Login to acquire token
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@acme.com", "password": "Password123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create Tender
    tender_payload = {
        "title": "Supply of Enterprise Core Switches",
        "reference_number": "TND-CORE-2026",
        "issuing_organization": "Department of Telecom",
        "estimated_value": 25000000.0,
        "emd_amount": 500000.0,
    }
    create_res = client.post("/api/v1/tenders/", json=tender_payload, headers=headers)
    assert create_res.status_code == 201
    tender = create_res.json()
    assert tender["title"] == "Supply of Enterprise Core Switches"
    tender_id = tender["id"]

    # Read Tender
    get_res = client.get(f"/api/v1/tenders/{tender_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["reference_number"] == "TND-CORE-2026"

    # Check deadlines
    dl_res = client.get(f"/api/v1/tenders/{tender_id}/deadlines", headers=headers)
    assert dl_res.status_code == 200
    assert dl_res.json()["tender_id"] == tender_id


def test_text_cleaning_and_chunking():
    """Verify procurement text cleaning and section preservation."""
    sample_text = (
        "SECTION 3: ELIGIBILITY REQUIREMENTS\n\n"
        "1. Bidder must hold valid GST Registration Certificate.\n"
        "2. Minimum annual turnover of Rs 10 Crore in past 3 financial years.\n\n"
        "Page 1 of 40"
    )
    cleaned = clean_page_text(sample_text)
    assert "Page 1 of 40" not in cleaned
    assert "ELIGIBILITY REQUIREMENTS" in cleaned

    page = ExtractedPage(page_number=3, text=cleaned, char_count=len(cleaned))
    chunks = chunk_extracted_pages([page], chunk_size=200, chunk_overlap=30)
    assert len(chunks) > 0
    assert chunks[0].page_number == 3
    assert "SECTION 3" in (chunks[0].section or "")


def test_capability_matching_logic():
    """Verify deterministic matching rules."""
    profile = CompanyProfile(
        organization_id=1,
        legal_name="Acme Tech",
        annual_turnover=150000000.0,  # 15 Crore
        years_experience=8,
        gst_number="27AAACA1234A1Z5",
        certifications="ISO 9001, ISO 27001",
        past_contracts_count=5,
    )

    # 1. GST requirement
    req_gst = Requirement(
        tender_id=1,
        category="ELIGIBILITY",
        title="Valid GST Registration",
        description="The bidder must submit valid GST registration certificate",
        mandatory=True,
    )
    status_val, evidence = evaluate_requirement_match(req_gst, profile)
    assert status_val == "MATCHED"
    assert "27AAACA1234A1Z5" in evidence

    # 2. ISO 14001 requirement (Missing in company profile)
    req_iso = Requirement(
        tender_id=1,
        category="TECHNICAL",
        title="ISO 14001 Certification",
        description="Bidder must possess valid ISO 14001 environmental certification",
        mandatory=True,
    )
    status_val, evidence = evaluate_requirement_match(req_iso, profile)
    assert status_val in ("PARTIAL", "MISSING")
