from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import random 
import datetime

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

# 1. SWITCH TO STABLE MODEL (Fixes the 429/503 Crashes)
MODEL_NAME = "gemini-3-flash-preview" 

# ==========================================
# 1. DAILY QUESTION (With Rotation Fix)
# ==========================================
async def get_ai_question():
    try:
        # 2. FORCE VARIETY: Pick the theme in Python, not AI
        themes = [
            "DEEP: Ask about a childhood memory, a core value, or a fear.",
            "SPICY: Ask about a turn-on, an attractive trait, or a romantic wish.",
            "FUTURE: Ask about a specific future scenario (kids, house, travel, aging).",
            "HYPOTHETICAL: Ask a 'What if we were...' or 'Zombie apocalypse' style question.",
            "NOSTALGIA: Ask about a specific happy memory from our relationship.",
            "GRATITUDE: Ask what is one small thing they appreciate today."
        ]
        chosen_theme = random.choice(themes)

        prompt = f"""
        You are a relationship coach for a couple.
        Generate ONE unique question for them based on this theme:
        👉 {chosen_theme}
        
        CRITICAL INSTRUCTION: Do NOT ask about wrestling, fighting, or superpowers.
        Output ONLY the question text. Keep it short and engaging.
        """
        
        response = client.models.generate_content(
            model=MODEL_NAME, 
            contents=prompt, 
            config=types.GenerateContentConfig(
                temperature=1.1, # High creativity
                top_p=0.95,
                top_k=40,
            )
        )
        
        # Cleanup response
        return f"**{response.text.strip().replace('*', '').replace('"', '')}**"

    except Exception as e:
        print(f"⚠️ AI Question Error: {e}")
        return "**If we could teleport anywhere right now, where would we go?**"

# ==========================================
# 2. DAILY DARE (With Format Fix)
# ==========================================
async def get_ai_dare():
    try:
        prompt = """
        Generate ONE fun relationship dare.
        Format: DARE_TEXT | PRICE_INT
        Example: Do a chicken dance | 50
        
        Constraints: 
        - No touch (Long Distance). 
        - No strangers. 
        - Fun but slightly embarrassing or physically active (e.g., hold a plank, sing a song).
        """
        
        response = client.models.generate_content(
            model=MODEL_NAME, 
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=1.1,
                top_p=0.95,
                top_k=40,
            )
        )
        
        # 3. ROBUST CLEANING (Fixes "invalid literal" errors)
        raw = response.text.strip().replace('*', '').replace('"', '')
        
        if '|' in raw:
            parts = raw.split('|')
            return parts[0].strip(), int(parts[1].strip())
        else:
            # Fallback if AI forgets the pipe
            return raw, 30
            
    except Exception as e:
        print(f"⚠️ AI Dare Error: {e}")
        return "Send a selfie making a funny face.", 50

# ==========================================
# 3. DECISION ROOM (Food, Movies, etc.)
# ==========================================
async def get_choices(category, criteria):
    try:
        prompt = f"""
        Give me 3 distinct options for: {category}
        Based on these preferences: {criteria}
        
        Output ONLY a simple list of 3 items.
        """
        
        response = client.models.generate_content(
            model=MODEL_NAME, 
            contents=prompt
        )
        
        # Split lines and clean up "1. ", "-", etc.
        lines = response.text.strip().split('\n')
        clean_lines = [line.lstrip("1234567890.-* ") for line in lines if line.strip()]
        
        return clean_lines[:3] # Ensure we return exactly 3
        
    except Exception as e:
        print(f"⚠️ AI Decision Error: {e}")
        return ["Option A", "Option B", "Option C"]

# ==========================================
# 4. REMINDER PARSING (NLP)
# ==========================================
async def extract_datetime(user_input, current_time_str):
    try:
        prompt = f"""
        Current Time: {current_time_str}
        User Input: "{user_input}"
        
        Extract the target datetime from the input.
        Format: YYYY-MM-DD HH:MM:SS
        
        If no time is found, output: None
        """
        
        response = client.models.generate_content(
            model=MODEL_NAME, 
            contents=prompt
        )
        
        return response.text.strip()
        
    except Exception as e:
        print(f"⚠️ AI Time Error: {e}")
        return None