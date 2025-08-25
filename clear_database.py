#!/usr/bin/env python3
"""
Script to clear all data from the database while keeping the table structure intact.
"""

from models import Base, Session, Post, Comment, Conversation, Message
from sqlalchemy import text

def clear_database():
    # Create a session
    session = Session()
    
    try:
        print("Starting database cleanup...")
        
        # Delete data in the correct order to respect foreign key constraints
        # First delete child tables, then parent tables
        session.query(Message).delete()
        session.query(Comment).delete()
        session.query(Conversation).delete()
        session.query(Post).delete()
        
        # Commit the changes
        session.commit()
        print("All data has been successfully deleted from the database.")
        
    except Exception as e:
        session.rollback()
        print(f"Error occurred while clearing database: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    # Confirm before proceeding
    confirmation = input("Are you sure you want to delete ALL data from the database? This cannot be undone. (y/N): ")
    
    if confirmation.lower() == 'y':
        clear_database()
    else:
        print("Operation cancelled.")