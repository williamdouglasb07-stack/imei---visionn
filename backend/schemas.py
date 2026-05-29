from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from typing import Optional, List
from enum import Enum


# ============= Auth Schemas =============
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: str
    password: str


# ============= IMEI Schemas =============
class IMEIResponse(BaseModel):
    id: str
    imei: str
    imei_normalized: str
    device_model: Optional[str]
    device_brand: Optional[str]
    confidence: float
    is_valid: bool
    extracted_at: datetime
    image_upload_id: str
    
    class Config:
        from_attributes = True


class IMEIDetailResponse(IMEIResponse):
    raw_text: Optional[str]
    x_position: Optional[int]
    y_position: Optional[int]
    width: Optional[int]
    height: Optional[int]
    manual_correction: Optional[str]


# ============= Image Upload Schemas =============
class ImageUploadResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    ocr_status: str
    uploaded_at: datetime
    processed_at: Optional[datetime]
    imeis_count: int = 0
    
    class Config:
        from_attributes = True


class ImageUploadDetailResponse(ImageUploadResponse):
    imeis: List[IMEIDetailResponse] = []


# ============= Search Schemas =============
class SearchQueryType(str, Enum):
    full = "full"
    partial = "partial"
    last_digits = "last_digits"


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=16)
    search_type: SearchQueryType = SearchQueryType.partial
    limit: int = Field(default=20, le=100)
    offset: int = Field(default=0, ge=0)


class SearchResult(BaseModel):
    total: int
    limit: int
    offset: int
    results: List[IMEIDetailResponse]


class SearchHistoryResponse(BaseModel):
    id: str
    query: str
    query_type: str
    results_count: int
    search_time_ms: float
    searched_at: datetime
    
    class Config:
        from_attributes = True


# ============= OCR Schemas =============
class OCRResult(BaseModel):
    imei: str
    confidence: float
    raw_text: str
    device_model: Optional[str] = None
    device_brand: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None


class ProcessImageResponse(BaseModel):
    image_id: str
    filename: str
    ocr_status: str
    imeis_found: int
    imeis: List[OCRResult]
    processing_time_ms: float


# ============= Validation Schemas =============
class ValidateIMEIRequest(BaseModel):
    imei: str


class ValidateIMEIResponse(BaseModel):
    imei: str
    is_valid: bool
    validation_method: str
    message: str


# ============= Batch Correction Schemas =============
class CorrectIMEIRequest(BaseModel):
    imei_id: str
    corrected_value: str


class CorrectIMEIResponse(BaseModel):
    id: str
    imei: str
    manual_correction: str
    updated_at: datetime


# ============= Dashboard Schemas =============
class DashboardStats(BaseModel):
    total_uploads: int
    total_imeis: int
    total_searches: int
    recent_uploads: int  # últimas 24 horas
    recent_imeis: int  # últimas 24 horas


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_uploads: List[ImageUploadResponse]
    recent_imeis: List[IMEIResponse]


# ============= Error Schemas =============
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    status_code: int
