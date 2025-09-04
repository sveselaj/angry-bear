from sqlalchemy import Boolean, create_engine, Column, Integer, String, DateTime, Float, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import json
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
    page_id = Column(String(100), nullable=False)
    post_id = Column(String(100), unique=True, nullable=False)
    message = Column(String(1000))
    created_time = Column(DateTime, nullable=False)
    avg_sentiment = Column(Float, default=0.0)
    trending_topics = Column(String(500))
    
    # Relationship to comments
    comments = relationship("Comment", backref="post_rel", lazy="select")
    
    @property
    def facebook_url(self):
        if self.post_id and self.page_id:
            if self.post_id.startswith(self.page_id):
                return f"https://www.facebook.com/{self.post_id}"
            else:
                return f"https://www.facebook.com/{self.page_id}/posts/{self.post_id.split('_')[-1]}"
        elif self.post_id:
            return f"https://www.facebook.com/{self.post_id}"
        else:
            return "#"

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
    sentiment_category = Column(String(20), default='neutral')
    user_name = Column(String(200))
    keywords = Column(String(500))
    
    # New fields for auto-reply
    ai_responded = Column(Boolean, default=False)
    ai_response = Column(Text)
    ai_evaluation = Column(Text)  # Store JSON evaluation data
    
    # Relationship to replies
    replies = relationship("CommentReply", backref="comment_rel", lazy="select")
    
    # Relationship to post
    post = relationship("Post", back_populates="comments")

    def __repr__(self):
        return f"<Comment(id={self.id}, comment_id='{self.comment_id}')>"

class Conversation(Base):
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(100), unique=True, nullable=False)
    snippet = Column(String(500))
    updated_time = Column(DateTime, nullable=False)
    message_count = Column(Integer, default=0)
    participants = Column(String(500))
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

class CommentReply(Base):
    __tablename__ = 'comment_replies'
    
    id = Column(Integer, primary_key=True)
    comment_id = Column(String(100), ForeignKey('comments.comment_id'), nullable=False)
    reply_id = Column(String(100), unique=True, nullable=False)
    message = Column(String(1000))
    created_time = Column(DateTime, nullable=False)
    user_name = Column(String(200))
    ai_generated = Column(Boolean, default=False)
    
    # New field to track if reply was posted to Facebook
    posted_to_facebook = Column(Boolean, default=False)
    post_error = Column(Text)

    def __repr__(self):
        return f"<CommentReply(id={self.id}, reply_id='{self.reply_id}')>"

class AutoReplySettings(Base):
    __tablename__ = 'auto_reply_settings'
    
    id = Column(Integer, primary_key=True)
    enabled = Column(Boolean, default=False)
    response_template = Column(Text, default="")
    min_confidence = Column(Float, default=0.7)
    max_daily_replies = Column(Integer, default=50)
    excluded_keywords = Column(Text, default="")  # JSON array of keywords
    reply_to_negative = Column(Boolean, default=True)
    reply_to_questions = Column(Boolean, default=True)
    reply_to_compliments = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<AutoReplySettings(id={self.id}, enabled={self.enabled})>"

class ResponseDraft(Base):
    __tablename__ = 'response_drafts'
    
    id = Column(Integer, primary_key=True)
    comment_id = Column(String(100), ForeignKey('comments.comment_id'), nullable=False)
    message = Column(Text, nullable=False)
    generated_at = Column(DateTime, default=datetime.now)
    posted = Column(Boolean, default=False)
    posted_at = Column(DateTime, nullable=True)
    posted_id = Column(String(100), nullable=True)  # Facebook ID if posted
    post_error = Column(Text, nullable=True)
    
    # Relationship to comment
    comment = relationship("Comment", backref="response_drafts")
    
    def __repr__(self):
        return f"<ResponseDraft(id={self.id}, comment_id='{self.comment_id}', posted={self.posted})>"
# Create all tables
#Base.metadata.create_all(engine)

# Add to your models.py
class OpenAILog(Base):
    __tablename__ = 'openai_logs'
    
    id = Column(Integer, primary_key=True)
    comment_id = Column(String(100), ForeignKey('comments.comment_id'), nullable=True)
    endpoint = Column(String(50), nullable=False)  # 'evaluate_comment' or 'detailed_analysis'
    model = Column(String(50), nullable=False)     # 'gpt-3.5-turbo', etc.
    tokens_used = Column(Integer, default=0)
    processing_time = Column(Float, default=0.0)   # in seconds
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationship to comment
    comment = relationship("Comment", backref="openai_logs")
    
    def __repr__(self):
        return f"<OpenAILog(id={self.id}, endpoint='{self.endpoint}', tokens={self.tokens_used})>"
    

class MessageResponse(Base):
    __tablename__ = 'message_responses'
    
    id = Column(Integer, primary_key=True)
    message_id = Column(String(100), ForeignKey('messages.message_id'), nullable=False)
    response_text = Column(Text, nullable=False)
    generated_at = Column(DateTime, default=datetime.now)
    sent_at = Column(DateTime, nullable=True)
    ai_generated = Column(Boolean, default=True)
    tokens_used = Column(Integer, default=0)
    processing_time = Column(Float, default=0.0)
    
    # Relationship to original message
    message = relationship("Message", backref="ai_responses")
    
    def __repr__(self):
        return f"<MessageResponse(id={self.id}, message_id='{self.message_id}')>"