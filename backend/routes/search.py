from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session

from models import User, IMEI
from schemas import (
    SearchRequest, SearchResult, SearchHistoryResponse,
    IMEIDetailResponse, ValidateIMEIRequest, ValidateIMEIResponse
)
from security import get_current_user
from database import get_db
from search_service import SearchService
from ocr_service import IMEIExtractor
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])
extractor = IMEIExtractor()


@router.post("/", response_model=SearchResult)
async def search_imeis(
    search_request: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Buscar IMEIs"""
    
    try:
        result = SearchService.search_imeis(
            user_id=current_user.id,
            query=search_request.query,
            search_type=search_request.search_type,
            limit=search_request.limit,
            offset=search_request.offset,
            db=db
        )
        
        imeis = [
            IMEIDetailResponse(
                id=imei.id,
                imei=imei.imei,
                imei_normalized=imei.imei_normalized,
                device_model=imei.device_model,
                device_brand=imei.device_brand,
                confidence=imei.confidence,
                is_valid=imei.is_valid,
                extracted_at=imei.extracted_at,
                image_upload_id=imei.image_upload_id,
                raw_text=imei.raw_text,
                x_position=imei.x_position,
                y_position=imei.y_position,
                width=imei.width,
                height=imei.height,
                manual_correction=imei.manual_correction
            )
            for imei in result["results"]
        ]
        
        return SearchResult(
            total=result["total"],
            limit=result["limit"],
            offset=result["offset"],
            results=imeis
        )
    
    except Exception as e:
        logger.error(f"Error searching IMEIs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error searching IMEIs"
        )


@router.get("/quick", response_model=SearchResult)
async def quick_search(
    query: str = Query(..., min_length=2, max_length=16),
    limit: int = Query(20, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Busca rápida (parcial)"""
    
    search_request = SearchRequest(
        query=query,
        search_type="partial",
        limit=limit,
        offset=0
    )
    
    return await search_imeis(search_request, current_user, db)


@router.get("/suggestions")
async def get_suggestions(
    prefix: str = Query(..., min_length=1, max_length=16),
    limit: int = Query(10, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obter sugestões de busca (autocomplete)"""
    
    try:
        suggestions = SearchService.get_search_suggestions(
            user_id=current_user.id,
            prefix=prefix,
            db=db,
            limit=limit
        )
        
        return {
            "prefix": prefix,
            "suggestions": suggestions
        }
    
    except Exception as e:
        logger.error(f"Error getting suggestions: {str(e)}")
        return {
            "prefix": prefix,
            "suggestions": []
        }


@router.get("/history", response_model=list[SearchHistoryResponse])
async def get_search_history(
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obter histórico de buscas"""
    
    try:
        history = SearchService.get_search_history(
            user_id=current_user.id,
            limit=limit,
            db=db
        )
        
        return [
            SearchHistoryResponse(
                id=h.id,
                query=h.query,
                query_type=h.query_type,
                results_count=h.results_count,
                search_time_ms=h.search_time_ms,
                searched_at=h.searched_at
            )
            for h in history
        ]
    
    except Exception as e:
        logger.error(f"Error getting search history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting search history"
        )


@router.get("/similar/{imei_id}", response_model=list[IMEIDetailResponse])
async def get_similar_imeis(
    imei_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Encontrar IMEIs similares"""
    
    # Obter IMEI original
    original_imei = db.query(IMEI).filter(
        IMEI.id == imei_id,
        IMEI.user_id == current_user.id
    ).first()
    
    if not original_imei:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IMEI not found"
        )
    
    try:
        similar = SearchService.get_similar_imeis(
            user_id=current_user.id,
            imei=original_imei.imei_normalized,
            db=db
        )
        
        return [
            IMEIDetailResponse(
                id=imei.id,
                imei=imei.imei,
                imei_normalized=imei.imei_normalized,
                device_model=imei.device_model,
                device_brand=imei.device_brand,
                confidence=imei.confidence,
                is_valid=imei.is_valid,
                extracted_at=imei.extracted_at,
                image_upload_id=imei.image_upload_id,
                raw_text=imei.raw_text,
                x_position=imei.x_position,
                y_position=imei.y_position,
                width=imei.width,
                height=imei.height,
                manual_correction=imei.manual_correction
            )
            for imei in similar
        ]
    
    except Exception as e:
        logger.error(f"Error getting similar IMEIs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting similar IMEIs"
        )


@router.post("/validate", response_model=ValidateIMEIResponse)
async def validate_imei(
    request: ValidateIMEIRequest,
    current_user: User = Depends(get_current_user)
):
    """Validar IMEI"""
    
    try:
        is_valid = extractor._is_valid_imei(request.imei)
        
        return ValidateIMEIResponse(
            imei=request.imei,
            is_valid=is_valid,
            validation_method="luhn",
            message="Valid IMEI" if is_valid else "Invalid IMEI"
        )
    
    except Exception as e:
        logger.error(f"Error validating IMEI: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error validating IMEI"
        )


@router.post("/imei/{imei_id}/correct")
async def correct_imei(
    imei_id: str,
    corrected_value: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Corrigir um IMEI manualmente"""
    
    imei = db.query(IMEI).filter(
        IMEI.id == imei_id,
        IMEI.user_id == current_user.id
    ).first()
    
    if not imei:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IMEI not found"
        )
    
    try:
        # Validar novo valor
        if not extractor._is_valid_imei(corrected_value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid IMEI format"
            )
        
        # Atualizar IMEI
        imei.manual_correction = corrected_value
        imei.imei = corrected_value
        imei.imei_normalized = extractor._normalize_imei(corrected_value)
        imei.is_valid = True
        imei.validation_source = "manual"
        
        db.commit()
        db.refresh(imei)
        
        logger.info(f"IMEI corrected: {imei_id}")
        
        return {
            "id": imei.id,
            "imei": imei.imei,
            "manual_correction": imei.manual_correction,
            "updated_at": imei.extracted_at
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error correcting IMEI: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error correcting IMEI"
        )
