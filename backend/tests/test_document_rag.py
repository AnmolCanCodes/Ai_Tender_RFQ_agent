"""
Integration tests for Document Processing Worker and RAG Q&A service.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.organization import Organization
from app.models.requirement import Requirement
from app.models.tender import Tender
from app.models.user import User
from app.services.matching_service import answer_tender_question, run_bid_readiness_analysis
from app.models.company_profile import CompanyProfile
from app.workers.document_worker import process_tender_document

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


def test_rag_and_bid_readiness_flow():
    """Verifies RAG Q&A retrieval and Bid Readiness scoring."""
    db = TestingSessionLocal()
    try:
        # Create Org, User, Tender
        org = Organization(name="Gov Tech Corp")
        db.add(org)
        db.flush()

        user = User(
            organization_id=org.id,
            email="gov@tech.com",
            password_hash="hash",
            full_name="Gov Admin",
            role="OWNER",
        )
        db.add(user)
        db.flush()

        tender = Tender(
            organization_id=org.id,
            title="Smart Grid RFQ",
            reference_number="RFQ-SG-2026",
            status="ANALYZED",
        )
        db.add(tender)
        db.flush()

        doc = Document(
            tender_id=tender.id,
            filename="smart_grid.pdf",
            storage_path="/tmp/fake.pdf",
            processing_status="PROCESSED",
        )
        db.add(doc)
        db.flush()

        # Add Chunks
        c1 = Chunk(
            document_id=doc.id,
            tender_id=tender.id,
            content="Section 4.2: Liquidated damages for delayed supply will be 0.5% per week up to a maximum of 10%.",
            page_number=14,
            section="Clause 4.2 - Liquidated Damages",
            chunk_index=0,
            embedding=None,
        )
        c2 = Chunk(
            document_id=doc.id,
            tender_id=tender.id,
            content="Section 2.1: The Earnest Money Deposit (EMD) of Rs 2,50,000 must be submitted via Bank Guarantee.",
            page_number=5,
            section="Clause 2.1 - EMD Submission",
            chunk_index=1,
            embedding=None,
        )
        db.add_all([c1, c2])

        # Add Requirements
        r1 = Requirement(
            tender_id=tender.id,
            category="ELIGIBILITY",
            title="GST Registration",
            description="Bidder must have active GST registration",
            mandatory=True,
            status="PENDING",
        )
        r2 = Requirement(
            tender_id=tender.id,
            category="FINANCIAL",
            title="Annual Turnover",
            description="Minimum average annual turnover of Rs 5 Crore",
            mandatory=True,
            status="PENDING",
        )
        db.add_all([r1, r2])

        # Add Company Profile
        profile = CompanyProfile(
            organization_id=org.id,
            legal_name="Gov Tech Corp",
            annual_turnover=80000000.0,
            gst_number="07AAAAA0000A1Z5",
            years_experience=6,
        )
        db.add(profile)
        db.commit()

        # Test RAG retrieval and answer
        rag_res = answer_tender_question(
            db=db,
            organization_id=org.id,
            user_id=user.id,
            tender_id=tender.id,
            question="What is the EMD requirement?",
        )
        assert rag_res["question"] == "What is the EMD requirement?"
        assert len(rag_res["citations"]) > 0
        assert any(c["page_number"] == 5 for c in rag_res["citations"])

        # Test Bid Readiness
        readiness_res = run_bid_readiness_analysis(
            db=db,
            organization_id=org.id,
            user_id=user.id,
            tender_id=tender.id,
        )
        assert readiness_res["tender_id"] == tender.id
        assert readiness_res["matched_count"] == 2
        assert readiness_res["eligibility_score"] == 100.0
        assert readiness_res["overall_readiness"] in ("HIGH", "MEDIUM")

    finally:
        db.close()
