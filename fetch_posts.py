#!/usr/bin/env python3
"""
Main script to fetch posts from a Facebook page and store them in the database.
"""

from fb_api import FacebookAPI
import argparse

def main():
    parser = argparse.ArgumentParser(description='Fetch posts from a Facebook Page')
    parser.add_argument('--limit', type=int, default=50, 
                       help='Maximum number of posts to fetch (default: 50)')
    
    args = parser.parse_args()
    
    # Initialize Facebook API
    fb_api = FacebookAPI()
    
    # Fetch and save posts
    saved_count = fb_api.fetch_and_save_posts(limit=args.limit)
    
    print(f"Process completed. {saved_count} new posts were saved.")

if __name__ == "__main__":
    main()