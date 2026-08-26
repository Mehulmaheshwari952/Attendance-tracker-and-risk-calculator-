import datetime
import os

from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..schemas import UserCreate, UserResponse, LoginRequest
import bcrypt
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

router = APIRouter(prefix="/auth", tags=["auth"])
@router.post("/signup", response_model=UserResponse)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    
    existing  = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
    new_user = User(
        email=user.email,
        password_hash=hashed_password.decode('utf-8'),
        term_start_date=user.term_start_date,
        term_end_date=user.term_end_date
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login")
def login(user: LoginRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if not existing:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not bcrypt.checkpw(user.password.encode('utf-8'), existing.password_hash.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    payload = {
        "sub": str(existing.id),
        "exp": datetime.datetime.now() + datetime.timedelta(hours=1)
    }
    jose_token = jwt.encode(payload, os.getenv("SECRET_KEY"), algorithm="HS256")
    return {"access_token": jose_token, "token_type": "bearer"}

