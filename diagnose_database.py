#!/usr/bin/env python3
"""
Script to diagnose database issues
"""

from models import Post, Comment, Session

def diagnose_database():
    session = Session()
    
    try:
        # Check posts
        posts = session.query(Post).all()
        print(f"Total posts: {len(posts)}")
        
        for post in posts:
            print(f"Post {post.id}:")
            print(f"  Message type: {type(post.message)}")
            print(f"  Message: {post.message[:100] if post.message else 'None'}")
            print(f"  Comments: {len(post.comments)}")
            
            # Check a few comments
            for i, comment in enumerate(post.comments[:2]):
                print(f"  Comment {i}: {type(comment.message)} - {comment.message[:50] if comment.message else 'None'}")
            
            print()
            
    except Exception as e:
        print(f"Error diagnosing database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    diagnose_database()