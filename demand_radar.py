import json
import os
from datetime import date
from google import genai
from google.genai import types
import streamlit as st


def get_gemini_client():
  api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
  if not api_key:
    raise ValueError(
        "Missing GEMINI_API_KEY in Streamlit Secrets or environment variables."
    )
  return genai.Client(api_key=api_key)


def analyze_inventory_demand(
    inventory_items: list,
    location: str = "Maharashtra, India",
    lang_name: str = "English",
):
  if not inventory_items:
    return [], None

  current_date = date.today().strftime("%B %d, %Y")

  prompt = f"""
    You are an expert FMCG & Kirana Store supply chain analyst in {location}.
    Current Date: {current_date}
    Target Language for descriptions: {lang_name}
    
    Analyze the following shopkeeper inventory:
    {json.dumps(inventory_items, indent=2)}
    
    Evaluate each item based on:
    1. Seasonal Demand: Current month/season in {location} (monsoon, summer, winter, harvest).
    2. Upcoming Festivals & Events in the next 30-45 days (e.g., Ganesh Chaturthi, Navratri, Diwali, Makar Sankranti, Eid, local jathras).
    3. Stock Status:
       - 'SURGE': High upcoming demand.
       - 'STABLE': Regular demand.
       - 'DEAD_STOCK': Low turnover risk.

    Write the 'reason' and 'action' fields strictly in {lang_name}.
    Keep 'status' as one of the exact English enum values: "SURGE", "STABLE", "DEAD_STOCK".

    Respond STRICTLY with a valid JSON array of objects:
    [
      {{
        "item_name": "string",
        "status": "SURGE" | "STABLE" | "DEAD_STOCK",
        "reason": "Short 1-line reason in {lang_name}",
        "action": "Actionable 1-line restocking or discount advice in {lang_name}"
      }}
    ]
    """

  try:
    client = get_gemini_client()
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    return json.loads(response.text), None
  except Exception as e:
    return [], str(e)
