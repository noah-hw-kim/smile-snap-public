from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    displayName: Optional[str] = Field(None, max_length=100)  # User's display name

class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    displayName: Optional[str] = Field(None, max_length=100)

class User(BaseModel):
    userId: str              # Your internal user ID
    email: str
    displayName: Optional[str] = None
    createdAt: datetime
    role: UserRole = UserRole.USER

class LoginUser(BaseModel):
    userId: str
    email: str
    displayName: Optional[str] = None
    role: UserRole

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: LoginUser

class UserDeleteResponse(BaseModel):
    message: str
    deletedUserId: str

class DiaryEntryCreate(BaseModel):
    filePath: str = Field(..., min_length=1, description="filePath to the uploaded image")
    location: Optional[dict] = Field(default=None)
    weather: Optional[dict] = Field(default=None)
    content: str = Field(..., min_length=1, max_length=5000, description="Diary entry content")
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DiaryEntryUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=5000)
    location: Optional[dict] = None
    weather: Optional[dict] = None

class DiaryEntry(BaseModel):
    entryId: str
    userId: str
    content: str
    imageUrl: Optional[str] = None
    location: Optional[dict] = None  # Make optional
    weather: Optional[dict] = None   # Make optional
    mode: str = "auto"
    createdAt: datetime
    editedAt: Optional[datetime] = None

class GenerateDiaryResponse(BaseModel):
    status: str
    diary_entry: DiaryEntry
    photo_id: str

class PhotoCreate(BaseModel):
    filePath: str
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PhotoUploadResponse(BaseModel):
    photoId: str
    photoUrl: Optional[str] = None

class Photo(BaseModel):
    userId: str
    photoId: str
    filePath: str
    photoUrl: Optional[str] = None
    createdAt: datetime