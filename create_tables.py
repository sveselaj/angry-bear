from sqlalchemy import create_engine
from models import Base, Post, Comment
import os
from dotenv import load_dotenv

def init_db():
    # Load environment variables
    load_dotenv()
    
    # Get database URL from environment or use SQLite as default
    database_url = os.getenv('DATABASE_URL', 'sqlite:///social_media.db')
    
    # Create engine
    engine = create_engine(database_url, echo=True)  # echo=True for debugging
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    print(f"Database tables created successfully at: {database_url}")
    return engine

if __name__ == "__main__":
    init_db()