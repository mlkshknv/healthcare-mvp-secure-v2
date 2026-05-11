from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserLogin, Token, UserOut
from app.security import hash_password, verify_password, create_access_token
from app.logging_config import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.security import OAuth2PasswordRequestForm



limiter = Limiter(key_func=get_remote_address)


router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=UserOut, status_code=201)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing:
        logger.warning("Registration failed: username or email already exists - %s", user_data.username)
        raise HTTPException(400, "Username or email already registered")
    
    hashed = hash_password(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed,
        role=user_data.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

   

    # создается профиль в зависимости от роли
    if new_user.role == 'patient':
        from app.models import Patient
        patient = Patient(user_id=new_user.id, date_of_birth="", phone="", address="")
        db.add(patient)
        db.commit()
        logger.info(f"Patient profile created for user {new_user.username}")
    elif new_user.role == 'doctor':
        from app.models import Doctor
        doctor = Doctor(user_id=new_user.id, specialization="", license_number="")
        db.add(doctor)
        db.commit()
        logger.info(f"Doctor profile created for user {new_user.username}")

    return new_user



@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(
    request: Request,
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for username: {user_data.username}")
        raise HTTPException(401, "Invalid username or password")
    if not user.is_active:
        logger.warning(f"Disabled account login attempt: {user_data.username}")
        raise HTTPException(403, "Account disabled")
    
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    logger.info(f"User logged in: {user.username}")
    return {"access_token": access_token}
    