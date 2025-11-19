import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Story as StorySchema, Chapter as ChapterSchema, Bubble as BubbleSchema

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Health & Utilities
# -----------------------------
@app.get("/")
def read_root():
    return {"message": "Story App Backend Running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "Unknown"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# -----------------------------
# Story Endpoints
# -----------------------------
class StoryCreate(BaseModel):
    title: str
    author: Optional[str] = None
    cover_image: Optional[str] = None
    description: Optional[str] = None

class StoryOut(BaseModel):
    id: str
    title: str
    author: Optional[str] = None
    cover_image: Optional[str] = None
    description: Optional[str] = None

@app.post("/api/stories", response_model=dict)
def create_story(payload: StoryCreate):
    story = StorySchema(**payload.model_dump())
    _id = create_document("story", story)
    return {"id": _id}

@app.get("/api/stories", response_model=List[StoryOut])
def list_stories():
    docs = get_documents("story")
    out = []
    for d in docs:
        out.append(StoryOut(
            id=str(d.get("_id")),
            title=d.get("title"),
            author=d.get("author"),
            cover_image=d.get("cover_image"),
            description=d.get("description"),
        ))
    return out

@app.get("/api/stories/{story_id}", response_model=dict)
def get_story_detail(story_id: str):
    if not ObjectId.is_valid(story_id):
        raise HTTPException(status_code=400, detail="Invalid story id")
    story = db["story"].find_one({"_id": ObjectId(story_id)})
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    chapters = list(db["chapter"].find({"story_id": story_id}).sort("order", 1))
    # For each chapter, fetch bubbles sorted by order
    chapter_list = []
    for ch in chapters:
        bubbles = list(db["bubble"].find({"chapter_id": str(ch["_id"])}) .sort("order", 1))
        chapter_list.append({
            "id": str(ch["_id"]),
            "title": ch.get("title"),
            "order": ch.get("order", 0),
            "bubbles": [
                {
                    "id": str(b["_id"]),
                    "content_html": b.get("content_html"),
                    "order": b.get("order", 0)
                } for b in bubbles
            ]
        })
    return {
        "id": str(story["_id"]),
        "title": story.get("title"),
        "author": story.get("author"),
        "cover_image": story.get("cover_image"),
        "description": story.get("description"),
        "chapters": chapter_list
    }


# -----------------------------
# Chapter Endpoints
# -----------------------------
class ChapterCreate(BaseModel):
    story_id: str
    title: str
    order: int = 0

class ChapterOut(BaseModel):
    id: str
    story_id: str
    title: str
    order: int

@app.post("/api/chapters", response_model=dict)
def create_chapter(payload: ChapterCreate):
    # Ensure parent story exists
    if not ObjectId.is_valid(payload.story_id):
        raise HTTPException(status_code=400, detail="Invalid story id")
    if db["story"].count_documents({"_id": ObjectId(payload.story_id)}) == 0:
        raise HTTPException(status_code=404, detail="Parent story not found")
    chapter = ChapterSchema(**payload.model_dump())
    _id = create_document("chapter", chapter)
    return {"id": _id}

@app.get("/api/chapters", response_model=List[ChapterOut])
def list_chapters(story_id: str = Query(...)):
    docs = get_documents("chapter", {"story_id": story_id})
    docs = sorted(docs, key=lambda x: x.get("order", 0))
    return [
        ChapterOut(
            id=str(d.get("_id")),
            story_id=d.get("story_id"),
            title=d.get("title"),
            order=d.get("order", 0)
        ) for d in docs
    ]


# -----------------------------
# Bubble Endpoints
# -----------------------------
class BubbleCreate(BaseModel):
    chapter_id: str
    content_html: str
    order: int = 0

class BubbleOut(BaseModel):
    id: str
    chapter_id: str
    content_html: str
    order: int

@app.post("/api/bubbles", response_model=dict)
def create_bubble(payload: BubbleCreate):
    if not ObjectId.is_valid(payload.chapter_id):
        raise HTTPException(status_code=400, detail="Invalid chapter id")
    if db["chapter"].count_documents({"_id": ObjectId(payload.chapter_id)}) == 0:
        raise HTTPException(status_code=404, detail="Parent chapter not found")
    bubble = BubbleSchema(**payload.model_dump())
    _id = create_document("bubble", bubble)
    return {"id": _id}

@app.get("/api/bubbles", response_model=List[BubbleOut])
def list_bubbles(chapter_id: str = Query(...)):
    docs = get_documents("bubble", {"chapter_id": chapter_id})
    docs = sorted(docs, key=lambda x: x.get("order", 0))
    return [
        BubbleOut(
            id=str(d.get("_id")),
            chapter_id=d.get("chapter_id"),
            content_html=d.get("content_html"),
            order=d.get("order", 0)
        ) for d in docs
    ]


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
