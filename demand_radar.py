import os
import json
from datetime import date
import streamlit as st
from google import genai
from google.genai import types

def get_gemini_client():
    # Check Streamlit Secrets first, then fallback to OS environment variable
    api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY. Please add it to your Streamlit Secrets or Environment Variables.")
    return genai.Client(api_key=api_key)

def analyze_inventory_demand(inventory_items: list, location: str = "Maharashtra, India"):
    if not inventory_items:
        return [], None
    
    current_date = date.today().strftime("%B %d, %Y")
    
    prompt = f"""
    You are an expert FMCG & Kirana Store supply chain analyst in {location}.
    Current Date: {current_date}
    
    Analyze the following shopkeeper inventory:
    {json.dumps(inventory_items, indent=2)}
    
    Evaluate each item based on:
    1. Seasonal Demand: Current month/season in {location} (e.g., monsoon, summer, winter).
    2. Upcoming Festivals & Events within 30-45 days (e.g., Ganesh Chaturthi, Navratri, Diwali, Holi, Eid).
    3. Stock Status:
       - 'SURGE': High upcoming demand. Recommend restocking quantity.
       - 'STABLE': Regular demand.
       - 'DEAD_STOCK': Low turnover risk. Recommend a discount or bundling strategy.

    Respond STRICTLY with a valid JSON array of objects with these exact keys:
    [
      {{
        "item_name": "string",
        "status": "SURGE" | "STABLE" | "DEAD_STOCK",
        "reason": "Brief 1-line reason",
        "action": "Clear 1-line advice"
      }}
    ]
    """
    
    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        return json.loads(response.text), None
    except Exception as e:
        return [], str(e)
