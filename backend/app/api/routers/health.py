from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.health_service import health_summary

router = APIRouter()


@router.get('/health')
async def health(db: Session = Depends(get_db)):
    return await health_summary(db)
