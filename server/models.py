from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

class UserCreate(BaseModel):
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    displayName: Optional[str] = Field(None, max_length=100)  # User's display name
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    role: UserRole = Field(default=UserRole.USER, description="User role: user or admin")

class UserUpdate(BaseModel):
    email: Optional[str] = None
    displayName: Optional[str] = None

class User(BaseModel):
    userId: str              # Your internal user ID
    email: str
    displayName: str = None
    createdAt: datetime
    role: UserRole = UserRole.USER

class DiaryEntryCreate(BaseModel):
    filePath: str = Field(..., min_length=1, description="filePath to the uploaded image")
    location: Optional[dict] = Field(default=None)
    weather: Optional[dict] = Field(default=None)
    content: str = Field(..., min_length=1, max_length=5000, description="Diary entry content")
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DiaryEntryUpdate(BaseModel):
    content: Optional[str] = None  # Now allowed
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

class PhotoCreate(BaseModel):
    filePath: str
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Photo(BaseModel):
    userId: str
    photoId: str
    filePath: str
    photoUrl: Optional[str] = None
    createdAt: datetime