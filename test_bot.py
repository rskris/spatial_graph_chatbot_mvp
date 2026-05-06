import re
from chatbot import PropertyGraphChatbot

bot = PropertyGraphChatbot()
queries = [
    "How many coffee shops near Sierra Madre Blvd",
    "What businesses are in 600 North Rosemead Boulevard",
    "What parcel is 600 North Rosemead Boulevard on",
    "Tell me about Sierra Madre City Hall"
]

for q in queries:
    print(f"Query: {q}")
    print(bot.query(q))
    print("-" * 20)
