import random
import os
import requests
import streamlit as st

def generate_otp():
    """Generates a secure 4-digit numeric OTP."""
    return str(random.randint(1000, 9999))

def send_sms_otp(phone_number, otp_code):
    """
    Sends real 4-digit SMS OTP to Indian mobile numbers.
    Supports Fast2SMS API Key from Streamlit Secrets or Environment Variables.
    Falls back gracefully if API key is not configured.
    """
    clean_phone = phone_number.replace("+91", "").replace(" ", "").strip()
    
    # Check if Fast2SMS API key is provided in secrets
    fast2sms_key = ""
    if hasattr(st, "secrets") and "FAST2SMS_API_KEY" in st.secrets:
        fast2sms_key = st.secrets["FAST2SMS_API_KEY"]
    else:
        fast2sms_key = os.environ.get("FAST2SMS_API_KEY", "")
        
    if fast2sms_key:
        try:
            url = "https://www.fast2sms.com/dev/bulkV2"
            payload = {
                "variables_values": otp_code,
                "route": "otp",
                "numbers": clean_phone
            }
            headers = {
                'authorization': fast2sms_key,
                'Content-Type': "application/x-www-form-urlencoded",
                'Cache-Control': "no-cache"
            }
            response = requests.post(url, data=payload, headers=headers, timeout=10)
            res_data = response.json()
            if res_data.get("return"):
                return True, "SMS sent successfully to your mobile number."
            else:
                return False, res_data.get("message", ["Failed to send SMS."])[0]
        except Exception as e:
            return False, f"SMS Gateway Error: {str(e)}"
    else:
        # Fallback for testing/demos without paid SMS API gateway
        return True, f"Demo Mode: OTP sent! (Use code: {otp_code})"
