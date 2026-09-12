import json
import os
from datetime import date
from google import genai
from google.genai import types

# Initialize Gemini Client (reads GEMINI_API_KEY from environment or config)
client = genai.Client()


def analyze_inventory_demand(
    inventory_items: list, location: str = "Maharashtra, India"
):
  """Uses Gemini to evaluate inventory demand based on current date,

  upcoming festivals, weather conditions, and dead-stock risks.
  """
  if not inventory_items:
    return []

  current_date = date.today().strftime("%B %d, %Y")

  prompt = f"""
    You are an expert FMCG & Kirana Store supply chain analyst in {location}.
    Current Date: {current_date}
    
    Analyze the following shopkeeper inventory:
    {json.dumps(inventory_items, indent=2)}
    
    Evaluate each item based on:
    1. Seasonal Demand: Current month/season in {location} (e.g., monsoon, summer, winter).
    2. Upcoming Festivals & Events within 30-45 days (e.g., Ganesh Chaturthi, Diwali, Navratri, Holi, Eid, Makar Sankranti).
    3. Stock Status:
       - 'SURGE': High upcoming demand. Recommend restocking quantity.
       - 'STABLE': Regular demand.
       - 'DEAD_STOCK': Low turnover risk. Recommend a discount or bundling strategy.

    Respond STRICTLY with a valid JSON array of objects with these exact keys:
    [
      {{
        "item_name": "string",
        "status": "SURGE" | "STABLE" | "DEAD_STOCK",
        "reason": "Brief 1-line reason (festival, weather, or seasonal trend)",
        "action": "Clear 1-line advice (e.g., 'Stock +20 units for Ganesh Chaturthi' or 'Offer 5% combo discount')"
      }}
    ]
    """

  try:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    return json.loads(response.text)
  except Exception as e:
    print(f"Demand analysis error: {e}")
    return []
