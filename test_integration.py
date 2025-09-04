#!/usr/bin/env python3
"""
Test program for ChatGPT Integration and Auto Responder
Run this script to test if your OpenAI API integration is working properly
"""

import os
import sys
from openai import OpenAI
from datetime import datetime

# Add the current directory to Python path to import your modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_chatgpt_integration():
    """Test the ChatGPT integration"""
    print("Testing ChatGPT Integration...")
    
    # Check if API key is set
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY environment variable not set")
        return False
    
    # Initialize the OpenAI client
    try:
        client = OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized successfully")
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize OpenAI client: {e}")
        return False
    
    # Test a simple chat completion
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello, how are you?"}],
            max_tokens=50
        )
        
        if response.choices and response.choices[0].message.content:
            print("✅ ChatGPT API test successful")
            print(f"Response: {response.choices[0].message.content}")
            return True
        else:
            print("❌ ERROR: Empty response from ChatGPT API")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: ChatGPT API test failed: {e}")
        return False

def test_auto_responder():
    """Test the Auto Responder functionality"""
    print("\nTesting Auto Responder...")
    
    try:
        # Try to import the auto_responder module
        from auto_responder import AutoResponder
        
        # Create an instance
        responder = AutoResponder()
        print("✅ AutoResponder class instantiated successfully")
        
        # Test generating a response
        test_message = "Hello, can you help me with something?"
        response = responder.generate_response(test_message)
        
        if response and len(response) > 0:
            print("✅ Auto Responder test successful")
            print(f"Test message: {test_message}")
            print(f"Response: {response}")
            return True
        else:
            print("❌ ERROR: Empty response from Auto Responder")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: Auto Responder test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chatgpt_integration_module():
    """Test the chatgpt_integration module specifically"""
    print("\nTesting ChatGPT Integration Module...")
    
    try:
        # Try to import the chatgpt_integration module
        from chatgpt_integration import chat_with_gpt
        
        # Test the function
        test_prompt = "What is the capital of France?"
        response = chat_with_gpt(test_prompt)
        
        if response and len(response) > 0:
            print("✅ ChatGPT Integration Module test successful")
            print(f"Test prompt: {test_prompt}")
            print(f"Response: {response}")
            return True
        else:
            print("❌ ERROR: Empty response from ChatGPT Integration Module")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: ChatGPT Integration Module test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing ChatGPT Integration and Auto Responder")
    print("=" * 60)
    
    # Run tests
    chatgpt_result = test_chatgpt_integration()
    auto_responder_result = test_auto_responder()
    integration_module_result = test_chatgpt_integration_module()
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY:")
    print("=" * 60)
    print(f"ChatGPT API Integration: {'✅ PASS' if chatgpt_result else '❌ FAIL'}")
    print(f"Auto Responder: {'✅ PASS' if auto_responder_result else '❌ FAIL'}")
    print(f"ChatGPT Integration Module: {'✅ PASS' if integration_module_result else '❌ FAIL'}")
    
    if chatgpt_result and auto_responder_result and integration_module_result:
        print("\n🎉 All tests passed! Your integration is working correctly.")
        return 0
    else:
        print("\n💥 Some tests failed. Please check the error messages above.")
        return 1

if __name__ == "__main__":
    # Check if API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️  WARNING: OPENAI_API_KEY environment variable is not set")
        print("Please set it using:")
        print("  export OPENAI_API_KEY='your-api-key-here'  # Linux/macOS")
        print("  set OPENAI_API_KEY='your-api-key-here'     # Windows")
        print()
        print("You can continue with tests, but they will likely fail.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Run the tests
    sys.exit(main())