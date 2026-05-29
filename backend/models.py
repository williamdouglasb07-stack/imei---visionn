from sqlalchemy import Column, String, Integer, DateTime, Float, Boolean, LargeBinary, ForeignKey, Index, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class User(Base):
    """Modelo de usuário"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    uploads = relationship("ImageUpload", back_populates="user", cascade="all, delete-orphan")
    imeis = relationship("IMEI", back_populates="user", cascade="all, delete-orphan")
    search_history = relationship("SearchHistory", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_email', 'email'),
        Index('idx_username', 'username'),
    )


class ImageUpload(Base):
    """Modelo de upload de imagens"""
    __tablename__ = "image_uploads"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(50), nullable=False)
    image_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA256
    perceptual_hash = Column(String(64), nullable=True, index=True)  # Para detecção de duplicatas
    ocr_status = Column(String(20), default="pending")  # pending, processing, completed, failed
    ocr_error = Column(String(500), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="uploads")
    imeis = relationship("IMEI", back_populates="image_upload", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_image_hash', 'image_hash'),
        Index('idx_perceptual_hash', 'perceptual_hash'),
        Index('idx_uploaded_at', 'uploaded_at'),
    )


class IMEI(Base):
    """Modelo de IMEI extraído"""
    __tablename__ = "imeis"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    image_upload_id = Column(String(36), ForeignKey("image_uploads.id"), nullable=False)
    imei = Column(String(16), nullable=False, index=True)
    imei_normalized = Column(String(16), nullable=False, index=True)  # sem espaços/caracteres especiais
    confidence = Column(Float, default=0.0)
    raw_text = Column(Text, nullable=True)  # Texto bruto do OCR
    device_model = Column(String(500), nullable=True)
    device_brand = Column(String(100), nullable=True)
    is_valid = Column(Boolean, default=False)
    validation_source = Column(String(50), nullable=True)  # manual, luhn, ai
    manual_correction = Column(String(16), nullable=True)
    x_position = Column(Integer, nullable=True)  # Posição X da detecção
    y_position = Column(Integer, nullable=True)  # Posição Y da detecção
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    extracted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="imeis")
    image_upload = relationship("ImageUpload", back_populates="imeis")
    
    __table_args__ = (
        Index('idx_user_id_imei', 'user_id', 'imei_normalized'),
        Index('idx_imei_normalized', 'imei_normalized'),
        Index('idx_device_model', 'device_model'),
        Index('idx_extracted_at', 'extracted_at'),
    )


class SearchHistory(Base):
    """Modelo de histórico de buscas"""
    __tablename__ = "search_history"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    query = Column(String(256), nullable=False)
    query_type = Column(String(20), default="full")  # full, partial, last_digits
    results_count = Column(Integer, default=0)
    search_time_ms = Column(Float, default=0.0)
    searched_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="search_history")
    
    __table_args__ = (
        Index('idx_user_id_searched_at', 'user_id', 'searched_at'),
        Index('idx_query', 'query'),
    )


class DuplicateImage(Base):
    """Modelo para rastrear imagens duplicadas"""
    __tablename__ = "duplicate_images"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_image_id = Column(String(36), ForeignKey("image_uploads.id"), nullable=False)
    duplicate_image_id = Column(String(36), ForeignKey("image_uploads.id"), nullable=False)
    similarity_score = Column(Float, default=0.0)  # 0-1
    detected_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_original_image_id', 'original_image_id'),
        Index('idx_duplicate_image_id', 'duplicate_image_id'),
    )
