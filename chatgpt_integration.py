# chatgpt_integration.py - Updated for modern OpenAI API

# Import the OpenAI library
from openai import OpenAI
import os

# Initialize the client with your API key
# Recommended: Store your API key in an environment variable
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def chat_with_gpt(prompt, model="gpt-3.5-turbo", temperature=0.7):
    """
    Send a prompt to ChatGPT and return the response
    
    Args:
        prompt (str): The message to send to ChatGPT
        model (str): The model to use (default: gpt-3.5-turbo)
        temperature (float): Controls randomness (0.0 to 1.0)
    
    Returns:
        str: The response from ChatGPT
    """
    try:
        # Create a chat completion
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=temperature
        )
        
        # Extract and return the response text
        return response.choices[0].message.content
        
    except Exception as e:
        return f"An error occurred: {str(e)}"

# Example usage
if __name__ == "__main__":
    # Test the function
    response = chat_with_gpt("Hello, how are you?")
    print("ChatGPT response:", response)