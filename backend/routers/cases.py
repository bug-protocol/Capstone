from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from backend.database import get_db
from backend.models.db_models import User, TriageCase
from backend.models.schemas import (
    CaseResponse,
    CaseListResponse,
    CaseUpdateStatusRequest,
)
from backend.auth.dependencies import get_current_user

router = APIRouter(prefix="/cases", tags=["Pharmacovigilance Triage Review Queue"])


@router.get("", response_model=CaseListResponse)
async def list_triage_cases(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    drug_name: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    mine_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(TriageCase)
    count_query = select(func.count(TriageCase.id))

    if status_filter:
        query = query.where(TriageCase.status == status_filter.upper())
        count_query = count_query.where(TriageCase.status == status_filter.upper())

    if drug_name:
        query = query.where(TriageCase.drug_name.ilike(f"%{drug_name}%"))
        count_query = count_query.where(TriageCase.drug_name.ilike(f"%{drug_name}%"))
        
    if mine_only:
        query = query.where(TriageCase.user_id == current_user.id)
        count_query = count_query.where(TriageCase.user_id == current_user.id)

    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(TriageCase.created_at.desc()).offset(offset).limit(limit)
    res = await db.execute(query)
    cases = res.scalars().all()

    return CaseListResponse(
        total=total,
        cases=[CaseResponse.model_validate(c) for c in cases]
    )


@router.get("/{case_id}", response_model=CaseResponse)
async def get_triage_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TriageCase).where(TriageCase.id == case_id)
    res = await db.execute(stmt)
    case = res.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Triage case not found")

    return case


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case_status(
    case_id: str,
    update_data: CaseUpdateStatusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TriageCase).where(TriageCase.id == case_id)
    res = await db.execute(stmt)
    case = res.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Triage case not found")

    case.status = update_data.status.upper()
    if update_data.reviewer_notes is not None:
        case.reviewer_notes = update_data.reviewer_notes
    if update_data.assigned_reviewer is not None:
        case.assigned_reviewer = update_data.assigned_reviewer
    else:
        case.assigned_reviewer = current_user.username

    await db.commit()
    await db.refresh(case)

    return case


@router.delete("/{case_id}")
async def delete_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TriageCase).where(TriageCase.id == case_id)
    res = await db.execute(stmt)
    case = res.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Triage case not found")

    await db.delete(case)
    await db.commit()

    return {"message": "Case deleted successfully"}


@router.delete("/{case_id}")
async def delete_cases(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TriageCase).where(TriageCase.id == case_id)
    res = await db.execute(stmt)
    case = res.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Triage case not found")

    await db.delete(case)
    await db.commit()

    return {"message": "Case deleted successfully"}
