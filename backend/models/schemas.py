from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict
from datetime import datetime
import uuid

from utils.timezone import get_jakarta_now

# User Models
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    role: str
    created_at: datetime = Field(default_factory=lambda: get_jakarta_now())

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    password: Optional[str] = None

# Product Models
class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    created_at: datetime = Field(default_factory=lambda: get_jakarta_now())

class ProductCreate(BaseModel):
    name: str

# Database Models
class Database(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_type: str
    file_size: int
    description: Optional[str] = None
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    uploaded_by: str
    uploaded_by_name: str
    uploaded_at: datetime = Field(default_factory=lambda: get_jakarta_now())
    file_path: str
    preview_data: Optional[dict] = None
    total_records: int = 0

class DatabaseCreate(BaseModel):
    description: Optional[str] = None
    product_id: str

class DatabaseProductUpdate(BaseModel):
    product_id: str

# Customer Record Models
class CustomerRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    database_id: str
    database_name: str
    product_id: str
    product_name: str
    row_number: int
    row_data: dict
    status: str = "available"
    whatsapp_status: Optional[str] = None
    whatsapp_status_updated_at: Optional[datetime] = None
    respond_status: Optional[str] = None
    respond_status_updated_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    assigned_at: Optional[datetime] = None
    request_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: get_jakarta_now())

class WhatsAppStatusUpdate(BaseModel):
    whatsapp_status: str

class RespondStatusUpdate(BaseModel):
    respond_status: str

# Download Request Models
class DownloadRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    database_id: str
    database_name: str
    record_ids: List[str]
    record_count: int
    requested_by: str
    requested_by_name: str
    status: str = "pending"
    requested_at: datetime = Field(default_factory=lambda: get_jakarta_now())
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reviewed_by_name: Optional[str] = None

class DownloadRequestCreate(BaseModel):
    database_id: str
    record_count: int

class DownloadHistory(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    database_id: str
    database_name: str
    downloaded_by: str
    downloaded_by_name: str
    downloaded_at: datetime = Field(default_factory=lambda: get_jakarta_now())

# Reserved Member Models
class ReservedMember(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_name: str
    product_id: str
    product_name: str
    staff_id: str
    staff_name: str
    status: str = "approved"
    created_by: str
    created_by_name: str
    created_at: datetime = Field(default_factory=lambda: get_jakarta_now())
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_by_name: Optional[str] = None

class ReservedMemberCreate(BaseModel):
    customer_name: str
    product_id: str
    staff_id: Optional[str] = None

# OMSET CRM Models
class OmsetRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    product_name: str
    staff_id: str
    staff_name: str
    record_date: str  # YYYY-MM-DD format
    customer_name: str
    customer_id: str
    nominal: float
    depo_kelipatan: float = 1.0
    depo_total: float
    keterangan: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: get_jakarta_now())
    updated_at: Optional[datetime] = None

class OmsetRecordCreate(BaseModel):
    product_id: str
    record_date: str
    customer_name: str
    customer_id: str
    nominal: float
    depo_kelipatan: float = 1.0
    keterangan: Optional[str] = None

class OmsetRecordUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_id: Optional[str] = None
    nominal: Optional[float] = None
    depo_kelipatan: Optional[float] = None
    keterangan: Optional[str] = None

# DB Bonanza Models
class BonanzaDatabase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    filename: str
    file_type: str
    total_records: int = 0
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    uploaded_by: str
    uploaded_by_name: str
    uploaded_at: datetime = Field(default_factory=lambda: get_jakarta_now())

class BonanzaRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    database_id: str
    database_name: str
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    row_number: int
    row_data: dict
    status: str = "available"
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    assigned_at: Optional[datetime] = None
    assigned_by: Optional[str] = None
    assigned_by_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: get_jakarta_now())

class BonanzaAssignment(BaseModel):
    record_ids: List[str]
    staff_id: str

class RandomBonanzaAssignment(BaseModel):
    database_id: str
    staff_id: str
    count: int
    exclude_reserved: bool = True

# Member WD Models (same structure as Bonanza)
class MemberWDDatabase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    filename: str
    file_type: str
    total_records: int = 0
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    uploaded_by: str
    uploaded_by_name: str
    uploaded_at: datetime = Field(default_factory=lambda: get_jakarta_now())

class MemberWDRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    database_id: str
    database_name: str
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    row_number: int
    row_data: dict
    status: str = "available"
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    assigned_at: Optional[datetime] = None
    assigned_by: Optional[str] = None
    assigned_by_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: get_jakarta_now())

# Notification Model
class Notification(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    type: str
    title: str
    message: str
    data: Optional[dict] = None
    read: bool = False
    created_at: datetime = Field(default_factory=lambda: get_jakarta_now())

# Bulk Operation Models
class BulkRequestAction(BaseModel):
    request_ids: List[str]
    action: str  # approve or reject

class BulkStatusUpdate(BaseModel):
    record_ids: List[str]
    whatsapp_status: Optional[str] = None
    respond_status: Optional[str] = None

class BulkDeleteRecords(BaseModel):
    record_ids: List[str]

# Batch Models
class BatchTitleUpdate(BaseModel):
    title: str

# User Layout Model
class UserLayoutUpdate(BaseModel):
    widget_order: List[str]
