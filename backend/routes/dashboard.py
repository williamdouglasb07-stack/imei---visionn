from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from models import User, ImageUpload, IMEI, SearchHistory
from schemas import DashboardResponse, DashboardStats, ImageUploadResponse, IMEIResponse
from security import get_current_user
from database import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obter estatísticas do usuário"""
    
    try:
        # Total de uploads
        total_uploads = db.query(func.count(ImageUpload.id)).filter(
            ImageUpload.user_id == current_user.id
        ).scalar() or 0
        
        # Total de IMEIs
        total_imeis = db.query(func.count(IMEI.id)).filter(
            IMEI.user_id == current_user.id
        ).scalar() or 0
        
        # Total de buscas
        total_searches = db.query(func.count(SearchHistory.id)).filter(
            SearchHistory.user_id == current_user.id
        ).scalar() or 0
        
        # Uploads recentes (24 horas)
        since_24h = datetime.utcnow() - timedelta(hours=24)
        recent_uploads = db.query(func.count(ImageUpload.id)).filter(
            ImageUpload.user_id == current_user.id,
            ImageUpload.uploaded_at >= since_24h
        ).scalar() or 0
        
        # IMEIs recentes (24 horas)
        recent_imeis = db.query(func.count(IMEI.id)).filter(
            IMEI.user_id == current_user.id,
            IMEI.extracted_at >= since_24h
        ).scalar() or 0
        
        return DashboardStats(
            total_uploads=total_uploads,
            total_imeis=total_imeis,
            total_searches=total_searches,
            recent_uploads=recent_uploads,
            recent_imeis=recent_imeis
        )
    
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting statistics"
        )


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obter dados completos do dashboard"""
    
    try:
        # Obter estatísticas
        stats = await get_stats(current_user, db)
        
        # Uploads recentes
        recent_uploads = db.query(ImageUpload).filter(
            ImageUpload.user_id == current_user.id
        ).order_by(
            ImageUpload.uploaded_at.desc()
        ).limit(10).all()
        
        uploads_response = [
            ImageUploadResponse(
                id=img.id,
                filename=img.filename,
                original_filename=img.original_filename,
                file_size=img.file_size,
                mime_type=img.mime_type,
                ocr_status=img.ocr_status,
                uploaded_at=img.uploaded_at,
                processed_at=img.processed_at,
                imeis_count=len(img.imeis)
            )
            for img in recent_uploads
        ]
        
        # IMEIs recentes
        recent_imeis_records = db.query(IMEI).filter(
            IMEI.user_id == current_user.id
        ).order_by(
            IMEI.extracted_at.desc()
        ).limit(10).all()
        
        imeis_response = [
            IMEIResponse(
                id=imei.id,
                imei=imei.imei,
                imei_normalized=imei.imei_normalized,
                device_model=imei.device_model,
                device_brand=imei.device_brand,
                confidence=imei.confidence,
                is_valid=imei.is_valid,
                extracted_at=imei.extracted_at,
                image_upload_id=imei.image_upload_id
            )
            for imei in recent_imeis_records
        ]
        
        return DashboardResponse(
            stats=stats,
            recent_uploads=uploads_response,
            recent_imeis=imeis_response
        )
    
    except Exception as e:
        logger.error(f"Error getting dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting dashboard"
        )


@router.get("/activity")
async def get_activity(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obter atividade dos últimos N dias"""
    
    try:
        since = datetime.utcnow() - timedelta(days=days)
        
        # Uploads por dia
        uploads_by_day = db.query(
            func.date(ImageUpload.uploaded_at).label('date'),
            func.count(ImageUpload.id).label('count')
        ).filter(
            ImageUpload.user_id == current_user.id,
            ImageUpload.uploaded_at >= since
        ).group_by(
            func.date(ImageUpload.uploaded_at)
        ).order_by('date').all()
        
        # IMEIs extraídos por dia
        imeis_by_day = db.query(
            func.date(IMEI.extracted_at).label('date'),
            func.count(IMEI.id).label('count')
        ).filter(
            IMEI.user_id == current_user.id,
            IMEI.extracted_at >= since
        ).group_by(
            func.date(IMEI.extracted_at)
        ).order_by('date').all()
        
        # Buscas por dia
        searches_by_day = db.query(
            func.date(SearchHistory.searched_at).label('date'),
            func.count(SearchHistory.id).label('count')
        ).filter(
            SearchHistory.user_id == current_user.id,
            SearchHistory.searched_at >= since
        ).group_by(
            func.date(SearchHistory.searched_at)
        ).order_by('date').all()
        
        return {
            "uploads": [
                {"date": str(date), "count": count}
                for date, count in uploads_by_day
            ],
            "imeis": [
                {"date": str(date), "count": count}
                for date, count in imeis_by_day
            ],
            "searches": [
                {"date": str(date), "count": count}
                for date, count in searches_by_day
            ]
        }
    
    except Exception as e:
        logger.error(f"Error getting activity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting activity"
        )


@router.get("/stats-by-device")
async def get_stats_by_device(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obter estatísticas por dispositivo/marca"""
    
    try:
        # IMEIs por marca
        by_brand = db.query(
            IMEI.device_brand,
            func.count(IMEI.id).label('count')
        ).filter(
            IMEI.user_id == current_user.id,
            IMEI.device_brand.isnot(None)
        ).group_by(
            IMEI.device_brand
        ).order_by('count').desc().all()
        
        # IMEIs por modelo
        by_model = db.query(
            IMEI.device_model,
            func.count(IMEI.id).label('count')
        ).filter(
            IMEI.user_id == current_user.id,
            IMEI.device_model.isnot(None)
        ).group_by(
            IMEI.device_model
        ).order_by('count').desc().limit(10).all()
        
        return {
            "by_brand": [
                {"brand": brand, "count": count}
                for brand, count in by_brand
            ],
            "by_model": [
                {"model": model, "count": count}
                for model, count in by_model
            ]
        }
    
    except Exception as e:
        logger.error(f"Error getting device stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting device statistics"
        )
