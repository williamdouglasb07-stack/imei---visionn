import os
import hashlib
import imagehash
from PIL import Image
from pathlib import Path
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from models import ImageUpload, IMEI, DuplicateImage, User
from ocr_service import IMEIExtractor
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class FileService:
    """Serviço de gerenciamento de arquivos"""
    
    @staticmethod
    def ensure_upload_dir():
        """Garantir que diretório de uploads existe"""
        Path("/app/uploads").mkdir(parents=True, exist_ok=True)
        Path("/app/temp").mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """Calcular hash SHA256 do arquivo"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    @staticmethod
    def calculate_perceptual_hash(file_path: str) -> str:
        """Calcular hash perceptual da imagem"""
        try:
            img = Image.open(file_path)
            phash = imagehash.phash(img)
            return str(phash)
        except Exception as e:
            logger.error(f"Error calculating perceptual hash: {str(e)}")
            return ""
    
    @staticmethod
    def is_duplicate_image(
        user_id: str,
        perceptual_hash: str,
        threshold: float = 0.9,
        db: Session = None
    ) -> Optional[str]:
        """
        Detectar se imagem é duplicada comparando hashes perceptuais
        Retorna o ID da imagem original se for duplicada, None caso contrário
        """
        if not db or not perceptual_hash:
            return None
        
        try:
            # Procurar por imagens similares do mesmo usuário
            similar_images = db.query(ImageUpload).filter(
                ImageUpload.user_id == user_id,
                ImageUpload.perceptual_hash.isnot(None)
            ).all()
            
            current_hash = imagehash.ImageHash(
                bytes.fromhex(perceptual_hash)
            )
            
            for image in similar_images:
                try:
                    existing_hash = imagehash.ImageHash(
                        bytes.fromhex(image.perceptual_hash)
                    )
                    # Comparar similaridade
                    similarity = 1 - (current_hash - existing_hash) / len(current_hash.hash.flatten())
                    
                    if similarity >= threshold:
                        logger.info(f"Duplicate image detected: {image.id}")
                        return image.id
                except Exception as e:
                    logger.warning(f"Error comparing hashes: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"Error checking duplicate images: {str(e)}")
        
        return None
    
    @staticmethod
    def get_unique_filename(original_filename: str, user_id: str) -> str:
        """Gerar nome único para arquivo"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(original_filename)
        return f"{user_id}/{timestamp}_{hashlib.md5(name.encode()).hexdigest()}{ext}"


class ImageProcessingService:
    """Serviço de processamento de imagens e OCR"""
    
    def __init__(self):
        self.extractor = IMEIExtractor()
    
    async def process_image(
        self,
        image_path: str,
        image_upload: ImageUpload,
        db: Session
    ) -> Tuple[int, List[dict]]:
        """
        Processar imagem e extrair IMEIs
        Retorna (número de IMEIs encontrados, lista de IMEIs)
        """
        try:
            # Atualizar status para processando
            image_upload.ocr_status = "processing"
            db.commit()
            
            # Extrair IMEIs
            detections = self.extractor.extract_imeis_from_image(image_path)
            
            imeis_data = []
            
            # Salvar cada IMEI no banco
            for detection in detections:
                # Obter informações do dispositivo
                brand, model = self.extractor.get_device_info(detection.imei)
                
                imei = IMEI(
                    user_id=image_upload.user_id,
                    image_upload_id=image_upload.id,
                    imei=detection.imei,
                    imei_normalized=self.extractor._normalize_imei(detection.imei),
                    confidence=detection.confidence,
                    raw_text=detection.raw_text,
                    device_brand=brand,
                    device_model=model,
                    is_valid=True,
                    validation_source="ocr",
                    x_position=detection.x,
                    y_position=detection.y,
                    width=detection.width,
                    height=detection.height
                )
                
                db.add(imei)
                
                imeis_data.append({
                    "imei": detection.imei,
                    "confidence": detection.confidence,
                    "device_brand": brand,
                    "device_model": model
                })
            
            # Atualizar status
            image_upload.ocr_status = "completed"
            image_upload.processed_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Processed image {image_upload.id}: {len(imeis_data)} IMEIs found")
            return len(imeis_data), imeis_data
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            image_upload.ocr_status = "failed"
            image_upload.ocr_error = str(e)
            db.commit()
            return 0, []
    
    async def process_batch(
        self,
        image_ids: List[str],
        user_id: str,
        db: Session
    ) -> dict:
        """
        Processar múltiplas imagens em paralelo
        """
        results = {
            "total": len(image_ids),
            "processed": 0,
            "failed": 0,
            "total_imeis": 0,
            "results": []
        }
        
        for image_id in image_ids:
            try:
                image_upload = db.query(ImageUpload).filter(
                    ImageUpload.id == image_id,
                    ImageUpload.user_id == user_id
                ).first()
                
                if image_upload:
                    count, imeis = await self.process_image(
                        image_upload.file_path,
                        image_upload,
                        db
                    )
                    results["processed"] += 1
                    results["total_imeis"] += count
                    results["results"].append({
                        "image_id": image_id,
                        "imeis_count": count
                    })
            except Exception as e:
                logger.error(f"Error in batch processing: {str(e)}")
                results["failed"] += 1
        
        return results
    
    @staticmethod
    def get_image_info(image_path: str) -> dict:
        """Obter informações da imagem"""
        try:
            img = Image.open(image_path)
            return {
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode
            }
        except Exception as e:
            logger.error(f"Error getting image info: {str(e)}")
            return {}
