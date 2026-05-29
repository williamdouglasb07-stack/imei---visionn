from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os
from pathlib import Path

from models import User, ImageUpload
from schemas import ImageUploadResponse, ImageUploadDetailResponse, ProcessImageResponse, OCRResult
from security import get_current_user
from database import get_db
from upload_service import FileService, ImageProcessingService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

# Inicializar serviços
FileService.ensure_upload_dir()
image_service = ImageProcessingService()


@router.post("/images", response_model=List[ImageUploadResponse], status_code=status.HTTP_202_ACCEPTED)
async def upload_images(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload de múltiplas imagens"""
    
    uploaded_images = []
    
    for file in files:
        try:
            # Validar tipo de arquivo
            if not file.content_type.startswith("image/"):
                continue
            
            # Ler arquivo
            contents = await file.read()
            
            if len(contents) == 0:
                continue
            
            # Gerar nome único
            unique_filename = FileService.get_unique_filename(file.filename, current_user.id)
            file_path = f"/app/uploads/{unique_filename}"
            
            # Garantir diretório
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Salvar arquivo
            with open(file_path, "wb") as f:
                f.write(contents)
            
            # Calcular hashes
            file_hash = FileService.calculate_file_hash(file_path)
            perceptual_hash = FileService.calculate_perceptual_hash(file_path)
            
            # Verificar duplicação
            is_duplicate = FileService.is_duplicate_image(
                current_user.id,
                perceptual_hash,
                db=db
            )
            
            # Criar registro no banco
            image_upload = ImageUpload(
                user_id=current_user.id,
                filename=unique_filename,
                original_filename=file.filename,
                file_path=file_path,
                file_size=len(contents),
                mime_type=file.content_type,
                image_hash=file_hash,
                perceptual_hash=perceptual_hash,
                ocr_status="pending"
            )
            
            db.add(image_upload)
            db.commit()
            db.refresh(image_upload)
            
            # Adicionar à lista de resposta
            response = ImageUploadResponse(
                id=image_upload.id,
                filename=image_upload.filename,
                original_filename=image_upload.original_filename,
                file_size=image_upload.file_size,
                mime_type=image_upload.mime_type,
                ocr_status=image_upload.ocr_status,
                uploaded_at=image_upload.uploaded_at,
                processed_at=image_upload.processed_at,
                imeis_count=0
            )
            
            uploaded_images.append(response)
            
            # Agendar processamento em background
            background_tasks.add_task(
                image_service.process_image,
                file_path,
                image_upload,
                db
            )
            
            logger.info(f"Image uploaded: {unique_filename} by user {current_user.id}")
        
        except Exception as e:
            logger.error(f"Error uploading file {file.filename}: {str(e)}")
            continue
    
    if not uploaded_images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid images uploaded"
        )
    
    return uploaded_images


@router.get("/images/{image_id}", response_model=ImageUploadDetailResponse)
async def get_image_detail(
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obter detalhes de uma imagem e seus IMEIs"""
    
    image_upload = db.query(ImageUpload).filter(
        ImageUpload.id == image_id,
        ImageUpload.user_id == current_user.id
    ).first()
    
    if not image_upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    response = ImageUploadDetailResponse(
        id=image_upload.id,
        filename=image_upload.filename,
        original_filename=image_upload.original_filename,
        file_size=image_upload.file_size,
        mime_type=image_upload.mime_type,
        ocr_status=image_upload.ocr_status,
        uploaded_at=image_upload.uploaded_at,
        processed_at=image_upload.processed_at,
        imeis_count=len(image_upload.imeis),
        imeis=[
            {
                "id": imei.id,
                "imei": imei.imei,
                "imei_normalized": imei.imei_normalized,
                "device_model": imei.device_model,
                "device_brand": imei.device_brand,
                "confidence": imei.confidence,
                "is_valid": imei.is_valid,
                "extracted_at": imei.extracted_at,
                "image_upload_id": imei.image_upload_id,
                "raw_text": imei.raw_text,
                "x_position": imei.x_position,
                "y_position": imei.y_position,
                "width": imei.width,
                "height": imei.height,
                "manual_correction": imei.manual_correction
            }
            for imei in image_upload.imeis
        ]
    )
    
    return response


@router.get("/images")
async def list_images(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Listar imagens do usuário"""
    
    query = db.query(ImageUpload).filter(
        ImageUpload.user_id == current_user.id
    ).order_by(ImageUpload.uploaded_at.desc())
    
    total = query.count()
    images = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
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
            for img in images
        ]
    }


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletar uma imagem"""
    
    image_upload = db.query(ImageUpload).filter(
        ImageUpload.id == image_id,
        ImageUpload.user_id == current_user.id
    ).first()
    
    if not image_upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    try:
        # Deletar arquivo
        if os.path.exists(image_upload.file_path):
            os.remove(image_upload.file_path)
        
        # Deletar do banco (cascade delete IMEIs)
        db.delete(image_upload)
        db.commit()
        
        logger.info(f"Image deleted: {image_id}")
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting image"
        )


@router.get("/file/{image_id}")
async def download_image(
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download da imagem original"""
    
    image_upload = db.query(ImageUpload).filter(
        ImageUpload.id == image_id,
        ImageUpload.user_id == current_user.id
    ).first()
    
    if not image_upload or not os.path.exists(image_upload.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    return FileResponse(
        image_upload.file_path,
        filename=image_upload.original_filename,
        media_type=image_upload.mime_type
    )
