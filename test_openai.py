
from openai import OpenAI

client = OpenAI(api_key='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')

completion = client.chat.completions.create(
  model="gpt-3.5-turbo",
  messages=[
    {"role": "user", "content": "Hello!"}
  ]
)

print(completion.choices[0].message.content)