#!/usr/bin/env python3
"""
Main script to fetch posts with their comments from a Facebook Page and store them in the database.
"""

from fb_api import FacebookAPI
import argparse

def main():
    parser = argparse.ArgumentParser(description='Fetch posts with comments from a Facebook Page')
    parser.add_argument('--posts-limit', type=int, default=50, 
                       help='Maximum number of posts to fetch (default: 50)')
    parser.add_argument('--comments-limit', type=int, default=100,
                       help='Maximum number of comments to fetch per post (default: 100)')
    
    args = parser.parse_args()
    
    # Initialize Facebook API
    fb_api = FacebookAPI()
    
    # Fetch and save posts with comments
    posts_saved, comments_saved = fb_api.fetch_and_save_posts_with_comments(
        posts_limit=args.posts_limit,
        comments_per_post=args.comments_limit
    )
    
    print(f"Process completed. {posts_saved} posts and {comments_saved} comments were saved.")

if __name__ == "__main__":
    main()