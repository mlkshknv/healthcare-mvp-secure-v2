from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, Patient, Doctor, Appointment, MedicalRecord
from app.schemas import (
    AppointmentCreate, AppointmentOut,
    MedicalRecordInput, MedicalRecordOut,
    PatientReportOut
)
from app.security import verify_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.logging_config import logger
import csv
from fastapi.responses import StreamingResponse
import io
from app.schemas import UserOut


router = APIRouter(prefix="/api/medical", tags=["medical"])
security = HTTPBearer()


# проверка токена и ошибки
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        logger.warning("Invalid token attempt")
        raise HTTPException(401, "Invalid authentication credentials")
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user

@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "role": current_user.role, "full_name": current_user.full_name}


# админ имеет право на все
def require_role(required_role: str):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role and current_user.role != 'admin':
            logger.warning(f"Access denied: {current_user.username} (role {current_user.role}) tried to access {required_role} resource")
            raise HTTPException(403, "Insufficient permissions")
        return current_user
    return role_checker

@router.get("/me/doctor")
def get_my_doctor_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != 'doctor':
        raise HTTPException(403, "Not a doctor")
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(404, "Doctor profile not found")
    return {"doctor_id": doctor.id, "specialization": doctor.specialization}

@router.get("/me/patient")
def get_my_patient_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != 'patient':
        raise HTTPException(403, "Not a patient")
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(404, "Patient profile not found")
    return {
        "patient_id": patient.id,
        "user_id": patient.user_id,
        "date_of_birth": patient.date_of_birth,
        "phone": patient.phone,
        "address": patient.address
    }

# Appointments 
@router.post("/appointments", response_model=AppointmentOut)
def create_appointment(
    apt: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor"))
):
    # Проверка, что doctor_id соответствует текущему врачу (если не admin)
    if current_user.role != 'admin':
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or doctor.id != apt.doctor_id:
            raise HTTPException(403, "You can only create appointments for yourself")
    new_apt = Appointment(**apt.dict(), status="scheduled")
    db.add(new_apt)
    db.commit()
    db.refresh(new_apt)
    logger.info(f"Appointment created: id {new_apt.id} by doctor {current_user.username}")
    return new_apt

# пациент видит только свои, врач видит свои, админ видит все
@router.get("/appointments", response_model=List[AppointmentOut])
def list_appointments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Appointment)          # базовый запрос

    if current_user.role == 'patient':
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient:
            return []
        query = query.filter(Appointment.patient_id == patient.id)

    elif current_user.role == 'doctor':
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor:
            return []
        query = query.filter(Appointment.doctor_id == doctor.id)

    # admin – запрос остаётся без фильтрации

    appointments = query.offset(skip).limit(limit).all()
    return appointments


@router.get("/appointments/{appointment_id}", response_model=AppointmentOut)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    apt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not apt:
        raise HTTPException(404, "Appointment not found")
    # Проверка доступа
    if current_user.role == 'patient':
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient or apt.patient_id != patient.id:
            raise HTTPException(403, "Access denied")
    elif current_user.role == 'doctor':
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or apt.doctor_id != doctor.id:
            raise HTTPException(403, "Access denied")
    # admin всё видит
    return apt

# Medical Records  SOURCE
@router.post("/records", response_model=MedicalRecordOut)
def create_medical_record(
    record: MedicalRecordInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("doctor"))
):
    # Проверка, что doctor_id соответствует текущему врачу
    if current_user.role != 'admin':
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or doctor.id != record.doctor_id:
            raise HTTPException(403, "You can only create records for yourself")
    # Проверка, что врач может создать назначение только для пациента, с которым у него уже был приём
    if current_user.role == 'doctor':
        doctor_obj = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if doctor_obj:
            # Есть ли хотя бы один приём у этого врача с этим пациентом?
            appointment_exists = db.query(Appointment).filter(
                Appointment.doctor_id == doctor_obj.id,
                Appointment.patient_id == record.patient_id
            ).first()
            if not appointment_exists:
                logger.warning(f"Doctor {current_user.username} tried to create record for patient {record.patient_id} without prior appointment")
                raise HTTPException(403, "You can only create medical records for patients you have appointments with")
    new_record = MedicalRecord(**record.dict())
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    logger.info(f"Medical record created: id {new_record.id} for patient {new_record.patient_id} by doctor {current_user.username}")
    return new_record

@router.get("/records", response_model=List[MedicalRecordOut])
def list_medical_records(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(MedicalRecord)
    if current_user.role == 'patient':
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if patient:
            query = query.filter(MedicalRecord.patient_id == patient.id)
        else:
            return []
    elif current_user.role == 'doctor':
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if doctor:
            query = query.filter(MedicalRecord.doctor_id == doctor.id)
        else:
            return []
    # Пагинация
    records = query.offset(skip).limit(limit).all()
    return records

@router.get("/records/{record_id}", response_model=MedicalRecordOut)
def get_medical_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(404, "Record not found")
    if current_user.role == 'patient':
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient or record.patient_id != patient.id:
            raise HTTPException(403, "Access denied")
    elif current_user.role == 'doctor':
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor or record.doctor_id != doctor.id:
            raise HTTPException(403, "Access denied")
    return record

# Reports 
@router.get("/reports/patient/{patient_id}", response_model=PatientReportOut)
def get_patient_report(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Проверка роли: только doctor или admin
    if current_user.role not in ['doctor', 'admin']:
        raise HTTPException(403, "Access denied")
    
    # Находим пациента
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")
    
    # Если врач, проверяем, что он лечит этого пациента (есть приём)
    if current_user.role == 'doctor':
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor:
            raise HTTPException(403, "Doctor profile not found")
        appointment_exists = db.query(Appointment).filter(
            Appointment.doctor_id == doctor.id,
            Appointment.patient_id == patient_id
        ).first()
        if not appointment_exists:
            raise HTTPException(403, "You can only view reports of your own patients")
    
    # Получаем данные
    user = db.query(User).filter(User.id == patient.user_id).first()
    appointments = db.query(Appointment).filter(Appointment.patient_id == patient_id).all()
    records = db.query(MedicalRecord).filter(MedicalRecord.patient_id == patient_id).all()
    
    # Преобразуем в Pydantic (если нужно)
    from app.schemas import AppointmentOut, MedicalRecordOut
    appointments_out = [AppointmentOut.model_validate(a) for a in appointments]
    records_out = [MedicalRecordOut.model_validate(r) for r in records]
    
    return PatientReportOut(
        patient_id=patient_id,
        patient_name=user.full_name,
        appointments=appointments_out,
        medical_records=records_out
    )
 

def sanitize_csv_field(value):
    if isinstance(value, str) and value.startswith(('=', '+', '-', '@')):
        return "'" + value
    return value

@router.get("/export/csv")
def export_csv(current_user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    appointments = db.query(Appointment).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "patient_id", "doctor_id", "reason"])
    for a in appointments:
        writer.writerow([a.id, a.patient_id, a.doctor_id, a.reason])
    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=appointments.csv"
    return response

@router.patch("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == current_user.id:
        raise HTTPException(400, "Cannot deactivate your own account")
    user.is_active = False
    db.commit()
    logger.info(f"User {user_id} ({user.username}) deactivated by admin {current_user.username}")
    return {"detail": "User deactivated"}

@router.patch("/users/{user_id}/activate")
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == current_user.id:
        raise HTTPException(400, "Cannot activate your own account")
    user.is_active = True
    db.commit()
    logger.info(f"User {user_id} ({user.username}) activated by admin {current_user.username}")
    return {"detail": "User activated"}
@router.get("/users", response_model=List[UserOut])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    users = db.query(User).all()
    return users
