from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.health_service import health_summary

router = APIRouter()


@router.get('/ready')
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text('SELECT 1'))
    except Exception as exc:
        raise HTTPException(status_code=503, detail='Database is not ready') from exc
    return {'ready': True}


@router.get('/health')
async def health(db: Session = Depends(get_db)):
    return await health_summary(db)
