from urllib import request
from flask import Flask, redirect, render_template, url_for
from fb_api import FacebookAPI
from models import Conversation, Message, Post, Session, Comment
from datetime import datetime
import json

app = Flask(__name__)

@app.route('/')
def index():
    """Display all posts in the database"""
    session = Session()
    try:
        # Get all posts, ordered by most recent first
        posts = session.query(Post).order_by(Post.created_time.desc()).all()
        return render_template('index.html', posts=posts)
    except Exception as e:
        return f"Error retrieving posts: {str(e)}"
    finally:
        session.close()

@app.route('/post/<post_id>')
def post_detail(post_id):
    """Display a specific post and its comments"""
    session = Session()
    try:
        post = session.query(Post).filter_by(post_id=post_id).first()
        if not post:
            return f"Post with ID {post_id} not found", 404
        
        # Get comments for this post
        comments = session.query(Comment).filter_by(post_id=post_id).order_by(Comment.created_time).all()
        
        return render_template('post_detail.html', post=post, comments=comments)
    except Exception as e:
        return f"Error retrieving post: {str(e)}"
    finally:
        session.close()

@app.route('/api/posts')
def api_posts():
    """JSON API endpoint for posts"""
    session = Session()
    try:
        posts = session.query(Post).order_by(Post.created_time.desc()).all()
        posts_data = []
        for post in posts:
            posts_data.append({
                'id': post.id,
                'post_id': post.post_id,
                'page_id': post.page_id,
                'message': post.message,
                'created_time': post.created_time.isoformat(),
                'comment_count': len(post.comments)
            })
        return json.dumps(posts_data, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': str(e)}), 500
    finally:
        session.close()

@app.route('/messages')
def messages():
    """Display all conversations"""
    session = Session()
    try:
        conversations = session.query(Conversation).order_by(
            Conversation.updated_time.desc()).all()
        return render_template('messages.html', conversations=conversations)
    except Exception as e:
        return f"Error retrieving conversations: {str(e)}"
    finally:
        session.close()

@app.route('/conversation/<conversation_id>')
def conversation_detail(conversation_id):
    """Display a specific conversation and its messages"""
    session = Session()
    try:
        conversation = session.query(Conversation).filter_by(
            conversation_id=conversation_id).first()
        if not conversation:
            return f"Conversation with ID {conversation_id} not found", 404
        
        messages = session.query(Message).filter_by(
            conversation_id=conversation_id).order_by(Message.created_time).all()
        
        return render_template('conversation_detail.html', 
                             conversation=conversation, 
                             messages=messages)
    except Exception as e:
        return f"Error retrieving conversation: {str(e)}"
    finally:
        session.close()

@app.route('/reply', methods=['POST'])
def reply_to_message():
    """Handle replying to a message"""
    session = Session()
    try:
        recipient_id = request.form.get('recipient_id')
        message_text = request.form.get('message_text')
        
        if not recipient_id or not message_text:
            return "Missing recipient ID or message text", 400
        
        fb_api = FacebookAPI()
        success = fb_api.send_message(recipient_id, message_text)
        
        if success:
            return redirect(request.referrer or url_for('messages'))
        else:
            return "Failed to send message", 500
    except Exception as e:
        return f"Error sending message: {str(e)}", 500
    finally:
        session.close()
        
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)