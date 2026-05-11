from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import re
from pydantic import validator



# Валидация пароля
def validate_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError('Password must be at least 8 characters')
    if not re.search(r'[A-Z]', password):
        raise ValueError('Password must contain at least one uppercase letter')
    if not re.search(r'[a-z]', password):
        raise ValueError('Password must contain at least one lowercase letter')
    if not re.search(r'\d', password):
        raise ValueError('Password must contain at least one digit')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError('Password must contain at least one special character')
    return password

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str  
    full_name: str = Field(..., min_length=1, max_length=100)
    password: str
    role: str  # 'patient', 'doctor', 'admin'
    
    @validator('password')
    def check_password(cls, v):
        return validate_password(v)
    
    @validator('role')
    def check_role(cls, v):
        if v.lower() not in ['patient', 'doctor', 'admin']:
            raise ValueError('Role must be patient, doctor, or admin')
        return v.lower()

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Модели для Appointment
class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    appointment_time: str = Field(..., pattern=r'^\d{2}:\d{2}$')
    reason: str = Field(..., max_length=500)

class AppointmentOut(AppointmentCreate):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# Модели для MedicalRecord
class MedicalRecordInput(BaseModel):   
    patient_id: int = Field(..., gt=0)
    doctor_id: int = Field(..., gt=0)
    appointment_id: Optional[int] = None
    diagnosis: str = Field(..., max_length=200)
    treatment: str = Field(..., max_length=1000)
    prescription: Optional[str] = Field(None, max_length=1000)

class MedicalRecordOut(MedicalRecordInput):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Отчёт по пациенту
class PatientReportOut(BaseModel):
    patient_id: int
    patient_name: str
    appointments: list[AppointmentOut]
    medical_records: list[MedicalRecordOut]

class MedicalRecordCreate(BaseModel):
    treatment: str
    @validator('treatment')
    def check_length(cls, v):
        if len(v) > 10000:
            raise ValueError('Treatment too long')
        return v
    
