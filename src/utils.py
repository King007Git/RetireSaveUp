from src.connection.session import get_db
from src.models.userModel import User
from src.security.auth import (
    verify_token, oauth2_scheme
)
from fastapi import Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    payload = verify_token(token, "access")
    email: str = payload.get("sub")
    
    result = await db.exec(select(User).where(User.email == email))
    user = result.first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user