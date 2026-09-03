import json
import os
import time
import io
import streamlit as st
from PIL import Image
from google import genai
from google.genai import types

def get_gemini_client():
    api_key = ""
    if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        api_key = os.environ.get("GEMINI_API_KEY", "")
    
    if not api_key:
        st.error("⚠️ GEMINI_API_KEY not found in Streamlit Secrets.")
        return None
    return genai.Client(api_key=api_key)

def optimize_image(image_bytes):
    """Resizes and compresses heavy mobile bill photos to prevent upload timeouts."""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    # Resize max bound to 1500px for sharp text extraction with minimal bandwidth
    img.thumbnail((1500, 1500), Image.Resampling.LANCZOS)
    
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
    return buf.getvalue()

def extract_invoice_data_with_ai(image_bytes, mime_type="image/jpeg"):
    client = get_gemini_client()
    if client is None:
        return []

    try:
        ready_bytes = optimize_image(image_bytes)
    except Exception:
        ready_bytes = image_bytes

    prompt = """
    You are an expert document parser for Indian Kirana grocery store wholesale bills.
    Analyze this invoice image and extract all purchased line items accurately.
    
    Extract:
    1. Item Name (standardized product SKU name).
    2. Quantity (integer).
    3. Rate (₹) (float unit wholesale rate in INR).
    4. Total (₹) (float total line amount).
    
    Return ONLY a valid JSON array of objects:
    [
      {
        "Item Name": "Product Name",
        "Quantity": 10,
        "Rate (₹)": 45.0,
        "Total (₹)": 450.0
      }
    ]
    Do not wrap the response in markdown fences or explanation. Return only raw JSON.
    """
    
    # Active, stable multimodal models
    candidate_models = [
        'gemini-2.5-flash',
        'gemini-2.0-flash'
    ]
    
    last_error = ""
    for model_name in candidate_models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Part.from_bytes(
                            data=ready_bytes,
                            mime_type="image/jpeg",
                        ),
                        prompt
                    ]
                )
                
                raw_output = response.text.strip()
                
                if "```json" in raw_output:
                    raw_output = raw_output.split("```json")[1].split("```")[0]
                elif "```" in raw_output:
                    raw_output = raw_output.split("```")[1].split("```")[0]
                    
                data = json.loads(raw_output.strip())
                return data
                
            except Exception as e:
                err_str = str(e)
                last_error = err_str
                # If overloaded, pause and retry
                if "503" in err_str or "UNAVAILABLE" in err_str:
                    time.sleep(1.5)
                    continue
                else:
                    break

    st.error(f"Vision AI Engine Error: {last_error}")
    return []
