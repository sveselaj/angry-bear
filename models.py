from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database setup
database_url = os.getenv('DATABASE_URL', 'sqlite:///social_media.db')
engine = create_engine(database_url)
Session = sessionmaker(bind=engine)

Base = declarative_base()

class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    page_id = Column(String(100), nullable=False)  # The Facebook Page ID
    post_id = Column(String(100), unique=True, nullable=False)  # The Facebook Post ID
    message = Column(String(1000))  # The content of the post
    created_time = Column(DateTime, nullable=False)  # When the post was created
    
    # Relationship to comments (one-to-many)
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Post(id={self.id}, post_id='{self.post_id}', created_time='{self.created_time}')>"

class Comment(Base):
    __tablename__ = 'comments'
    
    id = Column(Integer, primary_key=True)
    post_id = Column(String(100), ForeignKey('posts.post_id'), nullable=False)  # Reference to the post
    comment_id = Column(String(100), unique=True, nullable=False)  # The Facebook Comment ID
    message = Column(String(1000))  # The comment text
    created_time = Column(DateTime, nullable=False)  # When the comment was created
    sentiment_score = Column(Float, default=0.0)  # Will be populated in Sprint 2
    
    # Relationship to post (many-to-one)
    post = relationship("Post", back_populates="comments")
    
    def __repr__(self):
        return f"<Comment(id={self.id}, comment_id='{self.comment_id}', sentiment={self.sentiment_score})>"
    

