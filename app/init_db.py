import os
from dotenv import load_dotenv
from app.database import SessionLocal, engine, Base
from app.models import User, Patient, Doctor
from app.security import hash_password
from app.logging_config import logger

# Загружаем переменные из .env (если файл существует)
load_dotenv()

# Пароли берём из окружения, для разработки оставляем значения по умолчанию
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ChangeMeAdmin123!")
DOCTOR_PASSWORD = os.getenv("DOCTOR_PASSWORD", "ChangeMeDoctor123!")
DOCTOR1_PASSWORD = os.getenv("DOCTOR1_PASSWORD", "ChangeMeDoctor456!")
PATIENT_PASSWORD = os.getenv("PATIENT_PASSWORD", "ChangeMePatient123!")
PATIENT1_PASSWORD = os.getenv("PATIENT1_PASSWORD", "ChangeMePatient456!")

INITIAL_USERS = [
    {
        "username": "admin",
        "email": "admin@example.com",
        "full_name": "Admin User",
        "password": ADMIN_PASSWORD,
        "role": "admin"
    },
    {
        "username": "doctor",
        "email": "doctor@example.com",
        "full_name": "Doctor One",
        "password": DOCTOR_PASSWORD,
        "role": "doctor"
    },
    {
        "username": "doctor1",
        "email": "doctor1@example.com",
        "full_name": "Doctor Two",
        "password": DOCTOR1_PASSWORD,
        "role": "doctor"
    },
    {
        "username": "patient",
        "email": "patient@example.com",
        "full_name": "Patient One",
        "password": PATIENT_PASSWORD,
        "role": "patient"
    },
    {
        "username": "patient1",
        "email": "patient1@example.com",
        "full_name": "Patient Two",
        "password": PATIENT1_PASSWORD,
        "role": "patient"
    }
]

def init_db():
    """Создаёт таблицы и заполняет начальными пользователями, если их нет"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    for user_data in INITIAL_USERS:
        existing = db.query(User).filter(User.username == user_data["username"]).first()
        if not existing:
            hashed = hash_password(user_data["password"])
            new_user = User(
                username=user_data["username"],
                email=user_data["email"],
                full_name=user_data["full_name"],
                hashed_password=hashed,
                role=user_data["role"],
                is_active=True
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            if new_user.role == 'patient':
                patient = Patient(user_id=new_user.id, date_of_birth="", phone="", address="")
                db.add(patient)
            elif new_user.role == 'doctor':
                doctor = Doctor(user_id=new_user.id, specialization="", license_number="")
                db.add(doctor)
            db.commit()
            logger.info(f"Initial user created: {new_user.username} ({new_user.role})")
    db.close()