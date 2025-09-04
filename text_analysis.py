# text_analysis.py
from textblob import TextBlob
import numpy as np
from collections import Counter
import re
import nltk
from nltk.corpus import stopwords
import json

# Download stopwords if not already available
try:
    nltk.download('stopwords')
except:
    pass

def enhanced_sentiment_analysis(text):
    """
    Perform enhanced sentiment analysis with more detailed scoring
    """
    if not text or not isinstance(text, str):
        return 0.0, "neutral"
    
    analysis = TextBlob(text)
    polarity = analysis.sentiment.polarity
    
    # Categorize sentiment
    if polarity > 0.3:
        sentiment_category = "positive"
    elif polarity < -0.3:
        sentiment_category = "negative"
    else:
        sentiment_category = "neutral"
    
    return polarity, sentiment_category

def analyze_comment_sentiments(comments):
    """
    Analyze sentiments for a batch of comments
    """
    sentiments = []
    for comment in comments:
        polarity, category = enhanced_sentiment_analysis(comment.get('message', ''))
        comment['sentiment_score'] = polarity
        comment['sentiment_category'] = category
        sentiments.append(polarity)
    
    if sentiments:
        avg_sentiment = np.mean(sentiments)
        return avg_sentiment, sentiments
    return 0.0, []

def extract_keywords(text, num_keywords=10):
    """
    Extract keywords from text
    """
    if not text:
        return []
    
    # Remove special characters and convert to lowercase
    text = re.sub(r'[^\w\s]', '', text.lower())
    
    # Get English stopwords
    try:
        stop_words = set(stopwords.words('english'))
    except:
        stop_words = set()
    
    # Tokenize and remove stopwords
    words = [word for word in text.split() if word not in stop_words and len(word) > 2]
    
    # Count word frequency
    word_freq = Counter(words)
    
    # Return most common keywords
    return [word for word, count in word_freq.most_common(num_keywords)]

def extract_trending_topics(post_messages, num_topics=5):
    """
    Extract trending topics from a list of post messages
    """
    # Ensure we're working with a list of strings
    if not post_messages or not isinstance(post_messages, list):
        print(f"Invalid input to extract_trending_topics: {type(post_messages)}")
        return []
        
    all_keywords = []
        
    for message in post_messages:
        # Ensure each message is a string
        if not isinstance(message, str):
            print(f"Skipping non-string message: {type(message)}")
            continue
                
        keywords = extract_keywords(message)
        all_keywords.extend(keywords)
        
    # Count keyword frequency across all posts
    if all_keywords:
        topic_freq = Counter(all_keywords)
        return topic_freq.most_common(num_topics)
    else:
        return []
        
