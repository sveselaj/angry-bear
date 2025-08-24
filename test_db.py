from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Post, Comment
from datetime import datetime
from create_tables import init_db

def test_database():
    # Initialize database
    engine = init_db()
    
    # Create a session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Create a test post
        test_post = Post(
            page_id="1234567890",
            post_id="9876543210",
            message="This is a test post message",
            created_time=datetime.now()
        )
        
        # Create a test comment
        test_comment = Comment(
            post_id="9876543210",
            comment_id="5555555555",
            message="This is a test comment",
            created_time=datetime.now(),
            sentiment_score=0.5
        )
        
        # Add to session and commit
        session.add(test_post)
        session.add(test_comment)
        session.commit()
        
        # Query the database
        posts = session.query(Post).all()
        comments = session.query(Comment).all()
        
        print("Posts in database:")
        for post in posts:
            print(f"  - {post}")
            
        print("Comments in database:")
        for comment in comments:
            print(f"  - {comment}")
            
        # Test relationship
        post_with_comments = session.query(Post).filter_by(post_id="9876543210").first()
        print(f"Post comments: {post_with_comments.comments}")
        
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    test_database()