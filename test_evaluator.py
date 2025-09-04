
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Test the extraction function
from comment_evaluator import CommentEvaluator


test_responses = [
    "Sentiment: Neutral Type: Question Response: Nëse jeni të interesuar për banesat, ju lutemi kontaktoni në numrin +383 48 373 737 për më shumë informacione. Faleminderit!",
    "Përgjigje: Faleminderit për komentin tuaj! Do të jemi të lumtur t'ju ndihmojmë.",
    "Just a simple response without any labels."
]

evaluator = CommentEvaluator()
for response in test_responses:
    clean = evaluator._extract_response_text(response)
    print(f"Original: {response}")
    print(f"Clean: {clean}")
    print("---")