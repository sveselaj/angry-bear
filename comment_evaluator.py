# comment_evaluator.py
import os
import logging
import json
from typing import Dict, Any, Optional
from openai import OpenAI
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CommentEvaluator:
    def __init__(self):
        """Initialize the comment evaluator with OpenAI client"""
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.system_prompt = """
        You are a social media manager for a Facebook page. Your task is to evaluate comments and generate appropriate responses.
        
        Guidelines:
        1. Analyze the sentiment of the comment (positive, negative, neutral)
        2. Identify if the comment is a question, complaint, compliment, or general statement
        3. Generate a response that is:
           - Professional but friendly
           - Appropriate for the sentiment and content
           - Encourages engagement when suitable
           - Offers help for complaints or questions
           - Thanks users for compliments
        4. Keep responses concise (1-2 sentences typically)
        5. For negative comments, be empathetic and offer solutions
        6. For questions, provide helpful information or direct to appropriate resources
        
        Always respond in the same language as the comment.
        """

    # Add this method to your CommentEvaluator class
    def _log_to_database(self, comment_id, endpoint, model, tokens_used, 
                        processing_time, success, error_message=None):
        """Log OpenAI API usage to database"""
        try:
            from models import OpenAILog, Session
            session = Session()
            
            log_entry = OpenAILog(
                comment_id=comment_id,
                endpoint=endpoint,
                model=model,
                tokens_used=tokens_used,
                processing_time=processing_time,
                success=success,
                error_message=error_message
            )
            
            session.add(log_entry)
            session.commit()
            session.close()
            
        except Exception as e:
            # If database logging fails, log to file instead
            logger.error(f"Failed to log to database: {str(e)}")
    
    def evaluate_comment(self, comment_text: str, post_context: Optional[str] = None, 
                    comment_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluate a comment and generate a response with detailed logging
        """
        # Log the start of the request
        logger.info(f"Starting OpenAI API request for comment: {comment_text[:1000]}...")
        if post_context:
            logger.debug(f"Post context: {post_context[:100]}...")
            #logger.info(f"Post context: {post_context[:100]}...")

        start_time = datetime.now()
        tokens_used = 0
        
        try:
            # Prepare the prompt
            user_prompt = f"Comment to evaluate: {comment_text}"
            if post_context:
                user_prompt += f"\nPost context: {post_context}"
            
            # Log the request details
            logger.debug(f"OpenAI Request - Model: gpt-3.5-turbo, Temperature: 0.7")
            logger.debug(f"System Prompt: {self.system_prompt[:100]}...")
            logger.debug(f"User Prompt: {user_prompt[:1000]}...")
            #logger.info(f"User Prompt: {user_prompt[:1000]}...")

            # Get response from ChatGPT
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            # Extract the response text
            assistant_response = response.choices[0].message.content
            
            # Calculate usage and timing
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Extract token usage if available
            if hasattr(response, 'usage'):
                tokens_used = getattr(response.usage, 'total_tokens', 0)
                logger.debug(f"OpenAI Usage - Tokens: {tokens_used}")
            
            # Log successful response
            logger.info(f"OpenAI API request completed in {processing_time:.2f}s, Tokens: {tokens_used}")
            logger.debug(f"Generated response: {assistant_response}")
            
            # Log to database
            self._log_to_database(
                comment_id=comment_id,
                endpoint='evaluate_comment',
                model='gpt-3.5-turbo',
                tokens_used=tokens_used,
                processing_time=processing_time,
                success=True
            )

            return {
                "success": True,
                "response": assistant_response,
                "evaluated_at": datetime.now().isoformat(),
                "processing_time": processing_time,
                "tokens_used": tokens_used
            }
            
        except Exception as e:
            # Log the error
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            logger.error(f"OpenAI API error after {processing_time:.2f}s: {str(e)}")
            # Log error to database
            self._log_to_database(
                comment_id=comment_id,
                endpoint='evaluate_comment',
                model='gpt-3.5-turbo',
                tokens_used=0,
                processing_time=processing_time,
                success=False,
                error_message=str(e)
            )

            return {
                "success": False,
                "error": str(e),
                "evaluated_at": datetime.now().isoformat(),
                "processing_time": processing_time
            }
    
    def generate_detailed_analysis(self, comment_text: str, post_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a more detailed analysis of a comment with logging
        """
        logger.info(f"Starting detailed analysis for comment: {comment_text[:50]}...")
        start_time = datetime.now()
        
        try:
            # Prepare a prompt for detailed analysis
            analysis_prompt = f"""
            Analyze this Facebook comment in detail and provide a JSON response with the following structure:
            {{
                "sentiment": "positive/negative/neutral",
                "category": "question/complaint/compliment/general",
                "urgency": "high/medium/low",
                "key_topics": ["topic1", "topic2", ...],
                "recommended_action": "respond/ignore/escalate",
                "response_template": "A suggested response template"
            }}
            
            Comment: {comment_text}
            """
            
            if post_context:
                analysis_prompt += f"\nPost Context: {post_context}"
            
            # Log the detailed analysis request
            logger.debug(f"Detailed Analysis Request: {analysis_prompt[:200]}...")
            
            # Get analysis from ChatGPT
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a social media analyst. Provide detailed analysis of comments in JSON format."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            # Extract and parse the response
            analysis_text = response.choices[0].message.content
            
            # Calculate usage and timing
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Extract token usage if available
            tokens_used = 0
            if hasattr(response, 'usage'):
                tokens_used = getattr(response.usage, 'total_tokens', 0)
            
            # Log successful analysis
            logger.info(f"Detailed analysis completed in {processing_time:.2f}s, Tokens: {tokens_used}")
            logger.debug(f"Analysis result: {analysis_text[:200]}...")
            
            # Try to extract JSON from the response
            try:
                if "{" in analysis_text and "}" in analysis_text:
                    json_start = analysis_text.find("{")
                    json_end = analysis_text.rfind("}") + 1
                    json_str = analysis_text[json_start:json_end]
                    analysis_data = json.loads(json_str)
                else:
                    analysis_data = {"analysis": analysis_text}
            except json.JSONDecodeError:
                analysis_data = {"analysis": analysis_text}
                logger.warning("Failed to parse JSON from analysis response")
            
            return {
                "success": True,
                "analysis": analysis_data,
                "evaluated_at": datetime.now().isoformat(),
                "processing_time": processing_time,
                "tokens_used": tokens_used
            }
            
        except Exception as e:
            # Log the error
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            logger.error(f"Detailed analysis error after {processing_time:.2f}s: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "evaluated_at": datetime.now().isoformat(),
                "processing_time": processing_time
            }
        
    def _extract_response_text(self, raw_response: str) -> str:
        """
        Extract just the response text from OpenAI's output
        Handles different formats that OpenAI might return
        """
        # If the response contains "Response:" pattern, extract text after it
        response_patterns = [
            "Response:",
            "Përgjigja:",
            "Përgjigje:",
            "Reply:"
        ]
        
        for pattern in response_patterns:
            if pattern in raw_response:
                parts = raw_response.split(pattern, 1)
                if len(parts) > 1:
                    extracted = parts[1].strip()
                    # Remove any trailing labels or metadata
                    for other_pattern in response_patterns:
                        if other_pattern in extracted and other_pattern != pattern:
                            extracted = extracted.split(other_pattern)[0].strip()
                    return extracted
        
        # If no pattern found, return the original text
        return raw_response.strip()
