# message_evaluator.py
import os
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)

class MessageEvaluator:
    def __init__(self):
        """Initialize the message evaluator with OpenAI client"""
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.system_prompt = """
        You are a customer service representative for a business on Facebook. 
        Your task is to respond to private messages in a helpful, professional, and friendly manner.
        
        Guidelines:
        1. Be empathetic and understanding
        2. Provide accurate information
        3. Offer solutions to problems
        4. Ask clarifying questions when needed
        5. Maintain a consistent brand voice
        6. For complex issues, suggest moving to email or phone
        7. Always respond in the same language as the message
        
        Keep responses concise but complete (typically 2-3 sentences).
        """
    
    def generate_response(self, message_text: str, conversation_history: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a response to a Facebook message
        """
        logger.info(f"Generating response for message: {message_text[:50]}...")
        start_time = datetime.now()
        
        try:
            # Prepare the prompt with conversation history if available
            user_prompt = f"Message to respond to: {message_text}"
            if conversation_history:
                user_prompt = f"Conversation history:\n{conversation_history}\n\nLatest message: {message_text}"
            
            # Get response from ChatGPT
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            # Extract the response text
            assistant_response = response.choices[0].message.content
            
            # Calculate usage and timing
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Extract token usage
            tokens_used = 0
            if hasattr(response, 'usage'):
                tokens_used = getattr(response.usage, 'total_tokens', 0)
            
            logger.info(f"Message response generated in {processing_time:.2f}s, Tokens: {tokens_used}")
            
            return {
                "success": True,
                "response": assistant_response.strip(),
                "processing_time": processing_time,
                "tokens_used": tokens_used
            }
            
        except Exception as e:
            logger.error(f"Error generating message response: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }