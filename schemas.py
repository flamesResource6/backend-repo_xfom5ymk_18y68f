"""
Database Schemas for the Story App

Each Pydantic model corresponds to a MongoDB collection with the lowercase
class name as the collection name:
- Story -> "story"
- Chapter -> "chapter"
- Bubble -> "bubble"
"""

from pydantic import BaseModel, Field
from typing import Optional, List

class Story(BaseModel):
    title: str = Field(..., description="Story title")
    author: Optional[str] = Field(None, description="Author name")
    cover_image: Optional[str] = Field(None, description="Optional cover URL")
    description: Optional[str] = Field(None, description="Short description")

class Chapter(BaseModel):
    story_id: str = Field(..., description="Parent story ID (ObjectId as string)")
    title: str = Field(..., description="Chapter title")
    order: int = Field(0, ge=0, description="Order within the story")

class Bubble(BaseModel):
    chapter_id: str = Field(..., description="Parent chapter ID (ObjectId as string)")
    content_html: str = Field(..., description="Rich text/HTML content for the bubble")
    order: int = Field(0, ge=0, description="Order within the chapter")
