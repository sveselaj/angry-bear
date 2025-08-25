import requests
import json
from datetime import datetime
from typing import List, Dict, Optional
import time
from models import Comment, Post, Session
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
    
    def fetch_conversations(self, limit: int = 50) -> List[Dict]:
        """
        Fetch recent conversations from the Facebook Page
        """
        endpoint = f"{self.page_id}/conversations"
        params = {
            'fields': 'id,link,snippet,updated_time,message_count,participants,can_reply',
            'limit': min(limit, 50),  # Facebook's limit for conversations
            'access_token': self.access_token
        }
        
        try:
            response = requests.get(f"{self.base_url}/{endpoint}", params=params)
            response.raise_for_status()
            return response.json().get('data', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching conversations: {e}")
            return []

    def fetch_messages(self, conversation_id: str, limit: int = 100) -> List[Dict]:
        """
        Fetch messages from a specific conversation
        """
        endpoint = f"{conversation_id}/messages"
        params = {
            'fields': 'id,from,to,message,created_time,sticker,attachments',
            'limit': min(limit, 100),
            'access_token': self.access_token
        }
        
        try:
            response = requests.get(f"{self.base_url}/{endpoint}", params=params)
            response.raise_for_status()
            return response.json().get('data', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching messages: {e}")
            return []

    def send_message(self, recipient_id: str, message: str) -> bool:
        """
        Send a message to a user
        """
        endpoint = f"me/messages"
        params = {
            'recipient': json.dumps({'id': recipient_id}),
            'message': json.dumps({'text': message}),
            'access_token': self.access_token
        }
        
        try:
            response = requests.post(f"{self.base_url}/{endpoint}", params=params)
            response.raise_for_status()
            print(f"Message sent to {recipient_id}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error sending message: {e}")
            return False
        
    def comment_exists(self, comment_id: str) -> bool:
        """
        Check if a comment already exists in the database
        """
        try:
            return self.session.query(Comment).filter_by(comment_id=comment_id).count() > 0
        except Exception as e:
            print(f"Error checking if comment exists: {e}")
            return False
        
    def fetch_and_save_posts_with_comments(self, posts_limit: int = 50, comments_per_post: int = 100):
        """
        Main method to fetch posts with comments and save them to the database
        """
        print("Checking permissions first...")
        self.check_permissions()
        
        print(f"Fetching up to {posts_limit} posts with comments from page {self.page_id}")
        
        # Fetch posts with comments from API
        raw_posts = self.fetch_posts_with_comments(posts_limit, comments_per_post)
        print(f"Retrieved {len(raw_posts)} posts from API")
        
        # Process and save posts with comments
        posts_saved = 0
        total_comments_saved = 0
        
        for i, raw_post in enumerate(raw_posts):
            print(f"Processing post {i+1}/{len(raw_posts)}")
            parsed_post = self.parse_post_with_comments_data(raw_post)
            if parsed_post:
                comments_saved = self.save_post_with_comments(parsed_post)
                if comments_saved >= 0:  # 0 is valid if post already existed
                    posts_saved += 1
                    total_comments_saved += comments_saved
            else:
                print(f"Skipped post {i+1}")
        
        print(f"Successfully processed {posts_saved} posts with {total_comments_saved} comments")
        return posts_saved, total_comments_saved

    def parse_post_with_comments_data(self, post_data: Dict) -> Optional[Dict]:
        """
        Parse raw post data that includes comments
        """
        try:
            # Parse post data
            message = post_data.get('message', '')
            if not message:
                print("No message in post, skipping")
                return None
                
            # Handle both string and datetime objects for post created_time
            if isinstance(post_data['created_time'], str):
                created_time = datetime.strptime(
                    post_data['created_time'], 
                    '%Y-%m-%dT%H:%M:%S%z'
                )
            else:
                created_time = post_data['created_time']
            
            # Parse comments if they exist
            comments = []
            if 'comments' in post_data and 'data' in post_data['comments']:
                for comment_data in post_data['comments']['data']:
                    try:
                        # Handle both string and datetime objects for comment created_time
                        if isinstance(comment_data['created_time'], str):
                            comment_created_time = datetime.strptime(
                                comment_data['created_time'], 
                                '%Y-%m-%dT%H:%M:%S%z'
                            )
                        else:
                            comment_created_time = comment_data['created_time']
                        
                        comment = {
                            'id': comment_data['id'],
                            'message': comment_data.get('message', ''),
                            'created_time': comment_created_time,
                            'from': comment_data.get('from', {}).get('name', 'Unknown')
                        }
                        comments.append(comment)
                    except (KeyError, ValueError) as e:
                        print(f"Error parsing comment data: {e}")
                        continue
            
            return {
                'post_id': post_data['id'],
                'message': message,
                'created_time': created_time,
                'comments': comments
            }
            
        except (KeyError, ValueError) as e:
            print(f"Error parsing post data: {e}")
            import traceback
            traceback.print_exc()
            return None

    def save_post_with_comments(self, post_data: Dict) -> int:
        """
        Save a post and its comments to the database
        """
        if self.post_exists(post_data['post_id']):
            print(f"Post {post_data['post_id']} already exists in database")
            return 0
            
        try:
            # Save the post
            post = Post(
                page_id=self.page_id,
                post_id=post_data['post_id'],
                message=post_data['message'],
                created_time=post_data['created_time']
            )
            
            self.session.add(post)
            self.session.flush()
            
            # Save the comments
            comments_saved = 0
            comments = post_data.get('comments', [])
            
            for comment_data in comments:
                if not self.comment_exists(comment_data['id']):
                    # Handle both string and datetime objects for created_time
                    if isinstance(comment_data['created_time'], str):
                        comment_created_time = datetime.strptime(
                            comment_data['created_time'], 
                            '%Y-%m-%dT%H:%M:%S%z'
                        )
                    else:
                        # It's already a datetime object
                        comment_created_time = comment_data['created_time']
                    
                    comment = Comment(
                        post_id=post_data['post_id'],
                        comment_id=comment_data['id'],
                        message=comment_data.get('message', ''),
                        created_time=comment_created_time,
                        user_name=comment_data.get('from', 'Unknown')
                    )
                    self.session.add(comment)
                    comments_saved += 1
            
            self.session.commit()
            print(f"Saved post {post_data['post_id']} with {comments_saved} comments")
            return comments_saved
            
        except Exception as e:
            self.session.rollback()
            print(f"Error saving post {post_data['post_id']} with comments: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def fetch_and_save_posts_with_comments(self, posts_limit: int = 50, comments_per_post: int = 100):
        """
        Main method to fetch posts with comments and save them to the database
        """
        print(f"Fetching up to {posts_limit} posts with comments from page {self.page_id}")
        
        # Fetch posts with comments from API
        raw_posts = self.fetch_posts_with_comments(posts_limit, comments_per_post)
        print(f"Retrieved {len(raw_posts)} posts with comments from API")
        
        # Process and save posts with comments
        posts_saved = 0
        total_comments_saved = 0
        
        for raw_post in raw_posts:
            parsed_post = self.parse_post_with_comments_data(raw_post)
            if parsed_post:
                comments_saved = self.save_post_with_comments(parsed_post)
                if comments_saved >= 0:  # 0 is valid if post already existed
                    posts_saved += 1
                    total_comments_saved += comments_saved
        
        print(f"Successfully processed {posts_saved} posts with {total_comments_saved} comments")
        return posts_saved, total_comments_saved
        
    def debug_api_response(self, endpoint, params):
        """
        Debug function to see exactly what the API returns
        """
        try:
            print(f"Making request to: {endpoint}")
            print(f"With params: {params}")
            
            response = requests.get(f"{self.base_url}/{endpoint}", params=params)
            print(f"Status code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Error: {response.text}")
                return None
                
            data = response.json()
            print(f"Response keys: {list(data.keys())}")
            
            if 'data' in data:
                print(f"Number of posts returned: {len(data['data'])}")
                if len(data['data']) > 0:
                    first_post = data['data'][0]
                    print(f"First post keys: {list(first_post.keys())}")
                    if 'comments' in first_post:
                        print(f"Comments in first post: {first_post['comments']}")
                    else:
                        print("No 'comments' key in first post")
            
            return data
        except Exception as e:
            print(f"Debug request failed: {e}")
            return None
        
    def fetch_posts_with_comments(self, limit: int = 50, comments_per_post: int = 100) -> List[Dict]:
        """
        Fetch posts and their comments with a fallback approach
        """
        print("Using fallback approach: fetching posts first, then comments separately")
        return self.fetch_posts_separate_from_comments(limit, comments_per_post)

    def fetch_posts_separate_from_comments(self, limit: int = 50, comments_per_post: int = 100) -> List[Dict]:
        """
        Fetch posts first, then fetch comments for each post separately
        """
        # First, fetch just the posts
        posts_endpoint = f"{self.page_id}/posts"
        posts_params = {
            'fields': 'id,message,created_time',
            'limit': limit,
            'access_token': self.access_token
        }
        
        posts_response = self.make_api_request(posts_endpoint, posts_params)
        if not posts_response or 'data' not in posts_response:
            print("Failed to fetch posts")
            return []
        
        posts_data = posts_response['data']
        print(f"Fetched {len(posts_data)} posts")
        
        # Now fetch comments for each post
        for i, post in enumerate(posts_data):
            print(f"Fetching comments for post {i+1}/{len(posts_data)}: {post['id']}")
            comments_endpoint = f"{post['id']}/comments"
            comments_params = {
                'fields': 'id,message,created_time,from{name}',
                'limit': comments_per_post,
                'access_token': self.access_token
            }
            
            comments_response = self.make_api_request(comments_endpoint, comments_params)
            if comments_response and 'data' in comments_response:
                post['comments'] = {'data': comments_response['data']}
                print(f"Found {len(comments_response['data'])} comments")
            else:
                post['comments'] = {'data': []}
                print("No comments found")
            
            # Add a small delay to avoid rate limiting
            time.sleep(1)
        
        return posts_data
    
    def check_permissions(self):
        """
        Check what permissions your app has been granted
        """
        debug_token_endpoint = "debug_token"
        params = {
            'input_token': self.access_token,
            'access_token': self.access_token
        }
        
        response_data = self.debug_api_response(debug_token_endpoint, params)
        print("response_data:")
        print(response_data)
        if response_data and 'data' in response_data:
            print("Token permissions:")
            print(json.dumps(response_data['data'], indent=2))
            
            # Check if we have pages_read_engagement permission
            if 'scopes' in response_data['data']:
                scopes = response_data['data']['scopes']
                print(f"Available scopes: {scopes}")
                if 'pages_read_engagement' not in scopes:
                    print("WARNING: Missing pages_read_engagement permission!")
                if 'pages_show_list' not in scopes:
                    print("WARNING: Missing pages_show_list permission!")
                    
        return response_data

    def test_simple_api_call(self):
        """
        Make a simple API call to verify basic functionality
        """
        print("Testing simple API call...")
        
        # Try to get basic page info
        endpoint = f"{self.page_id}"
        params = {
            'fields': 'id,name,fan_count',
            'access_token': self.access_token
        }
        
        response_data = self.make_api_request(endpoint, params)
        
        if response_data:
            print("Simple API call successful!")
            print(f"Page: {response_data.get('name')} (ID: {response_data.get('id')})")
            print(f"Likes: {response_data.get('fan_count', 'Unknown')}")
            return True
        else:
            print("Simple API call failed")
            return False

    def make_api_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make a request to the Facebook Graph API with enhanced error handling
        """
        if params is None:
            params = {}
        
        # Add access token to params
        params['access_token'] = self.access_token
        
        try:
            print(f"Making request to: {endpoint}")
            print(f"Params: { {k: v for k, v in params.items() if k != 'access_token'} }")  # Don't print token
            
            response = requests.get(f"{self.base_url}/{endpoint}", params=params, timeout=30)
            print(f"Response status: {response.status_code}")
            
            # Check for specific error status codes
            if response.status_code == 400:
                print("Bad Request - check your parameters")
                print(f"Response: {response.text}")
                return None
            elif response.status_code == 401:
                print("Unauthorized - check your access token")
                print(f"Response: {response.text}")
                return None
            elif response.status_code == 403:
                print("Forbidden - check your permissions")
                print(f"Response: {response.text}")
                return None
            elif response.status_code == 404:
                print("Not Found - check your endpoint URL")
                print(f"Response: {response.text}")
                return None
            
            response.raise_for_status()
            
            # Try to parse JSON
            try:
                data = response.json()
                print("API request successful")
                return data
            except json.JSONDecodeError:
                print(f"Failed to parse JSON response: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print("Request timed out after 30 seconds")
            return None
        except requests.exceptions.ConnectionError:
            print("Connection error - check your internet connection")
            return None
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return None

    def verify_credentials(self):
        """
        Verify that the access token and page ID are valid
        """
        print("Verifying credentials...")
        
        # First, verify the access token
        debug_url = f"https://graph.facebook.com/debug_token"
        debug_params = {
            'input_token': self.access_token,
            'access_token': self.access_token
        }
        
        try:
            response = requests.get(debug_url, params=debug_params)
            debug_data = response.json()
            
            if 'data' in debug_data and debug_data['data']['is_valid']:
                print("Access token is valid")
                print(f"App ID: {debug_data['data']['app_id']}")
                print(f"User ID: {debug_data['data']['user_id']}")
                print(f"Scopes: {debug_data['data']['scopes']}")
            else:
                print("Access token is invalid")
                return False
        except Exception as e:
            print(f"Error verifying token: {e}")
            return False
        
        # Next, verify the page ID
        try:
            page_url = f"https://graph.facebook.com/{self.page_id}"
            page_params = {
                'fields': 'id,name',
                'access_token': self.access_token
            }
            
            response = requests.get(page_url, params=page_params)
            page_data = response.json()
            
            if 'id' in page_data:
                print(f"Page ID is valid: {page_data['id']}")
                print(f"Page name: {page_data.get('name', 'Unknown')}")
                return True
            elif 'error' in page_data:
                print(f"Page ID error: {page_data['error']['message']}")
                return False
        except Exception as e:
            print(f"Error verifying page: {e}")
            return False
        
        return True

# For direct script execution
if __name__ == "__main__":
    fb_api = FacebookAPI()
    fb_api.fetch_and_save_posts(limit=50)