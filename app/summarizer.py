import os
from groq import Groq
from dotenv import load_dotenv
import json

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def analyze_article(title: str, description: str):
    prompt = f"""
    Analyze this news article and return ONLY a JSON response with these fields:
    - summary: a 2-3 sentence summary
    - category: one of [technology, business, sports, health, science, entertainment, politics, general]
    - sentiment: one of [positive, negative, neutral]

    Article Title: {title}
    Article Description: {description}

    Return ONLY valid JSON, nothing else.
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    text = response.choices[0].message.content.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)

def get_embedding(text: str):
    # We use Groq to generate a simple embedding via text similarity
    # Since Groq doesn't have embeddings, we'll use a sentence into numbers approach
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{
            "role": "user",
            "content": f"Represent this text as a comma-separated list of exactly 1536 floating point numbers between -1 and 1 for semantic embedding. Return ONLY the numbers, nothing else: {text[:500]}"
        }],
        temperature=0.0
    )
    text_response = response.choices[0].message.content.strip()
    numbers = [float(x.strip()) for x in text_response.split(",")]
    # Pad or truncate to exactly 1536
    if len(numbers) < 1536:
        numbers.extend([0.0] * (1536 - len(numbers)))
    return numbers[:1536]