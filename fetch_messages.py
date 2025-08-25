#!/usr/bin/env python3
"""
Script to fetch and store messages from Facebook Page conversations
"""

from fb_api import FacebookAPI
from models import Conversation, Message, Session
from datetime import datetime
import json

def fetch_and_store_messages():
    fb_api = FacebookAPI()
    session = Session()
    
    print("Fetching conversations...")
    conversations = fb_api.fetch_conversations(limit=50)
    
    for conv_data in conversations:
        # Check if conversation already exists
        existing_conv = session.query(Conversation).filter_by(
            conversation_id=conv_data['id']).first()
        
        if not existing_conv:
            # Create new conversation
            conversation = Conversation(
                conversation_id=conv_data['id'],
                snippet=conv_data.get('snippet', ''),
                updated_time=datetime.strptime(
                    conv_data['updated_time'], '%Y-%m-%dT%H:%M:%S%z'
                ),
                message_count=conv_data.get('message_count', 0),
                participants=json.dumps(conv_data.get('participants', {}).get('data', [])),
                can_reply=conv_data.get('can_reply', False)
            )
            session.add(conversation)
            session.commit()
            print(f"Added new conversation: {conv_data['id']}")
        else:
            conversation = existing_conv
        
        # Fetch messages for this conversation
        print(f"Fetching messages for conversation {conv_data['id']}...")
        messages = fb_api.fetch_messages(conv_data['id'], limit=100)
        
        for msg_data in messages:
            # Check if message already exists
            existing_msg = session.query(Message).filter_by(
                message_id=msg_data['id']).first()
            
            if not existing_msg:
                # Extract sender and recipient info
                from_data = msg_data.get('from', {})
                to_data = msg_data.get('to', {}).get('data', [{}])[0]
                
                message = Message(
                    conversation_id=conv_data['id'],
                    message_id=msg_data['id'],
                    sender_id=from_data.get('id', ''),
                    sender_name=from_data.get('name', ''),
                    recipient_id=to_data.get('id', ''),
                    recipient_name=to_data.get('name', ''),
                    message_text=msg_data.get('message', ''),
                    created_time=datetime.strptime(
                        msg_data['created_time'], '%Y-%m-%dT%H:%M:%S%z'
                    ),
                    has_attachments='attachments' in msg_data
                )
                session.add(message)
                print(f"Added new message: {msg_data['id']}")
        
        session.commit()
    
    session.close()
    print("Message fetching completed!")

if __name__ == "__main__":
    fetch_and_store_messages()