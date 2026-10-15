
from typing import Optional, Literal

from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine, SessionLocal
import models


app = FastAPI(
    title="MindBridge API",
    description="Privacy-First Student Support & Case Coordination",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create missing database tables
Base.metadata.create_all(bind=engine)


# Database session for each request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Allowed case statuses
CaseStatus = Literal[
    "submitted",
    "in_review",
    "in_progress",
    "resolved",
    "closed"
]


# Request model for creating a case
class CaseCreate(BaseModel):
    category: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=10)


# Request model for updating a case
class CaseUpdate(BaseModel):
    category: Optional[str] = Field(
        default=None, min_length=2, max_length=50
    )
    title: Optional[str] = Field(
        default=None, min_length=3, max_length=150
    )
    description: Optional[str] = Field(
        default=None, min_length=10
    )
    status: Optional[CaseStatus] = None


# Reusable response format

def case_to_dict(case):
    return {
        "id": case.id,
        "category": case.category,
        "title": case.title,
        "description": case.description,
        "status": case.status,
        "created_at": (
            case.created_at.isoformat()
            if case.created_at else None
        )
    }



# Home endpoint
@app.get("/")
def home():
    return {
        "message": "Welcome to MindBridge API!",
        "status": "running"
    }


# Create a new case
@app.post("/api/v1/cases", status_code=201)
def create_case(
    case: CaseCreate,
    db: Session = Depends(get_db)
):
    new_case = models.Case(
        category=case.category,
        title=case.title,
        description=case.description,
        status="submitted"
    )

    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    return case_to_dict(new_case)


# List cases with pagination, filters, and sorting
@app.get("/api/v1/cases")
def get_cases(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    status: Optional[CaseStatus] = None,
    category: Optional[str] = None,
    sort_order: str = Query(
        default="desc",
        pattern="^(asc|desc)$"
    ),
    db: Session = Depends(get_db)
):
    query = db.query(models.Case)

    if status is not None:
        query = query.filter(models.Case.status == status)

    if category:
        query = query.filter(models.Case.category == category)

    if sort_order == "asc":
        query = query.order_by(models.Case.id.asc())
    else:
        query = query.order_by(models.Case.id.desc())

    cases = query.offset(skip).limit(limit).all()

    return [case_to_dict(case) for case in cases]


# Count all cases
# Keep this route BEFORE /api/v1/cases/{case_id}
@app.get("/api/v1/cases/count")
def get_case_count(db: Session = Depends(get_db)):
    total = db.query(models.Case).count()
    return {"total_cases": total}


# Get one case by ID
@app.get("/api/v1/cases/{case_id}")
def get_case(
    case_id: int,
    db: Session = Depends(get_db)
):
    case = db.query(models.Case).filter(
        models.Case.id == case_id
    ).first()

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="Case not found"
        )

    return case_to_dict(case)


# Update an existing case
@app.patch("/api/v1/cases/{case_id}")
def update_case(
    case_id: int,
    update: CaseUpdate,
    db: Session = Depends(get_db)
):
    case = db.query(models.Case).filter(
        models.Case.id == case_id
    ).first()

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="Case not found"
        )

    changes = update.model_dump(exclude_unset=True)

        # Status changes are blocked until coordinator authentication
    # and role-based authorization are implemented.
    if "status" in changes:
        raise HTTPException(
            status_code=403,
            detail="Only an authenticated coordinator can update case status."
        )

    for field, value in changes.items():
        setattr(case, field, value)

    db.commit()
    db.refresh(case)

    return case_to_dict(case)
