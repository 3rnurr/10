import json
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Annotated
from sqlalchemy import create_engine, Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func

app = FastAPI()

# --- CORS ---
origins = ["http://localhost:3000"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

SQLALCHEMY_DATABASE_URL = "sqlite:///./blog.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PostDB(Base):
    __tablename__ = "posts"

    id = Column(String, primary_key=True, index=True)
    text = Column(String)
    timestamp = Column(DateTime, default=func.now())
    owner_id = Column(String)
    owner_username = Column(String)

class LikeDB(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String)
    post_id = Column(String, ForeignKey("posts.id"))

Base.metadata.create_all(bind=engine)

# --- Фейковые данные пользователей ---
# В реальном приложении пароли должны быть хэшированы
FAKE_USERS_DB = {
    "user1": {"id": "1", "username": "user1", "password": "password1"},
    "user2": {"id": "2", "username": "user2", "password": "password2"},
}

# --- Pydantic модели ---
class Post(BaseModel):
    id: str
    text: str
    timestamp: datetime
    owner_id: str
    owner_username: str
    likes_count: int = 0

class PostCreate(BaseModel):
    text: str

class User(BaseModel):
    id: str
    username: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Аутентификация ---
async def get_current_user(authorization: Annotated[str, Header()]) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid scheme")

    token = authorization.split(" ")[1] # токен - это просто username
    user_data = FAKE_USERS_DB.get(token)

    if not user_data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    return User(**{"id": user_data["id"], "username": user_data["username"]})

@app.post("/api/login")
async def login(form_data: Dict[str, str]):
    username = form_data.get("username")
    password = form_data.get("password")
    user = FAKE_USERS_DB.get(username)
    if not user or user["password"] != password:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password")

    # В качестве токена просто возвращаем имя пользователя
    return {"access_token": user["username"], "token_type": "bearer", "user": {"id": user["id"], "username": user["username"]}}

# --- Эндпоинты для постов ---
@app.get("/api/posts", response_model=List[Post])
async def list_posts(db: Session = Depends(get_db)):
    posts = db.query(PostDB).order_by(PostDB.timestamp.desc()).all()
    result = []
    for post in posts:
        likes_count = db.query(LikeDB).filter(LikeDB.post_id == post.id).count()
        result.append(Post(
            id=post.id,
            text=post.text,
            timestamp=post.timestamp,
            owner_id=post.owner_id,
            owner_username=post.owner_username,
            likes_count=likes_count
        ))
    return result

@app.post("/api/posts", response_model=Post, status_code=201)
async def create_post(post_data: PostCreate, current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)):
    new_post = PostDB(
        id=str(uuid.uuid4()),
        text=post_data.text,
        timestamp=datetime.now(timezone.utc),
        owner_id=current_user.id,
        owner_username=current_user.username
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    return Post(
        id=new_post.id,
        text=new_post.text,
        timestamp=new_post.timestamp,
        owner_id=new_post.owner_id,
        owner_username=new_post.owner_username,
        likes_count=0
    )

@app.delete("/api/posts/{post_id}", status_code=204)
async def delete_post(post_id: str, current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)):
    post_to_delete = db.query(PostDB).filter(PostDB.id == post_id).first()

    if not post_to_delete:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")

    if post_to_delete.owner_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to delete this post")

    # Удаляем лайки к посту
    db.query(LikeDB).filter(LikeDB.post_id == post_id).delete()
    db.delete(post_to_delete)
    db.commit()

# --- Эндпоинты для лайков (пункт 2) ---
@app.post("/api/posts/{post_id}/like")
async def like_post(post_id: str, current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)):
    # Проверяем, что пост существует
    post = db.query(PostDB).filter(PostDB.id == post_id).first()
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")
    
    # Проверяем, не лайкнул ли уже пользователь этот пост
    existing_like = db.query(LikeDB).filter(LikeDB.post_id == post_id, LikeDB.user_id == current_user.id).first()
    if existing_like:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Already liked this post")
    
    # Создаем лайк
    new_like = LikeDB(user_id=current_user.id, post_id=post_id)
    db.add(new_like)
    db.commit()
    
    return {"message": "Post liked successfully"}

@app.delete("/api/posts/{post_id}/like")
async def unlike_post(post_id: str, current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(get_db)):
    # Проверяем, что пост существует
    post = db.query(PostDB).filter(PostDB.id == post_id).first()
    if not post:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")
    
    # Ищем лайк пользователя
    like = db.query(LikeDB).filter(LikeDB.post_id == post_id, LikeDB.user_id == current_user.id).first()
    if not like:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Post not liked")
    
    # Удаляем лайк
    db.delete(like)
    db.commit()
    
    return {"message": "Post unliked successfully"}

# --- Эндпоинт для постов пользователя (пункт 3) ---
@app.get("/api/users/{username}/posts", response_model=List[Post])
async def get_user_posts(username: str, db: Session = Depends(get_db)):
    posts = db.query(PostDB).filter(PostDB.owner_username == username).order_by(PostDB.timestamp.desc()).all()
    result = []
    for post in posts:
        likes_count = db.query(LikeDB).filter(LikeDB.post_id == post.id).count()
        result.append(Post(
            id=post.id,
            text=post.text,
            timestamp=post.timestamp,
            owner_id=post.owner_id,
            owner_username=post.owner_username,
            likes_count=likes_count
        ))
    return result