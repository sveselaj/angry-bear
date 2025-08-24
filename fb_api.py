import requests
import json
from datetime import datetime
from typing import List, Dict, Optional
import time
from models import Post, Session
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class FacebookAPI:
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v19.0"
        self.access_token = os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN')
        self.page_id = os.getenv('FACEBOOK_PAGE_ID')
        self.session = Session()
        
    def make_api_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make a request to the Facebook Graph API
        """
        if params is None:
            params = {}
            
        # Add access token to params
        params['access_token'] = self.access_token
        
        try:
            response = requests.get(f"{self.base_url}/{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return None
    
    def fetch_posts(self, limit: int = 100) -> List[Dict]:
        """
        Fetch posts from a Facebook page with pagination handling
        """
        all_posts = []
        endpoint = f"{self.page_id}/posts"
        params = {
            'fields': 'id,message,created_time,updated_time',
            'limit': min(limit, 100)  # Facebook's max limit per request is 100
        }
        
        while endpoint and len(all_posts) < limit:
            response_data = self.make_api_request(endpoint, params)
            
            if not response_data or 'data' not in response_data:
                break
                
            all_posts.extend(response_data['data'])
            
            # Check for next page
            endpoint = response_data.get('paging', {}).get('next', '').replace(self.base_url + '/', '')
            
            # Add a small delay to avoid rate limiting
            time.sleep(1)
        
        return all_posts[:limit]
    
    def parse_post_data(self, post_data: Dict) -> Optional[Dict]:
        """
        Parse raw post data from API into a structured format
        """
        try:
            # Handle cases where message might be missing
            message = post_data.get('message', '')
            if not message:
                return None
                
            # Convert Facebook's ISO format to datetime
            created_time = datetime.strptime(
                post_data['created_time'], 
                '%Y-%m-%dT%H:%M:%S%z'
            )
            
            return {
                'post_id': post_data['id'],
                'message': message,
                'created_time': created_time
            }
        except (KeyError, ValueError) as e:
            print(f"Error parsing post data: {e}")
            return None
    
    def post_exists(self, post_id: str) -> bool:
        """
        Check if a post already exists in the database
        """
        return self.session.query(Post).filter_by(post_id=post_id).count() > 0
    
    def save_post(self, post_data: Dict) -> Optional[Post]:
        """
        Save a post to the database if it doesn't already exist
        """
        if self.post_exists(post_data['post_id']):
            print(f"Post {post_data['post_id']} already exists in database")
            return None
            
        try:
            post = Post(
                page_id=self.page_id,
                post_id=post_data['post_id'],
                message=post_data['message'],
                created_time=post_data['created_time']
            )
            
            self.session.add(post)
            self.session.commit()
            print(f"Saved post: {post_data['post_id']}")
            return post
        except Exception as e:
            self.session.rollback()
            print(f"Error saving post {post_data['post_id']}: {e}")
            return None
    
    def fetch_and_save_posts(self, limit: int = 50):
        """
        Main method to fetch posts from Facebook and save them to the database
        """
        print(f"Fetching up to {limit} posts from page {self.page_id}")
        
        # Fetch posts from API
        raw_posts = self.fetch_posts(limit)
        print(f"Retrieved {len(raw_posts)} posts from API")
        
        # Process and save posts
        saved_count = 0
        for raw_post in raw_posts:
            parsed_post = self.parse_post_data(raw_post)
            if parsed_post:
                saved_post = self.save_post(parsed_post)
                if saved_post:
                    saved_count += 1
        
        print(f"Successfully saved {saved_count} new posts to database")
        return saved_count

# For direct script execution
if __name__ == "__main__":
    fb_api = FacebookAPI()
    fb_api.fetch_and_save_posts(limit=50)