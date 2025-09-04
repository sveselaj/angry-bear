#!/usr/bin/env python3
"""
Debug script to test Facebook API connection
"""

import os
from dotenv import load_dotenv
from fb_api import FacebookAPI

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize Facebook API
    fb_api = FacebookAPI()
    
    print("=== Facebook API Debug ===")
    
    
    # Verify credentials
    if not fb_api.verify_credentials():
        print("Credentials verification failed")
        return
    
    # Test simple API call
    if not fb_api.test_simple_api_call():
        print("Simple API call failed")
        return
    
    # Try to fetch a few posts
    print("\n=== Testing Posts Fetch ===")
    posts = fb_api.fetch_posts_with_comments(limit=5, comments_per_post=10)
    
    if posts:
        print(f"Successfully fetched {len(posts)} posts")
        for i, post in enumerate(posts):
            print(f"Post {i+1}: {post.get('id')}")
            if 'comments' in post:
                print(f"  Comments: {len(post['comments'].get('data', []))}")
    else:
        print("Failed to fetch posts")

if __name__ == "__main__":
    main()