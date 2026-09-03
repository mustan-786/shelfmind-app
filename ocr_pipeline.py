import json
import os
import time
import streamlit as st
from google import genai
from google.genai import types

def get_gemini_client():
    """Retrieves API key securely from Streamlit Secrets or Environment Variables."""
    api_key = ""
    if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        api_key = os.environ.get("GEMINI_API_KEY", "")
    
    if not api_key:
        st.error("⚠️ GEMINI_API_KEY not found. Please configure it in Streamlit Cloud Secrets.")
        return None
    return genai.Client(api_key=api_key)

def extract_invoice_data_with_ai(image_bytes, mime_type="image/jpeg"):
    """
    Parses Kirana wholesale bills with automated fallback 
    across 3.8 Flash, 3.5 Flash-Lite, and 3.1 Pro to prevent 503 errors.
    """
    client = get_gemini_client()
    if client is None:
        return []

    prompt = """
    You are an expert document parser for Indian Kirana grocery store wholesale bills.
    Analyze this invoice image and extract all purchased line items accurately.
    
    Even if the text is faint, dot-matrix, handwritten, or on colored/pink paper:
    1. Extract the Item Name (clean standard product name with brand and size/weight if visible).
    2. Extract the Quantity (integer).
    3. Extract the Unit Wholesale Rate in INR (float).
    4. Extract the Total Amount in INR (float).
    
    Return ONLY a valid JSON array of objects with these exact keys:
    [
      {
        "Item Name": "Product Name",
        "Quantity": 10,
        "Rate (₹)": 45.0,
        "Total (₹)": 450.0
      }
    ]
    Do not wrap the response in markdown formatting or explanation. Return only the raw JSON.
    """
    
    candidate_models = [
        'gemini-3.8-flash',
        'gemini-3.5-flash-lite',
        'gemini-3.1-pro'
    ]
    
    last_error = ""
    for model_name in candidate_models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=mime_type,
                        ),
                        prompt
                    ]
                )
                
                raw_output = response.text.strip()
                
                # Clean any markdown code blocks
                if "```json" in raw_output:
                    raw_output = raw_output.split("```json")[1].split("```")[0]
                elif "```" in raw_output:
                    raw_output = raw_output.split("```")[1].split("```")[0]
                    
                data = json.loads(raw_output.strip())
                return data
                
            except Exception as e:
                err_str = str(e)
                last_error = err_str
                # If a 503 capacity surge occurs, pause briefly and allow failover
                if "503" in err_str or "UNAVAILABLE" in err_str:
                    time.sleep(1.0)
                    continue
                elif "404" in err_str:
                    break
                else:
                    break

    st.error(f"Vision AI Engine Error: {last_error}")
    return []
