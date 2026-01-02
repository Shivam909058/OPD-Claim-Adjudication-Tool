"""
Database setup and models for OPD Claim Adjudication Tool.
Uses SQLite with SQLAlchemy for persistence.
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings

# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class ClaimRecord(Base):
    """SQLAlchemy model for storing claims."""
    __tablename__ = "claims"
    
    # Primary key
    claim_id = Column(String(50), primary_key=True, index=True)
    
    # Member info
    member_id = Column(String(50), index=True, nullable=False)
    member_name = Column(String(200), nullable=False)
    member_join_date = Column(String(20), nullable=True)
    
    # Claim details
    treatment_date = Column(String(20), nullable=False)
    claim_amount = Column(Float, nullable=False)
    hospital = Column(String(200), nullable=True)
    category = Column(String(50), nullable=True)
    cashless_request = Column(Boolean, default=False)
    
    # Status and decision
    status = Column(String(20), default="PENDING", index=True)
    decision = Column(String(20), nullable=True)
    approved_amount = Column(Float, default=0)
    confidence_score = Column(Float, default=0)
    
    # Rejection info
    rejection_reasons = Column(Text, nullable=True)  # JSON string
    rejected_items = Column(Text, nullable=True)  # JSON string
    
    # Deductions
    copay_amount = Column(Float, default=0)
    network_discount = Column(Float, default=0)
    excluded_amount = Column(Float, default=0)
    
    # Extracted data (JSON)
    extracted_data = Column(Text, nullable=True)
    
    # Documents (JSON) - stores the original submission
    documents = Column(Text, nullable=True)
    
    # Notes and additional info
    notes = Column(Text, nullable=True)
    next_steps = Column(Text, nullable=True)
    fraud_flags = Column(Text, nullable=True)  # JSON string
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "claim_id": self.claim_id,
            "member_id": self.member_id,
            "member_name": self.member_name,
            "member_join_date": self.member_join_date,
            "treatment_date": self.treatment_date,
            "claim_amount": self.claim_amount,
            "hospital": self.hospital,
            "category": self.category,
            "cashless_request": self.cashless_request,
            "status": self.status,
            "decision": self.decision,
            "approved_amount": self.approved_amount,
            "confidence_score": self.confidence_score,
            "rejection_reasons": json.loads(self.rejection_reasons) if self.rejection_reasons else [],
            "rejected_items": json.loads(self.rejected_items) if self.rejected_items else [],
            "copay_amount": self.copay_amount,
            "network_discount": self.network_discount,
            "excluded_amount": self.excluded_amount,
            "extracted_data": json.loads(self.extracted_data) if self.extracted_data else None,
            "documents": json.loads(self.documents) if self.documents else None,
            "notes": self.notes,
            "next_steps": self.next_steps,
            "fraud_flags": json.loads(self.fraud_flags) if self.fraud_flags else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }


class AppealRecord(Base):
    """SQLAlchemy model for storing appeals."""
    __tablename__ = "appeals"
    
    appeal_id = Column(String(50), primary_key=True, index=True)
    claim_id = Column(String(50), index=True, nullable=False)
    reason = Column(Text, nullable=False)
    additional_documents = Column(Text, nullable=True)  # JSON string
    status = Column(String(20), default="UNDER_REVIEW")
    resolution = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


def init_db():
    """Initialize the database and create tables."""
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully!")


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Don't close here, let the caller manage it


def close_db(db: Session):
    """Close database session."""
    db.close()


# CRUD Operations
def create_claim(db: Session, claim_data: Dict[str, Any]) -> ClaimRecord:
    """Create a new claim record."""
    record = ClaimRecord(
        claim_id=claim_data["claim_id"],
        member_id=claim_data["member_id"],
        member_name=claim_data["member_name"],
        member_join_date=claim_data.get("member_join_date"),
        treatment_date=claim_data["treatment_date"],
        claim_amount=claim_data["claim_amount"],
        hospital=claim_data.get("hospital"),
        category=claim_data.get("category"),
        cashless_request=claim_data.get("cashless_request", False),
        status="PENDING",
        documents=json.dumps(claim_data.get("documents", {})),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_claim(db: Session, claim_id: str) -> Optional[ClaimRecord]:
    """Get a claim by ID."""
    return db.query(ClaimRecord).filter(ClaimRecord.claim_id == claim_id).first()


def get_claims_by_member(db: Session, member_id: str) -> List[ClaimRecord]:
    """Get all claims for a member."""
    return db.query(ClaimRecord).filter(ClaimRecord.member_id == member_id).all()


def get_all_claims(db: Session, skip: int = 0, limit: int = 100) -> List[ClaimRecord]:
    """Get all claims with pagination."""
    return db.query(ClaimRecord).order_by(ClaimRecord.created_at.desc()).offset(skip).limit(limit).all()


def update_claim_decision(
    db: Session,
    claim_id: str,
    decision: str,
    approved_amount: float,
    rejection_reasons: List[str] = None,
    rejected_items: List[str] = None,
    confidence_score: float = 0.95,
    notes: str = None,
    next_steps: str = None,
    fraud_flags: List[str] = None,
    extracted_data: Dict[str, Any] = None,
    copay_amount: float = 0,
    network_discount: float = 0,
    excluded_amount: float = 0,
) -> Optional[ClaimRecord]:
    """Update claim with adjudication decision."""
    record = get_claim(db, claim_id)
    if not record:
        return None
    
    record.status = decision
    record.decision = decision
    record.approved_amount = approved_amount
    record.confidence_score = confidence_score
    record.rejection_reasons = json.dumps(rejection_reasons or [])
    record.rejected_items = json.dumps(rejected_items or [])
    record.notes = notes
    record.next_steps = next_steps
    record.fraud_flags = json.dumps(fraud_flags or [])
    record.copay_amount = copay_amount
    record.network_discount = network_discount
    record.excluded_amount = excluded_amount
    record.processed_at = datetime.utcnow()
    
    if extracted_data:
        record.extracted_data = json.dumps(extracted_data)
    
    db.commit()
    db.refresh(record)
    return record


def get_claims_ytd(db: Session, member_id: str, year: int) -> float:
    """Get total approved claims for a member in a year."""
    from sqlalchemy import func, extract
    
    result = db.query(func.sum(ClaimRecord.approved_amount)).filter(
        ClaimRecord.member_id == member_id,
        ClaimRecord.status == "APPROVED",
        extract('year', ClaimRecord.created_at) == year
    ).scalar()
    
    return result or 0.0


def get_claims_same_day(db: Session, member_id: str, treatment_date: str) -> int:
    """Get count of claims for same member on same day."""
    return db.query(ClaimRecord).filter(
        ClaimRecord.member_id == member_id,
        ClaimRecord.treatment_date == treatment_date
    ).count()
