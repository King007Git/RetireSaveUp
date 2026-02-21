import uuid
from sqlmodel import SQLModel, Field
from pydantic import EmailStr, BaseModel

class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True)

class User(UserBase, table=True):
    __tablename__ = "users"
    # FIX: Use default_factory to execute the function on creation
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, 
        primary_key=True,
        index=True
    )
    hashed_password: str

class UserCreate(UserBase):
    password: str = Field(max_length=72)

class UserResponse(UserBase):
    id: uuid.UUID # Make sure the response expects a UUID now too!

class Token(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class LoginSchema(BaseModel):
    email: EmailStr
    password: str