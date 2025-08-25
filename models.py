from sqlalchemy import Boolean, create_engine, Column, Integer, String, DateTime, Float, ForeignKey
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
    post_id = Column(String(100), ForeignKey('posts.post_id'), nullable=False)
    comment_id = Column(String(100), unique=True, nullable=False)
    message = Column(String(1000))
    created_time = Column(DateTime, nullable=False)
    sentiment_score = Column(Float, default=0.0)
    user_name = Column(String(200))  # Store the comment author's name

    # Relationship to post (many-to-one)
    post = relationship("Post", back_populates="comments")

    def __repr__(self):
        return f"<Comment(id={self.id}, comment_id='{self.comment_id}')>"

class Conversation(Base):
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(100), unique=True, nullable=False)
    snippet = Column(String(500))  # Last message preview
    updated_time = Column(DateTime, nullable=False)
    message_count = Column(Integer, default=0)
    participants = Column(String(500))  # JSON string of participant info
    can_reply = Column(Boolean, default=True)
    
    # Relationship to messages
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, conversation_id='{self.conversation_id}')>"

class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(100), ForeignKey('conversations.conversation_id'), nullable=False)
    message_id = Column(String(100), unique=True, nullable=False)
    sender_id = Column(String(100), nullable=False)
    sender_name = Column(String(200))
    recipient_id = Column(String(100), nullable=False)
    recipient_name = Column(String(200))
    message_text = Column(String(1000))
    created_time = Column(DateTime, nullable=False)
    has_attachments = Column(Boolean, default=False)
    
    # Relationship to conversation
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, message_id='{self.message_id}')>"