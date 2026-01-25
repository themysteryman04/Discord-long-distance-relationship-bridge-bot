from google import genai
from google.genai import types # Import types for advanced config
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-3-flash-preview" # Switched to 3.0 Flash (Faster/Smarter than preview)

# --- DAILY QUESTION ---
async def get_ai_question():
    try:
        prompt = """
        You are a relationship coach for a long-distance couple. Generate ONE unique question for them to answer.
        
        CRITICAL INSTRUCTION: Do NOT ask about wrestling, fighting, or superpowers.
        
        Rotate strictly between these themes:
        1. 🧠 DEEP: "What is a core memory from childhood you've never told me?"
        2. 🔥 SPICY: "What is one thing I do that drives you crazy in a good way?"
        3. 🔮 FUTURE: "In 10 years, what does our Sunday morning look like?"
        4. 🤪 HYPOTHETICAL: "If we had to switch careers tomorrow, what would we be?"
        5. 🕰️ NOSTALGIA: "What was the exact moment you knew you liked me?"
        
        Output ONLY the question. Keep it short.
        """
        
        response = client.models.generate_content(
            model=MODEL_NAME, 
            contents=prompt, 
            config=types.GenerateContentConfig(
                temperature=1.1, # Higher creativity to avoid repetition
                top_p=0.95,
                top_k=40,
            )
        )
        return f"**{response.text.strip().replace('*', '').replace('"', '')}**"
    except Exception as e:
        print(f"⚠️ AI Error: {e}")
        return "**If we could teleport anywhere right now, where would we go?**"

# --- SMART DECISION MAKER ---
async def get_choices(category, user_input=""):
    try:
        prompt = f"""
        Give me exactly 3 distinct, creative options for: {category}.
        User Context: "{user_input}"
        
        INSTRUCTIONS:
        1. If 'Food/Date': Suggest recipes they can cook 'together' on video call, or delivery ideas.
        2. If 'Media': Suggest specific movies/books.
        3. STRICTLY Muslim-friendly (Halal, no alcohol).
        4. Format: Option 1|Option 2|Option 3
        """
        
        response = client.models.generate_content(
            model=MODEL_NAME, 
            contents=prompt, 
            config=types.GenerateContentConfig(temperature=0.8) 
        )
        
        raw_text = response.text.strip()
        options = raw_text.split('|')
        
        if len(options) < 3:
            return [f"Option 1", f"Option 2", f"Option 3"]
            
        return [opt.strip() for opt in options[:3]]

    except Exception as e:
        print(f"⚠️ AI Error: {e}")
        return ["Error", "Try again", "Check logs"]

# --- TIME PARSER ---
async def extract_datetime(user_text, current_time_str):
    try:
        prompt = f"""
        Act as a Date Parser.
        User Input: "{user_text}"
        Current Time (Malaysia): {current_time_str}
        OUTPUT: YYYY-MM-DD HH:MM:SS or "None"
        """
        response = client.models.generate_content(
            model=MODEL_NAME, 
            contents=prompt, 
            config=types.GenerateContentConfig(temperature=0.0) # Strict logic
        )
        return response.text.strip().replace('"', '').replace("'", "")
    except:
        return "None"

# --- UPDATED: TRUTH OR DARE ---
async def get_ai_dare():
    """
    Returns a tuple: (Dare_Text, Price_Int)
    """
    try:
        prompt = """
        Generate ONE dare for a married couple currently in a LONG DISTANCE relationship.
        
        Categories (Pick one randomly):
        1. VIRTUAL: Something done on video call (e.g., "Hold a plank for 60 seconds", "Don't blink for 1 minute").
        2. HOUSEHOLD: Something productive but annoying (e.g., "Fold all the laundry right now", "Organize your spice rack").
        3. PUBLIC/VISUAL: Done alone in public or at home, focusing on LOOKING silly rather than interacting.
           - GOOD EXAMPLES: "Wear socks on your hands to the shop", "Walk backwards around the living room", "Wear a shirt inside out".
           - BAD EXAMPLES: "Ask a stranger for time machine", "Speak nonsense to people".
        
        CONSTRAINTS:
        - NO physical touch between partners.
        - STRICTLY NO speaking to strangers or social pranks involving other people.
        - Focus on "Silent Embarrassment" or "Physical Difficulty".
        - Assign a 'Us-Bucks' reward (20-200).
        
        Format your response EXACTLY like this:
        DARE TEXT | PRICE
        """
        
        response = client.models.generate_content(
            model=MODEL_NAME, 
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=1.2, # High variety
                top_p=0.95,
                top_k=60,
            )
        )
        
        raw = response.text.strip()
        parts = raw.split('|')
        
        if len(parts) == 2:
            return parts[0].strip(), int(parts[1].strip())
        else:
            return "Wear your socks on your hands for the next 10 minutes.", 30
            
    except Exception as e:
        print(f"⚠️ AI Dare Error: {e}")
        return "Send a selfie making the ugliest face possible.", 50