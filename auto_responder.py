# auto_responder.py - Updated for modern OpenAI API

# Import the OpenAI library
from openai import OpenAI
import os
import time

# Initialize the client with your API key
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "your-api-key-here"))

class AutoResponder:
    def __init__(self, model="gpt-3.5-turbo", temperature=0.7, max_tokens=500):
        """
        Initialize the auto responder
        
        Args:
            model (str): The model to use (default: gpt-3.5-turbo)
            temperature (float): Controls randomness (0.0 to 1.0)
            max_tokens (int): Maximum tokens in response
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.conversation_history = []
    
    def add_to_history(self, role, content):
        """
        Add a message to the conversation history
        
        Args:
            role (str): 'user' or 'assistant'
            content (str): The message content
        """
        self.conversation_history.append({"role": role, "content": content})
    
    def generate_response(self, user_message, system_prompt=None):
        """
        Generate a response to the user's message
        
        Args:
            user_message (str): The user's message
            system_prompt (str): Optional system prompt to guide the assistant
        
        Returns:
            str: The generated response
        """
        # Add user message to history
        self.add_to_history("user", user_message)
        
        # Prepare messages for API call
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history
        messages.extend(self.conversation_history)
        
        try:
            # Create a chat completion
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Extract the response text
            assistant_response = response.choices[0].message.content
            
            # Add assistant response to history
            self.add_to_history("assistant", assistant_response)
            
            return assistant_response
            
        except Exception as e:
            error_msg = f"An error occurred: {str(e)}"
            print(error_msg)
            return error_msg
    
    def clear_history(self):
        """Clear the conversation history"""
        self.conversation_history = []

# Example usage
if __name__ == "__main__":
    # Create an auto responder instance
    responder = AutoResponder()
    
    # Set a system prompt (optional)
    system_prompt = "You are a helpful assistant that provides concise answers."
    
    # Test the auto responder
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("Goodbye!")
            break
            
        response = responder.generate_response(user_input, system_prompt)
        print(f"Assistant: {response}")
        print("-" * 50)