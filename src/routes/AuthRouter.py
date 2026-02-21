from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.connection.session import get_db
from src.models.userModel import User, UserCreate, UserResponse, Token
from src.security.auth import (
    get_password_hash, verify_password, create_access_token, 
    create_refresh_token
)
from config import settings
from src.utils import get_current_user

router = APIRouter(
    prefix=f"/blackrock/challenge/{settings.VERSION}",
    tags=['users']
)

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.exec(select(User).where(User.email == user.email))
    if result.first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pwd = get_password_hash(user.password)
    # SQLModel unpacks the fields beautifully
    new_user = User(email=user.email, hashed_password=hashed_pwd)
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.exec(select(User).where(User.email == form_data.username))
    user = result.first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.get("/protected", response_model=dict)
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.email}, you are authenticated!"}