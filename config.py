# config.py or a similar file
import os
from dotenv import load_dotenv
from flask import Flask

load_dotenv()  # Load environment variables from .env file

PAGE_ACCESS_TOKEN = os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN')
PAGE_ID = os.getenv('FACEBOOK_PAGE_ID')

if not PAGE_ACCESS_TOKEN:
    raise ValueError("No Facebook Page Access Token found in environment variables.")
else:
    print("Facebook Page Access Token loaded successfully.")


SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("No SECRET_KEY found in environment variables.")
else:
    print(f"SECRET_KEY loaded successfully. {SECRET_KEY}")