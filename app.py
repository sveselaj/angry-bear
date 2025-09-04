from urllib import request
from flask import Flask, jsonify, redirect, render_template, url_for, request, flash

from fb_api import FacebookAPI
from models import Conversation, Message, MessageResponse, OpenAILog, Post, Session, Comment, CommentReply, ResponseDraft
from datetime import datetime
import json
from text_analysis import extract_trending_topics
from sqlalchemy.orm import joinedload

from math import ceil
from sqlalchemy import func, select
from sqlalchemy.orm import Session as SASession  # optional alias

from flask_wtf.csrf import CSRFProtect, generate_csrf

import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Flask app
app = Flask(__name__)
# Configure secret key for CSRF protection
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
# Initialize CSRF protection
csrf = CSRFProtect(app)

# Make CSRF token available in all templates
@app.context_processor
def inject_csrf_token():
    from flask_wtf.csrf import generate_csrf
    return dict(csrf_token=generate_csrf)


@app.context_processor
def inject_global_vars():
    return {
        'FACEBOOK_PAGE_NAME': os.getenv('FACEBOOK_PAGE_NAME', 'N/A')
    }

# Your routes here...

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

@app.route('/analytics')
def analytics():
    """Display analytics dashboard"""
    session = Session()
    try:
        print("Starting analytics processing...")
        
        # Get all posts with their comments
        from sqlalchemy.orm import joinedload
        posts = session.query(Post).options(joinedload(Post.comments)).order_by(Post.created_time.desc()).all()
        print(f"Found {len(posts)} posts")
        
        # Calculate overall statistics
        total_posts = len(posts)
        total_comments = sum(len(post.comments) for post in posts)
        print(f"Total posts: {total_posts}, Total comments: {total_comments}")
        
        # Calculate sentiment distribution
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        for post in posts:
            for comment in post.comments:
                try:
                    # Handle cases where sentiment_category might be None
                    category = getattr(comment, 'sentiment_category', 'neutral') or 'neutral'
                    sentiment_counts[category] += 1
                except Exception as e:
                    print(f"Error processing comment {getattr(comment, 'id', 'unknown')}: {e}")
                    sentiment_counts['neutral'] += 1
        
        print(f"Sentiment counts: {sentiment_counts}")
        
        # Extract trending topics across all posts
        all_post_messages = []
        for post in posts:
            try:
                # Check if post.message exists and is a string
                if hasattr(post, 'message') and post.message and isinstance(post.message, str):
                    all_post_messages.append(post.message)
                else:
                    print(f"Post {getattr(post, 'id', 'unknown')} has no message or message is not a string")
            except Exception as e:
                print(f"Error extracting message from post {getattr(post, 'id', 'unknown')}: {e}")
        
        print(f"Extracted {len(all_post_messages)} post messages for topic analysis")
        
        # Check if we have messages to analyze
        if all_post_messages:
            trending_topics = extract_trending_topics(all_post_messages, num_topics=10)
            print(f"Found trending topics: {trending_topics}")
        else:
            trending_topics = []
            print("No post messages available for topic analysis")
        
        return render_template('analytics.html', 
                             posts=posts,
                             total_posts=total_posts,
                             total_comments=total_comments,
                             sentiment_counts=sentiment_counts,
                             trending_topics=trending_topics)
    except Exception as e:
        print(f"Error in analytics: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error retrieving analytics: {str(e)}"
    finally:
        session.close()

@app.route('/post/<post_id>/analysis')
def post_analysis(post_id):
    """Detailed analysis for a specific post"""
    session = Session()
    try:
        post = session.query(Post).filter_by(post_id=post_id).first()
        if not post:
            return f"Post with ID {post_id} not found", 404
        
        # Get comments with sentiment analysis
        comments = session.query(Comment).filter_by(post_id=post_id).order_by(Comment.created_time).all()
        
        # Calculate sentiment distribution for this post
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        for comment in comments:
            sentiment_counts[comment.sentiment_category] += 1
        
        # Extract keywords from this post
        post_keywords = json.loads(post.trending_topics) if post.trending_topics else []
        
        return render_template('post_analysis.html', 
                             post=post,
                             comments=comments,
                             sentiment_counts=sentiment_counts,
                             post_keywords=post_keywords)
    except Exception as e:
        return f"Error retrieving post analysis: {str(e)}"
    finally:
        session.close()


@app.route('/comments')
def comments():
    """Display all comments with filtering options and pagination"""
    session = Session()
    try:
        # Get filter parameters from request
        page = request.args.get('page', 1, type=int)
        sentiment_filter = request.args.get('sentiment', 'all')
        search_query = request.args.get('search', '')
        posts_filter = request.args.get('post', 'all')
        
        # Base query
        query = session.query(Comment).join(Post)
        
        # Apply sentiment filter
        if sentiment_filter != 'all':
            query = query.filter(Comment.sentiment_category == sentiment_filter)
        
        # Apply search filter
        if search_query:
            query = query.filter(Comment.message.ilike(f'%{search_query}%'))
        
        # Apply post filter
        if posts_filter != 'all':
            query = query.filter(Comment.post_id == posts_filter)
        
        # Get all posts for the filter dropdown
        all_posts = session.query(Post).order_by(Post.created_time.desc()).all()
        
        # Pagination settings
        per_page = 50
        total_count = query.count()
        total_pages = ceil(total_count / per_page) if total_count > 0 else 1
        
        # Ensure page is within valid range
        page = max(1, min(page, total_pages))
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Get paginated comments
        comments = query.order_by(Comment.created_time.desc()).offset(offset).limit(per_page).all()
        
        # Create pagination object
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total_count,
            'pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_num': page - 1,
            'next_num': page + 1
        }
        
        # Generate page range for pagination links
        def iter_pages(left_edge=2, left_current=2, right_current=5, right_edge=2):
            last = 0
            for num in range(1, total_pages + 1):
                if (num <= left_edge or 
                    (num > page - left_current - 1 and num < page + right_current) or 
                    num > total_pages - right_edge):
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num
        
        pagination['iter_pages'] = iter_pages
        
        return render_template('comments.html', 
                             comments=comments,
                             pagination=pagination,
                             sentiment_filter=sentiment_filter,
                             search_query=search_query,
                             posts_filter=posts_filter,
                             all_posts=all_posts)
    except Exception as e:
        return f"Error retrieving comments: {str(e)}"
    finally:
        session.close()

@app.route('/post/<post_id>/edit', methods=['GET', 'POST'])
def edit_post(post_id):
    """Edit a Facebook post"""
    session = Session()
    try:
        post = session.query(Post).filter_by(post_id=post_id).first()
        if not post:
            return f"Post with ID {post_id} not found", 404
        
        if request.method == 'POST':
            new_message = request.form.get('message')
            if not new_message:
                return "Message cannot be empty", 400
            
            # Update on Facebook
            fb_api = FacebookAPI()
            success = fb_api.edit_post(post_id, new_message)
            
            if success:
                # Update local database
                fb_api.update_local_post(post_id, new_message)
                return redirect(url_for('post_analysis', post_id=post_id))
            else:
                return "Failed to update post on Facebook", 500
        
        # For GET request, show the edit form
        return render_template('edit_post.html', post=post)
        
    except Exception as e:
        return f"Error editing post: {str(e)}", 500
    finally:
        session.close()

@csrf.exempt
@app.route('/post/<post_id>/delete', methods=['POST'])
def delete_post(post_id):
    """Delete a Facebook post with CSRF protection"""
    session = Session()
    try:
        # Verify CSRF token
        # This is automatically handled by Flask-WTF if you have the CSRF token in your form
        
        post = session.query(Post).filter_by(post_id=post_id).first()
        if not post:
            return f"Post with ID {post_id} not found", 404
        
        # Delete from Facebook
        fb_api = FacebookAPI()
        success = fb_api.delete_post(post_id)
        
        if success:
            # Delete from local database
            fb_api.delete_local_post(post_id)
            return redirect(url_for('analytics'))
        else:
            return "Failed to delete post from Facebook", 500
            
    except Exception as e:
        return f"Error deleting post: {str(e)}", 500
    finally:
        session.close()

@app.route('/post/<post_id>/facebook')
def get_post_facebook_url(post_id):
    """Redirect to the Facebook post"""
    session = Session()
    try:
        post = session.query(Post).filter_by(post_id=post_id).first()
        if post:
            # Use the property we added to the Post model
            return redirect(post.facebook_url)
        else:
            # Fallback URL if post not found in database
            return redirect(f"https://www.facebook.com/{post_id}")
    except Exception as e:
        # Fallback URL on error
        return redirect(f"https://www.facebook.com/{post_id}")
    finally:
        session.close()

@app.route('/fetch-posts')
def fetch_posts():
    """Manually trigger post fetching with progress updates"""
    try:
        # Create a simple progress tracking mechanism
        # In a real application, you might want to use a more sophisticated
        # solution like Celery with WebSockets for real-time progress updates
        
        # For now, we'll simulate progress with a simple approach
        fb_api = FacebookAPI()
        
        # Show loading immediately
        # The JavaScript will handle showing the indicator on click
        # We'll rely on the page reload to hide it
        
        # Fetch posts
        posts_saved, comments_saved = fb_api.fetch_and_save_posts_with_comments(
            posts_limit=100)
        
        flash(f"Successfully fetched {posts_saved} posts with {comments_saved} comments", "success")
    except Exception as e:
        flash(f"Error fetching posts: {str(e)}", "danger")
    
    return redirect(url_for('index'))

@app.route('/comment/<comment_id>/delete', methods=['POST'])
def delete_comment(comment_id):
    """Delete a comment from Facebook and local database"""
    session = Session()
    try:
        # Get the comment to find its post_id for redirection
        comment = session.query(Comment).filter_by(comment_id=comment_id).first()
        if not comment:
            flash("Comment not found", "danger")
            return redirect(url_for('comments'))
        
        post_id = comment.post_id
        
        # Delete from Facebook
        fb_api = FacebookAPI()
        fb_success = fb_api.delete_comment(comment_id)
        
        # Delete from local database regardless of Facebook success
        local_success = fb_api.delete_local_comment(comment_id)
        
        if fb_success and local_success:
            flash("Comment deleted successfully from Facebook and local database", "success")
        elif local_success:
            flash("Comment deleted from local database (Facebook deletion may have failed)", "warning")
        else:
            flash("Failed to delete comment", "danger")
            
        # Redirect back to the appropriate page
        if request.referrer and 'post_analysis' in request.referrer:
            return redirect(url_for('post_analysis', post_id=post_id))
        else:
            return redirect(url_for('comments'))
            
    except Exception as e:
        flash(f"Error deleting comment: {str(e)}", "danger")
        return redirect(url_for('comments'))
    finally:
        session.close()

import time
import json
from flask import Response

@app.route('/fetch-posts-with-progress')
def fetch_posts_with_progress():
    """Fetch posts with real-time progress updates"""
    def generate():
        # Create a new FacebookAPI instance with progress callback
        fb_api = FacebookAPI()
        
        # Set up progress callback
        def progress_callback(progress, message):
            data = json.dumps({'progress': progress, 'message': message})
            yield f"data: {data}\n\n"
        
        # Set the callback
        fb_api.set_progress_callback(progress_callback)
        
        try:
            # Start the process
            yield from progress_callback(0, "Starting post fetch...")
            
            # Fetch posts
            posts_saved, comments_saved = fb_api.fetch_and_save_posts_with_comments(
                posts_limit=10, 
                comments_per_post=20
            )
            
            # Final update
            yield from progress_callback(100, f"Successfully fetched {posts_saved} posts with {comments_saved} comments")
            
            # Add a small delay before closing the connection
            time.sleep(1)
            yield "event: close\ndata: {}\n\n"
            
        except Exception as e:
            yield from progress_callback(0, f"Error: {str(e)}")
            time.sleep(1)
            yield "event: close\ndata: {}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

# Add a new template for the progress page
@app.route('/fetch-posts-progress')
def fetch_posts_progress():
    """Page that shows progress of post fetching"""
    return render_template('fetch_progress.html')


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors by hiding the loading indicator"""
    return render_template('error.html', error=error), 500

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('error.html', error=error), 404

from flask import render_template
import traceback

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template(
        'error.html',
        error_code=404,
        error=str(error) if error else "Not Found",
        error_description="The requested resource could not be found."
    ), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    # Get the traceback for debugging
    tb = traceback.format_exc()
    
    return render_template(
        'error.html',
        error_code=500,
        error=str(error) if error else "Internal Server Error",
        error_description="An unexpected error occurred on the server.",
        error_traceback=tb if app.debug else None
    ), 500

@app.errorhandler(403)
def forbidden_error(error):
    """Handle 403 errors"""
    return render_template(
        'error.html',
        error_code=403,
        error=str(error) if error else "Forbidden",
        error_description="You don't have permission to access this resource."
    ), 403

@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """Handle any other unexpected errors"""
    # Get the traceback for debugging
    tb = traceback.format_exc()
    
    return render_template(
        'error.html',
        error_code=500,
        error=str(error) if error else "Unexpected Error",
        error_description="An unexpected error occurred.",
        error_traceback=tb if app.debug else None
    ), 500

@app.route('/error')
def show_error():
    """Route to display custom error messages"""
    error_code = request.args.get('code', 500, type=int)
    error_message = request.args.get('message', 'An error occurred')
    error_description = request.args.get('description', '')
    
    return render_template(
        'error.html',
        error_code=error_code,
        error=error_message,
        error_description=error_description
    ), error_code


# Add to your app.py
import logging
from logging.handlers import RotatingFileHandler
import os

# Set up logging
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/facebook_analytics.log', 
                                       maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Facebook Analytics startup')

# Update error handlers to log errors
@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors and log them"""
    app.logger.error('Server Error: %s', error)
    app.logger.error('Traceback: %s', traceback.format_exc())
    
    # Get the traceback for debugging
    tb = traceback.format_exc()
    
    return render_template(
        'error.html',
        error_code=500,
        error=str(error) if error else "Internal Server Error",
        error_description="An unexpected error occurred on the server.",
        error_traceback=tb if app.debug else None
    ), 500

""" 
@app.route('/comment/<comment_id>/reply', methods=['POST'])
def reply_to_comment(comment_id):
    session = Session()
     # Post reply to Facebook
    fb_api = FacebookAPI()
    if not fb_api.check_reply_permissions():
        flash('Your app does not have permission to reply to comments. Please check your Facebook app permissions.', 'danger')
        return redirect(request.referrer or url_for('comments'))

    try:
        message = request.form.get('message')
        if not message or not message.strip():
            flash('Reply message cannot be empty', 'danger')
            return redirect(request.referrer or url_for('comments'))
        
        # Get the comment to verify it exists
        comment = session.query(Comment).filter_by(comment_id=comment_id).first()
        if not comment:
            flash('Comment not found', 'danger')
            return redirect(request.referrer or url_for('comments'))
       
        reply_data = fb_api.reply_to_comment(comment_id, message.strip())
        
        if reply_data and 'id' in reply_data:
            # Save the reply to our database
            reply = CommentReply(
                comment_id=comment_id,
                reply_id=reply_data['id'],
                message=message.strip(),
                created_time=datetime.now(),
                user_name=os.getenv('FACEBOOK_PAGE_NAME', 'Admin')
            )
            
            session.add(reply)
            session.commit()
            
            flash('Reply posted successfully', 'success')
        else:
            flash('Failed to post reply to Facebook', 'danger')
        
        return redirect(request.referrer or url_for('comments'))
        
    except Exception as e:
        session.rollback()
        flash(f'Error posting reply: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('comments'))
    finally:
        session.close() """

@app.route('/comment/<comment_id>/replies')
def get_comment_replies(comment_id):
    """Get replies for a comment"""
    session = Session()
    try:
        # Get replies from our database
        replies = session.query(CommentReply).filter_by(comment_id=comment_id)\
                     .order_by(CommentReply.created_time.desc()).all()
        
        # If no replies in DB, try to fetch from Facebook
        if not replies:
            fb_api = FacebookAPI()
            fb_replies = fb_api.get_comment_replies(comment_id)
            
            # Save fetched replies to database
            for fb_reply in fb_replies:
                reply = CommentReply(
                    comment_id=comment_id,
                    reply_id=fb_reply['id'],
                    message=fb_reply.get('message', ''),
                    created_time=datetime.strptime(
                        fb_reply['created_time'], 
                        '%Y-%m-%dT%H:%M:%S%z'
                    ),
                    user_name=fb_reply.get('from', {}).get('name', 'Unknown')
                )
                session.add(reply)
            
            session.commit()
            replies = session.query(CommentReply).filter_by(comment_id=comment_id)\
                         .order_by(CommentReply.created_time.desc()).all()
        
        return jsonify({
            'success': True,
            'replies': [{
                'id': reply.id,
                'message': reply.message,
                'created_time': reply.created_time.strftime('%Y-%m-%d %H:%M'),
                'user_name': reply.user_name
            } for reply in replies]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@app.route('/reply/<reply_id>/delete', methods=['POST'])
def delete_reply(reply_id):
    """Delete a reply"""
    session = Session()
    try:
        reply = session.query(CommentReply).filter_by(reply_id=reply_id).first()
        if not reply:
            flash('Reply not found', 'danger')
            return redirect(request.referrer or url_for('replies'))
        
        # Delete from Facebook
        fb_api = FacebookAPI()
        success = fb_api.delete_comment(reply_id)  # Reuse the delete_comment method
        
        # Delete from local database
        session.delete(reply)
        session.commit()
        
        if success:
            flash('Reply deleted successfully', 'success')
        else:
            flash('Reply deleted from local database but may not have been deleted from Facebook', 'warning')
        
        return redirect(request.referrer or url_for('replies'))
        
    except Exception as e:
        session.rollback()
        flash(f'Error deleting reply: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('replies'))
    finally:
        session.close()



# Add these imports to your app.py
from comment_evaluator import CommentEvaluator
from models import AutoReplySettings, Comment, CommentReply, Post, Session
from sqlalchemy import desc

@app.route('/auto_reply_settings', methods=['GET', 'POST'])
def auto_reply_settings():
    """Manage auto-reply settings"""
    session = Session()
    try:
        # Get current settings or create default ones
        settings = session.query(AutoReplySettings).first()
        if not settings:
            settings = AutoReplySettings()
            session.add(settings)
            session.commit()
        
        # Calculate statistics for the template
        total_ai_replies = session.query(CommentReply).filter_by(ai_generated=True).count()
        
        # Get today's date at midnight for comparison
        from datetime import datetime, time
        today_start = datetime.combine(datetime.now().date(), time.min)
        
        todays_ai_replies = session.query(CommentReply).filter(
            CommentReply.ai_generated == True,
            CommentReply.created_time >= today_start
        ).count()
        
        pending_comments = session.query(Comment).filter_by(ai_responded=False).count()
        
        if request.method == 'POST':
            # Update settings from form data
            settings.enabled = 'enabled' in request.form
            settings.response_template = request.form.get('response_template', '')
            
            try:
                settings.min_confidence = float(request.form.get('min_confidence', 0.7))
            except ValueError:
                settings.min_confidence = 0.7
                
            try:
                settings.max_daily_replies = int(request.form.get('max_daily_replies', 50))
            except ValueError:
                settings.max_daily_replies = 50
                
            settings.reply_to_negative = 'reply_to_negative' in request.form
            settings.reply_to_questions = 'reply_to_questions' in request.form
            settings.reply_to_compliments = 'reply_to_compliments' in request.form
            
            # Handle excluded keywords
            excluded_keywords = request.form.get('excluded_keywords', '')
            settings.excluded_keywords = json.dumps([k.strip() for k in excluded_keywords.split(',') if k.strip()])
            
            session.commit()
            flash('Auto-reply settings updated successfully!', 'success')
            return redirect(url_for('auto_reply_settings'))
        
        # For GET requests, prepare the template data
        excluded_keywords = []
        if settings.excluded_keywords:
            try:
                excluded_keywords = json.loads(settings.excluded_keywords)
            except:
                excluded_keywords = []
        
        return render_template('auto_reply_settings.html', 
                             settings=settings,
                             excluded_keywords=", ".join(excluded_keywords),
                             total_ai_replies=total_ai_replies,
                             todays_ai_replies=todays_ai_replies,
                             pending_comments=pending_comments)
        
    except Exception as e:
        flash(f'Error managing auto-reply settings: {str(e)}', 'danger')
        import traceback
        traceback.print_exc()
        return redirect(url_for('index'))
    finally:
        session.close()

""" # Add these routes to your app.py
@app.route('/auto_reply_settings', methods=['GET', 'POST'])
def auto_reply_settings():
    session = Session()
    try:
        # Get current settings or create default ones
        settings = session.query(AutoReplySettings).first()
        if not settings:
            settings = AutoReplySettings()
            session.add(settings)
            session.commit()
        
        # Calculate statistics
        from datetime import datetime, date
        
        total_ai_replies = session.query(CommentReply).filter_by(ai_generated=True).count()
        
        todays_ai_replies = session.query(CommentReply).filter(
            CommentReply.ai_generated == True,
            CommentReply.created_time >= date.today()
        ).count()
        
        pending_comments = session.query(Comment).filter_by(ai_responded=False).count()
        
        if request.method == 'POST':
            # ... your existing POST handling code ...
            print("DEBUG: Processing POST request")
            print(f"DEBUG: Form data: {dict(request.form)}")
            
            # Update settings from form data with detailed debugging
            settings.enabled = 'enabled' in request.form
            print(f"DEBUG: enabled set to: {settings.enabled}")
            
            settings.response_template = request.form.get('response_template', '')
            print(f"DEBUG: response_template set to: {settings.response_template}")
            
            try:
                settings.min_confidence = float(request.form.get('min_confidence', 0.7))
                print(f"DEBUG: min_confidence set to: {settings.min_confidence}")
            except ValueError as e:
                print(f"DEBUG: Error parsing min_confidence: {e}")
                settings.min_confidence = 0.7
            
            try:
                settings.max_daily_replies = int(request.form.get('max_daily_replies', 50))
                print(f"DEBUG: max_daily_replies set to: {settings.max_daily_replies}")
            except ValueError as e:
                print(f"DEBUG: Error parsing max_daily_replies: {e}")
                settings.max_daily_replies = 50
            
            settings.reply_to_negative = 'reply_to_negative' in request.form
            print(f"DEBUG: reply_to_negative set to: {settings.reply_to_negative}")
            
            settings.reply_to_questions = 'reply_to_questions' in request.form
            print(f"DEBUG: reply_to_questions set to: {settings.reply_to_questions}")
            
            settings.reply_to_compliments = 'reply_to_compliments' in request.form
            print(f"DEBUG: reply_to_compliments set to: {settings.reply_to_compliments}")
            
            # Handle excluded keywords
            excluded_keywords = request.form.get('excluded_keywords', '')
            print(f"DEBUG: Raw excluded_keywords: {excluded_keywords}")
            
            try:
                keyword_list = [k.strip() for k in excluded_keywords.split(',') if k.strip()]
                settings.excluded_keywords = json.dumps(keyword_list)
                print(f"DEBUG: excluded_keywords set to: {settings.excluded_keywords}")
            except Exception as e:
                print(f"DEBUG: Error processing excluded_keywords: {e}")
                settings.excluded_keywords = json.dumps([])
            
            print("DEBUG: About to commit settings to database")
            session.commit()
            print("DEBUG: Settings committed successfully")
            
            flash('Auto-reply settings updated successfully!', 'success')
            return redirect(url_for('auto_reply_settings'))
        
        # For GET requests, render the settings page
        excluded_keywords = []
        if settings.excluded_keywords:
            try:
                excluded_keywords = json.loads(settings.excluded_keywords)
            except:
                excluded_keywords = []
        
        return render_template('auto_reply_settings.html', 
                             settings=settings,
                             excluded_keywords=", ".join(excluded_keywords),
                             total_ai_replies=total_ai_replies,
                             todays_ai_replies=todays_ai_replies,
                             pending_comments=pending_comments)
        
    except Exception as e:
        flash(f'Error managing auto-reply settings: {str(e)}', 'danger')
        import traceback
        traceback.print_exc()
        return redirect(url_for('index'))
    finally:
        session.close()
 """        
@app.route('/auto_reply_process', methods=['POST'])
def auto_reply_process():
    """Process comments for auto-reply"""
    session = Session()
    try:
        # Get settings
        settings = session.query(AutoReplySettings).first()
        if not settings:
            settings = AutoReplySettings()
        
        # Get limit from form
        limit = int(request.form.get('limit', 10))
        
        # Get comments that haven't been responded to yet
        comments = session.query(Comment).filter(
            Comment.ai_responded == False
        ).order_by(desc(Comment.created_time)).limit(limit).all()
        
        # Initialize evaluator and Facebook API
        evaluator = CommentEvaluator()
        fb_api = FacebookAPI()
        
        results = {
            'processed': len(comments),
            'replied': 0,
            'errors': 0,
            'details': []
        }
        
        # Process each comment
        for comment in comments:
            detail = {
                'comment_id': comment.comment_id,
                'success': False,
                'reply': None,
                'error': None
            }
            
            try:
                # Get post context if available
                post_context = None
                if comment.post_rel:
                    post_context = comment.post_rel.message
                
                # Evaluate the comment
                evaluation = evaluator.evaluate_comment(comment.message, post_context)
                
                if not evaluation['success']:
                    detail['error'] = evaluation.get('error', 'Evaluation failed')
                    results['errors'] += 1
                    results['details'].append(detail)
                    continue
                
                # Generate response
                response_text = evaluation['response']
                #response_text = evaluator._extract_response_text(response_text)
                detail['reply'] = response_text
                
                # Post reply to Facebook
                reply_data = fb_api.reply_to_comment(comment.comment_id, response_text)
                
                if reply_data and 'id' in reply_data:
                    # Save the reply to database
                    reply = CommentReply(
                        comment_id=comment.comment_id,
                        reply_id=reply_data['id'],
                        message=response_text,
                        created_time=datetime.now(),
                        user_name=os.getenv('FACEBOOK_PAGE_NAME', 'Admin'),
                        ai_generated=True,
                        posted_to_facebook=True
                    )
                    
                    # Update comment to mark as responded
                    comment.ai_responded = True
                    comment.ai_response = response_text
                    comment.ai_evaluation = json.dumps(evaluation)
                    
                    session.add(reply)
                    session.commit()
                    
                    detail['success'] = True
                    results['replied'] += 1
                else:
                    detail['error'] = 'Failed to post reply to Facebook'
                    results['errors'] += 1
                    
            except Exception as e:
                detail['error'] = str(e)
                results['errors'] += 1
                session.rollback()
            
            results['details'].append(detail)
        
        # Render results page
        return render_template('auto_reply_results.html', results=results)
        
    except Exception as e:
        flash(f'Error processing auto-replies: {str(e)}', 'danger')
        return redirect(url_for('auto_reply_settings'))
    finally:
        session.close()

@app.route('/api/auto_reply_generate', methods=['POST'])
def api_auto_reply_generate():
    """API endpoint to generate a response for a test comment"""
    try:
        data = request.get_json()
        comment_text = data.get('comment', '')
        
        if not comment_text:
            return jsonify({'error': 'No comment provided'}), 400
        
        # Generate response
        evaluator = CommentEvaluator()
        evaluation = evaluator.evaluate_comment(comment_text)
        
        if evaluation['success']:
            return jsonify({'response': evaluation['response']})
        else:
            return jsonify({'error': evaluation.get('error', 'Failed to generate response')}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add these imports at the top of your app.py
from sqlalchemy import or_

# Add these routes to your app.py

@app.route('/replies')
def replies():
    """Display all replies with filtering options"""
    session = Session()
    try:
        # Get filter parameter
        filter_type = request.args.get('filter', 'all')
        
        # Base query
        query = session.query(CommentReply)
        
        # Apply filters
        if filter_type == 'ai':
            query = query.filter_by(ai_generated=True)
        elif filter_type == 'facebook':
            query = query.filter_by(posted_to_facebook=True)
        elif filter_type == 'error':
            query = query.filter(CommentReply.post_error.isnot(None))
        
        # Get replies
        replies = query.order_by(CommentReply.created_time.desc()).all()
        
        return render_template('replies.html', replies=replies, filter_type=filter_type)
        
    except Exception as e:
        flash(f'Error loading replies: {str(e)}', 'danger')
        return redirect(url_for('index'))
    finally:
        session.close()

@app.context_processor
def inject_pending_comments_count():
    """Inject the count of pending comments into all templates"""
    try:
        session = Session()
        pending_count = session.query(Comment).filter_by(ai_responded=False).count()
        session.close()
        return {'pending_comments_count': pending_count}
    except:
        return {'pending_comments_count': 0}

# Add a route to handle the process form without requiring POST data
@app.route('/auto_reply_process')
def auto_reply_process_page():
    """Display the auto-reply process page"""
    return redirect(url_for('auto_reply_settings'))




@app.route('/comment/<comment_id>')
def comment_detail(comment_id):
    """View details of a specific comment"""
    session = Session()
    try:
        comment = session.query(Comment).filter_by(comment_id=comment_id).first()
        if not comment:
            flash('Comment not found', 'danger')
            return redirect(url_for('comments'))
            
        replies = session.query(CommentReply).filter_by(comment_id=comment_id).order_by(CommentReply.created_time.desc()).all()
        
        return render_template('comment_detail.html', comment=comment, replies=replies)
        
    except Exception as e:
        flash(f'Error loading comment: {str(e)}', 'danger')
        return redirect(url_for('comments'))
    finally:
        session.close()

@app.route('/comment/<comment_id>/reply', methods=['POST'])
def reply_to_comment(comment_id):
    """Handle replying to a comment"""
    session = Session()
    try:
        message = request.form.get('message')
        if not message or not message.strip():
            flash('Reply message cannot be empty', 'danger')
            return redirect(url_for('comment_detail', comment_id=comment_id))
        
        # Get the comment to verify it exists
        comment = session.query(Comment).filter_by(comment_id=comment_id).first()
        if not comment:
            flash('Comment not found', 'danger')
            return redirect(url_for('comments'))
       
        # Post reply to Facebook
        fb_api = FacebookAPI()
        reply_data = fb_api.reply_to_comment(comment_id, message.strip())
        
        if reply_data and 'id' in reply_data:
            # Save the reply to our database
            reply = CommentReply(
                comment_id=comment_id,
                reply_id=reply_data['id'],
                message=message.strip(),
                created_time=datetime.now(),
                user_name=os.getenv('FACEBOOK_PAGE_NAME', 'Admin'),
                posted_to_facebook=True
            )
            
            session.add(reply)
            session.commit()
            
            flash('Reply posted successfully', 'success')
        else:
            # Save the reply with error status
            reply = CommentReply(
                comment_id=comment_id,
                reply_id=f"error_{datetime.now().timestamp()}",
                message=message.strip(),
                created_time=datetime.now(),
                user_name=os.getenv('FACEBOOK_PAGE_NAME', 'Admin'),
                posted_to_facebook=False,
                post_error="Failed to post to Facebook"
            )
            
            session.add(reply)
            session.commit()
            flash('Failed to post reply to Facebook', 'danger')
        
        return redirect(url_for('comment_detail', comment_id=comment_id))
        
    except Exception as e:
        session.rollback()
        flash(f'Error posting reply: {str(e)}', 'danger')
        return redirect(url_for('comment_detail', comment_id=comment_id))
    finally:
        session.close()

@app.route('/post_reply/<int:reply_id>', methods=['POST'])
def post_reply(reply_id):
    """Manually post a reply to Facebook"""
    session = Session()
    try:
        reply = session.query(CommentReply).filter_by(id=reply_id).first()
        if not reply:
            flash('Reply not found', 'danger')
            return redirect(request.referrer or url_for('replies'))
            
        # Post to Facebook
        fb_api = FacebookAPI()
        reply_data = fb_api.reply_to_comment(reply.comment_id, reply.message)
        
        if reply_data and 'id' in reply_data:
            reply.posted_to_facebook = True
            reply.post_error = None
            reply.reply_id = reply_data['id']  # Update with real Facebook ID
            session.commit()
            flash('Reply posted successfully!', 'success')
        else:
            reply.post_error = "Failed to post to Facebook"
            session.commit()
            flash('Failed to post reply to Facebook', 'danger')
            
        return redirect(url_for('comment_detail', comment_id=reply.comment_id))
        
    except Exception as e:
        flash(f'Error posting reply: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('comment_detail', comment_id=reply.comment_id))
    finally:
        session.close()


# Add these imports to your app.py
from sqlalchemy import or_, and_

# Add these routes to your app.py

@app.route('/generate_response/<comment_id>')
def generate_response(comment_id):
    """Generate an AI response for a comment"""
    session = Session()
    try:
        comment = session.query(Comment).filter_by(comment_id=comment_id).first()
        if not comment:
            flash('Comment not found', 'danger')
            return redirect(request.referrer or url_for('comments'))
        
        # Get post context if available
        post_context = None
        if comment.post_rel:
            post_context = comment.post_rel.message
        
        # Generate response using AI
        evaluator = CommentEvaluator()
        evaluation = evaluator.evaluate_comment(comment.message, post_context)
        
        if evaluation['success']:
            # Save as a draft
            draft = ResponseDraft(
                comment_id=comment_id,
                message=evaluation['response'],
                generated_at=datetime.now()
            )
            session.add(draft)
            session.commit()
            
            flash('Response generated successfully!', 'success')
            return redirect(url_for('response_drafts'))
        else:
            flash(f'Failed to generate response: {evaluation.get("error", "Unknown error")}', 'danger')
            return redirect(request.referrer or url_for('comments'))
            
    except Exception as e:
        session.rollback()
        flash(f'Error generating response: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('comments'))
    finally:
        session.close()

@app.route('/response_drafts')
def response_drafts():
    """View all response drafts"""
    session = Session()
    try:
        # Get filter parameters
        status_filter = request.args.get('status', 'all')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Base query
        query = session.query(ResponseDraft).join(Comment)
        
        # Apply filters
        if status_filter == 'posted':
            query = query.filter(ResponseDraft.posted == True)
        elif status_filter == 'pending':
            query = query.filter(ResponseDraft.posted == False)
        
        # Get total count for pagination
        total = query.count()
        
        # Get paginated results
        drafts = query.order_by(ResponseDraft.generated_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        return render_template('response_drafts.html', 
                             drafts=drafts,
                             status_filter=status_filter,
                             page=page,
                             per_page=per_page,
                             total=total)
        
    except Exception as e:
        flash(f'Error loading response drafts: {str(e)}', 'danger')
        return redirect(url_for('index'))
    finally:
        session.close()

@app.route('/post_draft/<int:draft_id>')
def post_draft(draft_id):
    """Post a draft response to Facebook"""
    session = Session()
    try:
        draft = session.query(ResponseDraft).filter_by(id=draft_id).first()
        if not draft:
            flash('Draft not found', 'danger')
            return redirect(url_for('response_drafts'))
        
        if draft.posted:
            flash('This response has already been posted', 'warning')
            return redirect(url_for('response_drafts'))
        
        # Post to Facebook
        fb_api = FacebookAPI()
        reply_data = fb_api.reply_to_comment(draft.comment_id, draft.message)
        
        if reply_data and 'id' in reply_data:
            # Update draft status
            draft.posted = True
            draft.posted_at = datetime.now()
            draft.posted_id = reply_data['id']
            draft.post_error = None
            
            # Also create a CommentReply record
            reply = CommentReply(
                comment_id=draft.comment_id,
                reply_id=reply_data['id'],
                message=draft.message,
                created_time=datetime.now(),
                user_name=os.getenv('FACEBOOK_PAGE_NAME', 'Admin'),
                ai_generated=True,
                posted_to_facebook=True
            )
            session.add(reply)
            
            session.commit()
            flash('Response posted successfully!', 'success')
        else:
            draft.post_error = "Failed to post to Facebook"
            session.commit()
            flash('Failed to post response to Facebook', 'danger')
        
        return redirect(url_for('response_drafts'))
            
    except Exception as e:
        session.rollback()
        flash(f'Error posting response: {str(e)}', 'danger')
        return redirect(url_for('response_drafts'))
    finally:
        session.close()

@app.route('/delete_draft/<int:draft_id>')
def delete_draft(draft_id):
    """Delete a response draft"""
    session = Session()
    try:
        draft = session.query(ResponseDraft).filter_by(id=draft_id).first()
        if not draft:
            flash('Draft not found', 'danger')
            return redirect(url_for('response_drafts'))
        
        session.delete(draft)
        session.commit()
        flash('Draft deleted successfully', 'success')
        
        return redirect(url_for('response_drafts'))
            
    except Exception as e:
        session.rollback()
        flash(f'Error deleting draft: {str(e)}', 'danger')
        return redirect(url_for('response_drafts'))
    finally:
        session.close()

@app.route('/edit_draft/<int:draft_id>', methods=['GET', 'POST'])
def edit_draft(draft_id):
    """Edit a response draft"""
    session = Session()
    try:
        draft = session.query(ResponseDraft).filter_by(id=draft_id).first()
        if not draft:
            flash('Draft not found', 'danger')
            return redirect(url_for('response_drafts'))
        
        if request.method == 'POST':
            new_message = request.form.get('message')
            if not new_message or not new_message.strip():
                flash('Message cannot be empty', 'danger')
                return render_template('edit_draft.html', draft=draft)
            
            draft.message = new_message.strip()
            session.commit()
            
            flash('Draft updated successfully', 'success')
            return redirect(url_for('response_drafts'))
        
        return render_template('edit_draft.html', draft=draft)
            
    except Exception as e:
        session.rollback()
        flash(f'Error editing draft: {str(e)}', 'danger')
        return redirect(url_for('response_drafts'))
    finally:
        session.close()

@app.route('/batch_generate_responses', methods=['POST'])
def batch_generate_responses():
    """Generate responses for multiple comments at once"""
    session = Session()
    try:
        # Get data from JSON request
        data = request.get_json()
        app.logger.debug(f"Batch generate request JSON data: {data}")
        
        if not data or 'comment_ids' not in data:
            app.logger.error("No comment_ids found in JSON data")
            return jsonify({
                'success': False,
                'error': 'No comments selected'
            }), 400
        
        comment_ids = data['comment_ids']
        app.logger.debug(f"Received comment_ids: {comment_ids}")
        
        if not comment_ids:
            app.logger.warning("Empty comment_ids list")
            return jsonify({
                'success': False,
                'error': 'No comments selected'
            }), 400
        
        evaluator = CommentEvaluator()
        success_count = 0
        error_count = 0
        
        for comment_id in comment_ids:
            try:
                app.logger.debug(f"Processing comment ID: {comment_id}")
                comment = session.query(Comment).filter_by(comment_id=comment_id).first()
                if not comment:
                    app.logger.warning(f"Comment not found: {comment_id}")
                    error_count += 1
                    continue
                
                # Check if draft already exists
                existing_draft = session.query(ResponseDraft).filter_by(comment_id=comment_id, posted=False).first()
                if existing_draft:
                    app.logger.debug(f"Draft already exists for comment: {comment_id}")
                    continue
                
                # Get post context if available
                post_context = None
                if comment.post_rel:
                    post_context = comment.post_rel.message
                
                # Generate response
                evaluation = evaluator.evaluate_comment(comment.message, post_context)
                
                if evaluation['success']:
                    # Save as draft
                    draft = ResponseDraft(
                        comment_id=comment_id,
                        message=evaluation['response'],
                        generated_at=datetime.now()
                    )
                    session.add(draft)
                    success_count += 1
                    app.logger.debug(f"Successfully generated response for comment: {comment_id}")
                else:
                    error_count += 1
                    app.logger.error(f"Failed to generate response for comment {comment_id}: {evaluation.get('error', 'Unknown error')}")
                    
            except Exception as e:
                error_count += 1
                app.logger.error(f"Error generating response for comment {comment_id}: {str(e)}")
                app.logger.error(traceback.format_exc())
        
        session.commit()
        app.logger.info(f"Batch response generation completed: {success_count} successes, {error_count} errors")
        
        return jsonify({
            'success': True,
            'generated': success_count,
            'errors': error_count
        })
            
    except Exception as e:
        session.rollback()
        app.logger.error(f"Error in batch_generate_responses: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()

# Add to your app.py
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime

def setup_logging():
    """Set up application logging"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Get the current date for log file naming
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Set up loggers
    loggers = {
        'app': logging.getLogger('app'),
        'openai': logging.getLogger('openai'),
        'comment_evaluator': logging.getLogger('comment_evaluator')
    }
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]'
    )
    
    # Create handlers
    # Main application log
    app_handler = RotatingFileHandler(
        f'logs/facebook_analytics_{current_date}.log',
        maxBytes=1024 * 1024 * 10,  # 10MB
        backupCount=10
    )
    app_handler.setFormatter(formatter)
    
    # OpenAI-specific log
    openai_handler = RotatingFileHandler(
        f'logs/openai_requests_{current_date}.log',
        maxBytes=1024 * 1024 * 5,  # 5MB
        backupCount=10
    )
    openai_handler.setFormatter(formatter)
    
    # Set levels and add handlers
    for name, logger in loggers.items():
        logger.setLevel(logging.DEBUG if app.debug else logging.INFO)
        if name == 'openai':
            logger.addHandler(openai_handler)
        else:
            logger.addHandler(app_handler)
        
        # Also add console handler in development
        if app.debug:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

# Call this function when your app starts
setup_logging()


# Add to your app.py
@app.route('/openai_usage')
def openai_usage():
    """View OpenAI API usage statistics"""
    session = Session()
    try:
        # Get usage statistics
        total_requests = session.query(OpenAILog).count()
        successful_requests = session.query(OpenAILog).filter_by(success=True).count()
        failed_requests = session.query(OpenAILog).filter_by(success=False).count()
        total_tokens = session.query(func.sum(OpenAILog.tokens_used)).scalar() or 0
        
        # Get recent logs
        recent_logs = session.query(OpenAILog).order_by(OpenAILog.created_at.desc()).limit(50).all()
        
        # Calculate estimated cost (approximate)
        # Note: GPT-3.5-turbo is $0.002 per 1K tokens as of my knowledge cutoff
        estimated_cost = (total_tokens / 1000) * 0.002
        
        return render_template('openai_usage.html',
                             total_requests=total_requests,
                             successful_requests=successful_requests,
                             failed_requests=failed_requests,
                             total_tokens=total_tokens,
                             estimated_cost=estimated_cost,
                             recent_logs=recent_logs)
        
    except Exception as e:
        flash(f'Error retrieving OpenAI usage: {str(e)}', 'danger')
        return redirect(url_for('index'))
    finally:
        session.close()
        

# Add to your app.py
from message_evaluator import MessageEvaluator

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """
    Verify the webhook with Facebook
    """
    hub_mode = request.args.get('hub.mode')
    hub_token = request.args.get('hub.verify_token')
    hub_challenge = request.args.get('hub.challenge')
    
    if hub_mode == 'subscribe' and hub_token == os.environ.get('FACEBOOK_VERIFY_TOKEN'):
        app.logger.info("Webhook verified successfully")
        return hub_challenge
    else:
        app.logger.error("Webhook verification failed")
        return "Verification failed", 403

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """
    Handle incoming webhook events from Facebook
    """
    try:
        data = request.get_json()
        app.logger.debug(f"Webhook received: {data}")
        
        # Make sure this is a page subscription
        if data.get('object') == 'page':
            # Iterate over each entry
            for entry in data['entry']:
                page_id = entry['id']
                timestamp = entry['time']
                
                # Iterate over each messaging event
                for messaging_event in entry.get('messaging', []):
                    # Handle the message event
                    handle_message_event(messaging_event)
        
        return "EVENT_RECEIVED", 200
        
    except Exception as e:
        app.logger.error(f"Error handling webhook: {str(e)}")
        return "ERROR", 500

def handle_message_event(event):
    """
    Process a message event from Facebook
    """
    session = Session()
    try:
        sender_id = event['sender']['id']
        recipient_id = event['recipient']['id']
        
        # Check if this is a message event
        if 'message' in event:
            message_text = event['message'].get('text', '')
            message_id = event['message'].get('mid')
            
            if not message_text:
                app.logger.warning("Received message with no text")
                return
            
            app.logger.info(f"New message from {sender_id}: {message_text[:50]}...")
            
            # Get or create conversation
            conversation = session.query(Conversation).filter_by(
                conversation_id=sender_id).first()
            
            if not conversation:
                conversation = Conversation(
                    conversation_id=sender_id,
                    snippet=message_text[:100],
                    updated_time=datetime.now(),
                    participants=json.dumps({'sender_id': sender_id, 'recipient_id': recipient_id})
                )
                session.add(conversation)
            
            # Save the incoming message
            message = Message(
                conversation_id=sender_id,
                message_id=message_id,
                sender_id=sender_id,
                sender_name="Customer",  # We'll try to get the actual name later
                recipient_id=recipient_id,
                recipient_name=os.getenv('FACEBOOK_PAGE_NAME', 'Page'),
                message_text=message_text,
                created_time=datetime.now()
            )
            session.add(message)
            session.commit()
            
            # Generate AI response
            message_evaluator = MessageEvaluator()
            
            # Get conversation history for context
            history_messages = session.query(Message).filter_by(
                conversation_id=sender_id).order_by(Message.created_time.desc()).limit(10).all()
            
            conversation_history = ""
            if len(history_messages) > 1:  # More than just the current message
                # Format the conversation history
                history_list = []
                for msg in reversed(history_messages[:-1]):  # Exclude the current message
                    sender = "Customer" if msg.sender_id == sender_id else "You"
                    history_list.append(f"{sender}: {msg.message_text}")
                
                conversation_history = "\n".join(history_list)
            
            # Generate response
            response = message_evaluator.generate_response(message_text, conversation_history)
            
            if response['success']:
                # Send the response via Facebook API
                fb_api = FacebookAPI()
                send_success = fb_api.send_message(sender_id, response['response'])
                
                # Save the response
                message_response = MessageResponse(
                    message_id=message_id,
                    response_text=response['response'],
                    generated_at=datetime.now(),
                    sent_at=datetime.now() if send_success else None,
                    ai_generated=True,
                    tokens_used=response.get('tokens_used', 0),
                    processing_time=response.get('processing_time', 0)
                )
                session.add(message_response)
                
                # If sent successfully, also save as a message in the conversation
                if send_success:
                    response_message = Message(
                        conversation_id=sender_id,
                        message_id=f"ai_{datetime.now().timestamp()}",
                        sender_id=recipient_id,
                        sender_name=os.getenv('FACEBOOK_PAGE_NAME', 'Page'),
                        recipient_id=sender_id,
                        recipient_name="Customer",
                        message_text=response['response'],
                        created_time=datetime.now(),
                        is_ai_generated=True
                    )
                    session.add(response_message)
                
                session.commit()
                app.logger.info(f"AI response sent to {sender_id}")
            else:
                app.logger.error(f"Failed to generate response: {response.get('error')}")
        
    except Exception as e:
        app.logger.error(f"Error handling message event: {str(e)}")
        session.rollback()
    finally:
        session.close()


# Add to your app.py
@app.route('/messages/ai')
def ai_message_responses():
    """View AI-generated message responses"""
    session = Session()
    try:
        responses = session.query(MessageResponse).order_by(
            MessageResponse.generated_at.desc()).all()
        
        return render_template('ai_message_responses.html', responses=responses)
        
    except Exception as e:
        flash(f'Error loading AI responses: {str(e)}', 'danger')
        return redirect(url_for('messages'))
    finally:
        session.close()

@app.route('/message/<message_id>/respond', methods=['POST'])
def respond_to_message(message_id):
    """Manually respond to a message"""
    session = Session()
    try:
        message = session.query(Message).filter_by(message_id=message_id).first()
        if not message:
            flash('Message not found', 'danger')
            return redirect(request.referrer or url_for('messages'))
        
        response_text = request.form.get('response_text')
        if not response_text:
            flash('Response text cannot be empty', 'danger')
            return redirect(request.referrer or url_for('messages'))
        
        # Send response via Facebook API
        fb_api = FacebookAPI()
        success = fb_api.send_message(message.sender_id, response_text)
        
        if success:
            # Save the response
            message_response = MessageResponse(
                message_id=message_id,
                response_text=response_text,
                generated_at=datetime.now(),
                sent_at=datetime.now(),
                ai_generated=False
            )
            session.add(message_response)
            
            # Also save as a message in the conversation
            response_message = Message(
                conversation_id=message.conversation_id,
                message_id=f"manual_{datetime.now().timestamp()}",
                sender_id=message.recipient_id,
                sender_name=os.getenv('FACEBOOK_PAGE_NAME', 'Page'),
                recipient_id=message.sender_id,
                recipient_name=message.sender_name or "Customer",
                message_text=response_text,
                created_time=datetime.now(),
                is_ai_generated=False
            )
            session.add(response_message)
            
            session.commit()
            flash('Response sent successfully', 'success')
        else:
            flash('Failed to send response', 'danger')
        
        return redirect(request.referrer or url_for('messages'))
            
    except Exception as e:
        session.rollback()
        flash(f'Error sending response: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('messages'))
    finally:
        session.close()

# app.py
@app.route('/fetch_messages')
def fetch_messages():
    """Fetch messages from Facebook and save to database"""
    session = Session()
    try:
        fb_api = FacebookAPI()
        
        # Show loading immediately
        flash('Starting message fetch...', 'info')
        
        # Fetch conversations and messages
        result = fb_api.fetch_all_conversations_with_messages(
            conversations_limit=50,
            messages_limit=100
        )
        
        if 'error' in result:
            flash(f'Error fetching messages: {result["error"]}', 'danger')
            return redirect(url_for('messages'))
        
        # Process and save to database
        saved_conversations = 0
        saved_messages = 0
        
        for conv_data in result['conversations']:
            conversation = conv_data['conversation']
            messages = conv_data['messages']
            
            # Save or update conversation
            existing_conv = session.query(Conversation).filter_by(
                conversation_id=conversation['id']).first()
            
            if existing_conv:
                # Update existing conversation
                existing_conv.snippet = conversation.get('snippet', '')[:500]
                existing_conv.updated_time = datetime.fromisoformat(
                    conversation['updated_time'].replace('Z', '+00:00'))
                existing_conv.message_count = conversation.get('message_count', 0)
                existing_conv.participants = json.dumps(conversation.get('participants', {}))
                existing_conv.can_reply = conversation.get('can_reply', True)
            else:
                # Create new conversation
                new_conv = Conversation(
                    conversation_id=conversation['id'],
                    snippet=conversation.get('snippet', '')[:500],
                    updated_time=datetime.fromisoformat(
                        conversation['updated_time'].replace('Z', '+00:00')),
                    message_count=conversation.get('message_count', 0),
                    participants=json.dumps(conversation.get('participants', {})),
                    can_reply=conversation.get('can_reply', True)
                )
                session.add(new_conv)
            
            saved_conversations += 1
            
            # Save messages
            for msg in messages:
                # Check if message already exists
                existing_msg = session.query(Message).filter_by(
                    message_id=msg['id']).first()
                
                if existing_msg:
                    # Update existing message
                    existing_msg.message_text = msg.get('message', '')
                    existing_msg.created_time = datetime.fromisoformat(
                        msg['created_time'].replace('Z', '+00:00'))
                    
                    # Update sender/recipient info if available
                    if 'from' in msg:
                        existing_msg.sender_id = msg['from'].get('id', '')
                        existing_msg.sender_name = msg['from'].get('name', '')
                    if 'to' in msg and msg['to'].get('data'):
                        existing_msg.recipient_id = msg['to']['data'][0].get('id', '')
                        existing_msg.recipient_name = msg['to']['data'][0].get('name', '')
                else:
                    # Create new message
                    sender_id = msg['from'].get('id', '') if 'from' in msg else ''
                    sender_name = msg['from'].get('name', '') if 'from' in msg else ''
                    
                    recipient_id = ''
                    recipient_name = ''
                    if 'to' in msg and msg['to'].get('data'):
                        recipient_id = msg['to']['data'][0].get('id', '')
                        recipient_name = msg['to']['data'][0].get('name', '')
                    
                    new_msg = Message(
                        conversation_id=conversation['id'],
                        message_id=msg['id'],
                        sender_id=sender_id,
                        sender_name=sender_name,
                        recipient_id=recipient_id,
                        recipient_name=recipient_name,
                        message_text=msg.get('message', ''),
                        created_time=datetime.fromisoformat(
                            msg['created_time'].replace('Z', '+00:00')),
                        has_attachments=bool(msg.get('attachments', {}).get('data', []))
                    )
                    session.add(new_msg)
                
                saved_messages += 1
        
        session.commit()
        
        flash(f'Successfully fetched {saved_conversations} conversations with {saved_messages} messages', 'success')
        return redirect(url_for('messages'))
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error fetching messages: {str(e)}")
        flash(f'Error fetching messages: {str(e)}', 'danger')
        return redirect(url_for('messages'))
    finally:
        session.close()

@app.route('/api/conversations')
def api_conversations():
    """API endpoint to get conversations"""
    session = Session()
    try:
        conversations = session.query(Conversation).order_by(
            Conversation.updated_time.desc()).all()
        
        conversations_data = []
        for conv in conversations:
            conversations_data.append({
                'id': conv.id,
                'conversation_id': conv.conversation_id,
                'snippet': conv.snippet,
                'updated_time': conv.updated_time.isoformat(),
                'message_count': conv.message_count,
                'participants': json.loads(conv.participants) if conv.participants else [],
                'can_reply': conv.can_reply
            })
        
        return jsonify(conversations_data)
        
    except Exception as e:
        logger.error(f"Error fetching conversations: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

@app.route('/api/conversation/<conversation_id>/messages')
def api_conversation_messages(conversation_id):
    """API endpoint to get messages for a specific conversation"""
    session = Session()
    try:
        messages = session.query(Message).filter_by(
            conversation_id=conversation_id).order_by(Message.created_time).all()
        
        messages_data = []
        for msg in messages:
            messages_data.append({
                'id': msg.id,
                'message_id': msg.message_id,
                'sender_id': msg.sender_id,
                'sender_name': msg.sender_name,
                'recipient_id': msg.recipient_id,
                'recipient_name': msg.recipient_name,
                'message_text': msg.message_text,
                'created_time': msg.created_time.isoformat(),
                'has_attachments': msg.has_attachments,
                'is_ai_generated': msg.is_ai_generated if hasattr(msg, 'is_ai_generated') else False
            })
        
        return jsonify(messages_data)
        
    except Exception as e:
        logger.error(f"Error fetching messages: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)