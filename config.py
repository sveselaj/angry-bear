# config.py or a similar file
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

PAGE_ACCESS_TOKEN = os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN')
PAGE_ID = os.getenv('FACEBOOK_PAGE_ID')

if not PAGE_ACCESS_TOKEN:
    raise ValueError("No Facebook Page Access Token found in environment variables.")
else:
    print("Facebook Page Access Token loaded successfully.")