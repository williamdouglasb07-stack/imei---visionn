import cv2
import numpy as np
from PIL import Image
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass
from config import settings
import re

logger = logging.getLogger(__name__)


@dataclass
class IMEIDetection:
    """Classe para representar detecção de IMEI"""
    imei: str
    confidence: float
    raw_text: str
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0


class IMEIExtractor:
    """Extrator de IMEIs usando OCR"""
    
    def __init__(self):
        self.ocr_engine = settings.OCR_ENGINE
        self.confidence_threshold = settings.OCR_CONFIDENCE_THRESHOLD
        self.ocr = None
        self._init_ocr()
    
    def _init_ocr(self):
        """Inicializar engine de OCR"""
        try:
            if self.ocr_engine == "paddleocr":
                from paddleocr import PaddleOCR
                self.ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang=settings.OCR_LANGUAGE,
                    use_gpu=False
                )
                logger.info("PaddleOCR initialized")
            elif self.ocr_engine == "easyocr":
                import easyocr
                self.ocr = easyocr.Reader([settings.OCR_LANGUAGE])
                logger.info("EasyOCR initialized")
            else:
                logger.warning(f"Unknown OCR engine: {self.ocr_engine}")
        except Exception as e:
            logger.error(f"Error initializing OCR: {str(e)}")
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Pré-processar imagem para melhorar OCR"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not read image: {image_path}")
            
            # Converter para escala de cinza
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Aplicar CLAHE para melhorar contraste
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            # Aplicar threshold adaptativo
            _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(thresh, h=10)
            
            return denoised
        except Exception as e:
            logger.error(f"Error preprocessing image: {str(e)}")
            return cv2.imread(image_path)
    
    def extract_imeis_from_image(self, image_path: str) -> List[IMEIDetection]:
        """Extrair IMEIs de uma imagem"""
        detections = []
        
        try:
            # Pré-processar
            processed_img = self.preprocess_image(image_path)
            
            # Usar OCR apropriado
            if self.ocr_engine == "paddleocr":
                detections = self._extract_paddleocr(processed_img, image_path)
            elif self.ocr_engine == "easyocr":
                detections = self._extract_easyocr(processed_img)
            
            # Validar e normalizar IMEIs
            validated_detections = []
            for detection in detections:
                if self._is_valid_imei(detection.imei):
                    detection.imei = self._normalize_imei(detection.imei)
                    validated_detections.append(detection)
            
            logger.info(f"Extracted {len(validated_detections)} IMEIs from {image_path}")
            return validated_detections
            
        except Exception as e:
            logger.error(f"Error extracting IMEIs: {str(e)}")
            return []
    
    def _extract_paddleocr(self, processed_img: np.ndarray, original_path: str) -> List[IMEIDetection]:
        """Extrair usando PaddleOCR"""
        detections = []
        
        try:
            # Salvar imagem processada temporariamente
            temp_path = "/tmp/paddle_ocr_temp.png"
            cv2.imwrite(temp_path, processed_img)
            
            result = self.ocr.ocr(temp_path, cls=True)
            
            if result and result[0]:
                for line in result[0]:
                    bbox, (text, confidence) = line
                    
                    if confidence >= self.confidence_threshold:
                        # Extrair coordenadas
                        points = np.array(bbox, dtype=np.int32)
                        x = int(points[:, 0].min())
                        y = int(points[:, 1].min())
                        width = int(points[:, 0].max() - x)
                        height = int(points[:, 1].max() - y)
                        
                        # Extrair possíveis IMEIs do texto
                        imei_matches = self._extract_imei_patterns(text)
                        for imei in imei_matches:
                            detections.append(IMEIDetection(
                                imei=imei,
                                confidence=confidence,
                                raw_text=text,
                                x=x,
                                y=y,
                                width=width,
                                height=height
                            ))
        except Exception as e:
            logger.error(f"Error in PaddleOCR extraction: {str(e)}")
        
        return detections
    
    def _extract_easyocr(self, processed_img: np.ndarray) -> List[IMEIDetection]:
        """Extrair usando EasyOCR"""
        detections = []
        
        try:
            result = self.ocr.readtext(processed_img)
            
            for bbox, text, confidence in result:
                if confidence >= self.confidence_threshold:
                    # Extrair coordenadas
                    bbox_array = np.array(bbox)
                    x = int(bbox_array[:, 0].min())
                    y = int(bbox_array[:, 1].min())
                    width = int(bbox_array[:, 0].max() - x)
                    height = int(bbox_array[:, 1].max() - y)
                    
                    # Extrair possíveis IMEIs
                    imei_matches = self._extract_imei_patterns(text)
                    for imei in imei_matches:
                        detections.append(IMEIDetection(
                            imei=imei,
                            confidence=confidence,
                            raw_text=text,
                            x=x,
                            y=y,
                            width=width,
                            height=height
                        ))
        except Exception as e:
            logger.error(f"Error in EasyOCR extraction: {str(e)}")
        
        return detections
    
    def _extract_imei_patterns(self, text: str) -> List[str]:
        """Extrair padrões de IMEI do texto"""
        imei_pattern = r'\b\d{14,16}\b'
        matches = re.findall(imei_pattern, text)
        
        # Também tentar encontrar IMEIs com espaços ou hífens
        text_clean = re.sub(r'[\s\-\.]', '', text)
        if len(text_clean) >= 14:
            matches.extend(re.findall(imei_pattern, text_clean))
        
        return list(set(matches))  # Remover duplicatas
    
    def _is_valid_imei(self, imei: str) -> bool:
        """Validar se é um IMEI válido"""
        imei_clean = re.sub(r'[\s\-\.]', '', imei)
        
        # Validar tamanho
        if len(imei_clean) < settings.IMEI_MIN_LENGTH or len(imei_clean) > settings.IMEI_MAX_LENGTH:
            return False
        
        # Validar se é apenas números
        if not imei_clean.isdigit():
            return False
        
        # Validar checksum Luhn
        return self._validate_luhn(imei_clean)
    
    def _validate_luhn(self, imei: str) -> bool:
        """Validar usando algoritmo de Luhn"""
        try:
            digits = [int(d) for d in imei]
            # Inverter e processar
            total = 0
            for i, digit in enumerate(reversed(digits)):
                if i % 2 == 1:
                    digit *= 2
                    if digit > 9:
                        digit -= 9
                total += digit
            return total % 10 == 0
        except Exception:
            return False
    
    def _normalize_imei(self, imei: str) -> str:
        """Normalizar IMEI removendo caracteres especiais"""
        return re.sub(r'[\s\-\.]', '', imei)
    
    def get_device_info(self, imei: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Obter informações do dispositivo baseado no IMEI
        Retorna (brand, model)
        """
        # Implementação básica - pode ser expandida com banco de dados de IMEIs
        imei_clean = self._normalize_imei(imei)
        
        # TAC (Type Allocation Code) é os primeiros 8 dígitos
        tac = imei_clean[:8]
        
        # Mapeamento básico de TACs conhecidos
        tac_mapping = {
            "35278901": ("Apple", "iPhone 13"),
            "35278902": ("Apple", "iPhone 13 Pro"),
            "35278903": ("Apple", "iPhone 13 Pro Max"),
            "86625801": ("Samsung", "Galaxy S21"),
            "86625802": ("Samsung", "Galaxy S21+"),
            "86625803": ("Samsung", "Galaxy S21 Ultra"),
        }
        
        if tac in tac_mapping:
            return tac_mapping[tac]
        
        return None, None
