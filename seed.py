"""
seed.py – заполнение базы данных тестовыми данными (200+ записей)
Запуск: python seed.py
"""

from app.database import SessionLocal
from app.models import User, Patient, Doctor, Appointment, MedicalRecord
from app.security import hash_password
from datetime import datetime, timedelta
import random

def create_test_data():
    db = SessionLocal()
    
    # Очистка старых данных (опционально, закомментируйте если нужно)
    db.query(MedicalRecord).delete()
    db.query(Appointment).delete()
    db.query(Patient).delete()
    db.query(Doctor).delete()
    db.query(User).delete()
    db.commit()
    
    print("Создание пользователей...")
    users_data = [
        {"username": "admin", "email": "admin@test.com", "full_name": "Admin", "password": "Adminpass123!", "role": "admin"},
        {"username": "doctor1", "email": "doctor1@test.com", "full_name": "Doctor One", "password": "Doctorpass123!", "role": "doctor"},
        {"username": "doctor2", "email": "doctor2@test.com", "full_name": "Doctor Two", "password": "Doctorpass123!", "role": "doctor"},
    ]
    # Создаём 100 пациентов
    for i in range(1, 101):
        users_data.append({
            "username": f"patient{i}",
            "email": f"patient{i}@test.com",
            "full_name": f"Patient {i}",
            "password": "Patientpass123!",
            "role": "patient"
        })
    
    user_objects = []
    for u in users_data:
        existing = db.query(User).filter(User.username == u["username"]).first()
        if not existing:
            new_user = User(
                username=u["username"],
                email=u["email"],
                full_name=u["full_name"],
                hashed_password=hash_password(u["password"]),
                role=u["role"],
                is_active=True
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            user_objects.append(new_user)
        else:
            user_objects.append(existing)
    
    print("Создание профилей пациентов и врачей...")
    # Профили пациентов
    patients = []
    for user in user_objects:
        if user.role == "patient":
            existing = db.query(Patient).filter(Patient.user_id == user.id).first()
            if not existing:
                patient = Patient(user_id=user.id, date_of_birth=f"19{random.randint(60,99)}-{random.randint(1,12)}-{random.randint(1,28)}", phone=f"+7{random.randint(7000000000,7999999999)}", address=f"Address {user.id}")
                db.add(patient)
                db.commit()
                db.refresh(patient)
                patients.append(patient)
            else:
                patients.append(existing)
    
    doctors = []
    for user in user_objects:
        if user.role == "doctor":
            existing = db.query(Doctor).filter(Doctor.user_id == user.id).first()
            if not existing:
                doctor = Doctor(user_id=user.id, specialization="Therapist", license_number=f"LIC{random.randint(10000,99999)}")
                db.add(doctor)
                db.commit()
                db.refresh(doctor)
                doctors.append(doctor)
            else:
                doctors.append(existing)
    
    print("Создание приёмов (200+)...")
    appointments = []
    # Для каждого врача создаём приёмы с разными пациентами
    for doctor in doctors:
        for _ in range(30):  # 30 приёмов на врача +/- (2 врача = 60)
            patient = random.choice(patients)
            apt_date = (datetime.now() + timedelta(days=random.randint(-30, 90))).strftime("%Y-%m-%d")
            apt_time = f"{random.randint(8,18)}:{random.randint(0,59):02d}"
            appointment = Appointment(
                patient_id=patient.id,
                doctor_id=doctor.id,
                appointment_date=apt_date,
                appointment_time=apt_time,
                reason=random.choice(["Headache", "Fever", "Checkup", "Cough", "Pain", "Vaccination"]),
                status=random.choice(["scheduled", "completed", "cancelled"])
            )
            db.add(appointment)
            appointments.append(appointment)
    db.commit()
    
    print("Создание медицинских назначений...")
    diagnoses = ["Flu", "Common cold", "Hypertension", "Diabetes", "Fracture", "COVID-19", "Allergy"]
    treatments = ["Rest", "Medication", "Surgery", "Therapy", "Observation"]
    for appointment in appointments:
        # Создаём назначение для 80% приёмов
        if random.random() < 0.8:
            record = MedicalRecord(
                patient_id=appointment.patient_id,
                doctor_id=appointment.doctor_id,
                appointment_id=appointment.id,
                diagnosis=random.choice(diagnoses),
                treatment=random.choice(treatments),
                prescription=f"Prescription for {appointment.id}"
            )
            db.add(record)
    db.commit()
    
    print(f"Итоги: Пользователей: {len(user_objects)}, Пациентов: {len(patients)}, Врачей: {len(doctors)}, Приёмов: {len(appointments)}")
    db.close()
    print("Готово!")

if __name__ == "__main__":
    create_test_data()