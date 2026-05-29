from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Configurações da aplicação"""
    
    # API
    PROJECT_NAME: str = "IMEI Vision"
    PROJECT_VERSION: str = "1.0.0"
    DESCRIPTION: str = "Sistema de OCR e busca de IMEIs"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "postgresql://imei_user:imei_password@db:5432/imei_vision"
    DATABASE_ECHO: bool = False
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: list = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]
    
    # Upload
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR: str = "/app/uploads"
    ALLOWED_EXTENSIONS: list = ["jpg", "jpeg", "png", "gif", "webp"]
    
    # OCR
    OCR_ENGINE: str = "paddleocr"  # paddleocr, easyocr, tesseract
    OCR_LANGUAGE: str = "en"
    OCR_CONFIDENCE_THRESHOLD: float = 0.3
    
    # IMEI Validation
    IMEI_MIN_LENGTH: int = 14
    IMEI_MAX_LENGTH: int = 16
    
    # File Storage
    TEMP_DIR: str = "/app/temp"
    HASH_ALGORITHM: str = "sha256"
    
    # JWT
    TOKEN_ALGORITHM: str = "HS256"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
