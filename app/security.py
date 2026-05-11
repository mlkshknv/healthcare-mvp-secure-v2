import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt
from app.config import settings
from app.models import User
from app.logging_config import logger

def hash_password(password: str) -> str:        #используется bcrypt с солью (13 раундов)
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    salt = bcrypt.gensalt(rounds=13)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except ValueError as e:
        logger.error(f"Invalid hash format: {e}")
        return False
    except TypeError as e:
        logger.error(f"Invalid input type: {e}")
        return False
    
#токен подписывается алгоритмом HS256, срок жизни берётся из .env

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.JWTError:
        return None


def get_current_user_from_token(token: str, db) -> Optional[User]:
    payload = verify_token(token)
    if not payload:
        return None
    username = payload.get("sub")
    if not username:
        return None
    user = db.query(User).filter(User.username == username).first()
    return user