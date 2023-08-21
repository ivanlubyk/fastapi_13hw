from datetime import date
from pydantic import BaseModel, Field, EmailStr
from typing import Optional



class EmailSchema(BaseModel):
    email: EmailStr

class UserSchema(BaseModel):
    username: str = Field(min_length=6, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=14)





class UserResponseSchema(BaseModel):
    id: int
    username: str
    email: str
    avatar: str

    class Config:
        from_attributes = True



class TokenModel(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"




# Схема для створення контакту
class ContactCreateModel(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    birthday: date

# Схема для оновлення контакту
class ContactUpdateModel(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    birthday: Optional[date] = None

# Схема для відображення контакту
class ContactModel(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    birthday: date

class ResetPasswordRequest(BaseModel):
    email: str
    token: str
    new_password: str

    class ConfigDict:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "token": "your_reset_token_here",
                "new_password": "new_secure_password",
            }
        }