import streamlit as st
import os
import base64
from PIL import Image

logo_path = "logo.png"

# 1. Load Custom App Icon for Streamlit
if os.path.exists(logo_path):
    page_icon = Image.open(logo_path)
    with open(logo_path, "rb") as img_f:
        b64_logo = base64.b64encode(img_f.read()).decode("utf-8")
        icon_data_uri = f"data:image/png;base64,{b64_logo}"
else:
    page_icon = "📦"
    icon_data_uri = ""

st.set_page_config(
    page_title="SHELF MIND",
    page_icon=page_icon,
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. Force Mobile Browser Home Screen Metadata (Icon + App Name)
pwa_header_html = f"""
    <script>
        document.title = "SHELF MIND";
        
        // Dynamically inject apple-touch-icon and shortcut icons into mobile browser head
        function setAppMeta() {{
            var iconUri = "{icon_data_uri}";
            if (iconUri) {{
                // Home screen icon for iOS / Android
                var linkApple = document.createElement('link');
                linkApple.rel = 'apple-touch-icon';
                linkApple.href = iconUri;
                document.getElementsByTagName('head')[0].appendChild(linkApple);

                var linkFavicon = document.createElement('link');
                linkFavicon.rel = 'shortcut icon';
                linkFavicon.type = 'image/png';
                linkFavicon.href = iconUri;
                document.getElementsByTagName('head')[0].appendChild(linkFavicon);
            }}
        }}
        setAppMeta();
    </script>
    <meta name="apple-mobile-web-app-title" content="SHELF MIND">
    <meta name="application-name" content="SHELF MIND">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
"""
st.markdown(pwa_header_html, unsafe_allow_html=True)

# Rest of your imports and code...
import pandas as pd
import urllib.parse
import qrcode
import io
from datetime import date
from translations import TRANSLATIONS
from ocr_pipeline import extract_invoice_data_with_ai
import database as db
import sms_service

db.init_db()

# Language Selector
lang_choice = st.selectbox(
    "🌐 Language / भाषा निवडा / भाषा चुनें",
    ["English", "मराठी (Marathi)", "हिंदी (Hindi)"],
    index=0
)
lang_key = "mr" if "Marathi" in lang_choice else "hi" if "Hindi" in lang_choice else "en"
t = TRANSLATIONS[lang_key]

# -------------------------------------------------------------
# 🔄 PERSISTENT SESSION MANAGEMENT (Preserves login on Refresh)
# -------------------------------------------------------------
query_params = st.query_params
phone_in_url = query_params.get("phone", None)

if "logged_in_store" not in st.session_state or st.session_state["logged_in_store"] is None:
    if phone_in_url:
        cached_store = db.get_shopkeeper(phone_in_url)
        if cached_store:
            st.session_state["logged_in_store"] = cached_store

# -------------------------------------------------------------
# 🏪 SHOPKEEPER LOGIN & 4-DIGIT OTP REGISTRATION
# -------------------------------------------------------------
if not st.session_state.get("logged_in_store"):
    st.title("📦 SHELF MIND")
    st.subheader("🏪 Kirana Shopkeeper Portal / दुकानदार प्रवेश")
    
    auth_mode = st.radio("Choose Option:", ["🔑 Login with Mobile", "📝 Register New Shop (with OTP)"], horizontal=True)
    
    if auth_mode == "🔑 Login with Mobile":
        with st.form("login_form"):
            phone_input = st.text_input("10-Digit Mobile Number (नोंदणीकृत मोबाईल नंबर)", placeholder="e.g. 9822012345")
            submit_login = st.form_submit_button("Access Store Dashboard", use_container_width=True, type="primary")
            
            if submit_login:
                profile = db.get_shopkeeper(phone_input)
                if profile:
                    st.session_state["logged_in_store"] = profile
                    st.query_params["phone"] = profile["phone_number"]
                    st.toast(f"Welcome back, {profile['shop_name']}!")
                    st.rerun()
                else:
                    st.error("No store found with this number. Please register your shop first.")
                    
    else:
        # Shopkeeper Registration with 4-Digit Mobile OTP Verification
        if "reg_otp" not in st.session_state:
            st.session_state["reg_otp"] = None
            st.session_state["temp_reg_data"] = {}
            
        st.markdown("### 📝 Register New Kirana Store")
        new_shop = st.text_input("Store Name (दुकानाचे नाव)", placeholder="e.g. Patil Super Shoppe")
        new_owner = st.text_input("Owner Name (दुकानदाराचे नाव)", placeholder="e.g. Aniket Patil")
        new_phone = st.text_input("10-Digit Mobile Number (मोबाईल नंबर)", placeholder="e.g. 9822012345")
        new_upi = st.text_input("Store UPI ID for Receiving Money (उदा. yourname@oksbi / 9822012345@ybl)", placeholder="e.g. 9822012345@ybl")
        
        # Step 1: Request OTP
        if st.button("📲 Send 4-Digit OTP on Mobile", use_container_width=True):
            if new_shop and new_owner and new_phone and new_upi:
                generated_otp = sms_service.generate_otp()
                st.session_state["reg_otp"] = generated_otp
                st.session_state["temp_reg_data"] = {
                    "shop_name": new_shop,
                    "owner_name": new_owner,
                    "phone_number": new_phone,
                    "upi_id": new_upi
                }
                sent_ok, msg = sms_service.send_sms_otp(new_phone, generated_otp)
                if sent_ok:
                    st.success(f"✅ {msg}")
                else:
                    st.warning(f"⚠️ {msg}")
            else:
                st.error("Please fill in all shop details before requesting OTP.")
                
        # Step 2: Verify OTP and Complete Registration
        if st.session_state.get("reg_otp"):
            with st.form("otp_verification_form"):
                entered_otp = st.text_input("Enter 4-Digit OTP received on SMS", max_chars=4, placeholder="****")
                verify_btn = st.form_submit_button("Verify OTP & Complete Registration", use_container_width=True, type="primary")
                
                if verify_btn:
                    if entered_otp.strip() == st.session_state["reg_otp"]:
                        d = st.session_state["temp_reg_data"]
                        success, err = db.register_shopkeeper(d["shop_name"], d["owner_name"], d["phone_number"], d["upi_id"])
                        if success:
                            st.session_state["logged_in_store"] = d
                            st.query_params["phone"] = d["phone_number"]
                            st.session_state["reg_otp"] = None
                            st.balloons()
                            st.success("🎉 Store verified & registered successfully!")
                            st.rerun()
                        else:
                            st.error(err)
                    else:
                        st.error("❌ Invalid OTP. Please enter the correct 4-digit code.")

    st.stop()

# -------------------------------------------------------------
# 🎯 ACTIVE STORE DASHBOARD (Logged In & Isolated)
# -------------------------------------------------------------
current_store = st.session_state["logged_in_store"]
store_phone = current_store["phone_number"]
shop_name = current_store["shop_name"]
owner_name = current_store["owner_name"]
shop_upi = current_store["upi_id"]

# --- SIDEBAR PROFILE & SETTINGS ---
st.sidebar.markdown(f"### 🏪 **{shop_name}**")
st.sidebar.caption(f"👤 Owner: **{owner_name}**")
st.sidebar.caption(f"📞 Registered Mobile: `+91 {store_phone}`")
st.sidebar.info(f"💳 Active UPI: `{shop_upi}`")

# Expandable Profile Editor Form
with st.sidebar.expander("⚙️ Edit Store Details"):
    with st.form("edit_profile_form"):
        updated_shop_name = st.text_input("Store Name (दुकानाचे नाव)", value=shop_name)
        updated_owner_name = st.text_input("Owner Name (मालकाचे नाव)", value=owner_name)
        updated_upi = st.text_input("Store UPI ID (पेमेंटसाठी UPI)", value=shop_upi)
        
        save_changes = st.form_submit_button("💾 Save Profile Changes", use_container_width=True, type="primary")
        
        if save_changes:
            if updated_shop_name and updated_owner_name and updated_upi:
                db.update_shopkeeper_profile(store_phone, updated_shop_name, updated_owner_name, updated_upi)
                
                # Update current active session
                st.session_state["logged_in_store"]["shop_name"] = updated_shop_name
                st.session_state["logged_in_store"]["owner_name"] = updated_owner_name
                st.session_state["logged_in_store"]["upi_id"] = updated_upi
                
                st.toast("✅ Store details updated successfully!")
                st.rerun()
            else:
                st.error("Please fill in all fields.")

if st.sidebar.button("🚪 Logout Store", use_container_width=True):
    st.session_state["logged_in_store"] = None
    st.session_state["parsed_items"] = None
    st.query_params.clear()
    st.rerun()

# Dynamic KPI Metrics Isolated to this Shopkeeper
total_skus, total_capital, dead_stock = db.get_kpi_metrics(store_phone)
total_udhar = db.get_total_udhar_pending(store_phone)

st.title(f"📱 {shop_name}")
st.caption(f"{t['app_subtitle']}")

k1, k2 = st.columns(2)
k1.metric(t["total_skus"], f"{total_skus} SKUs")
k2.metric(t["working_capital"], f"₹{total_capital:,.0f}")

k3, k4 = st.columns(2)
k3.metric(t["dead_stock"], f"₹{dead_stock:,.0f}")
k4.metric(t["total_udhar"], f"₹{total_udhar:,.0f}", delta="Credit Locked", delta_color="inverse")

st.divider()

# Interactive Tabs
tab1, tab2, tab3, tab4 = st.tabs([t["tab_upload"], t["tab_stock"], t["tab_alerts"], t["tab_udhar"]])

# --- TAB 1: Invoice Vision Ingestion + Human-In-The-Loop Grid ---
with tab1:
    st.subheader(t["upload_heading"])
    input_mode = st.radio("Capture Method:", ["📸 Open Phone Camera", "📁 Upload from Gallery"], horizontal=True)
    image_file = st.camera_input("Take photo of wholesale bill") if input_mode == "📸 Open Phone Camera" else st.file_uploader(t["upload_btn"], type=["jpg", "png", "jpeg"])
    
    if image_file is not None:
        file_type = image_file.type if hasattr(image_file, "type") and image_file.type else "image/jpeg"
        file_id = getattr(image_file, "name", "cam_snap")
        
        if "parsed_items" not in st.session_state or st.session_state.get("last_up") != file_id:
            with st.spinner("⚡ Vision AI is analyzing invoice layout..."):
                extracted = extract_invoice_data_with_ai(image_file.getvalue(), mime_type=file_type)
                clean = [
                    {
                        "Item Name": str(i.get("Item Name", "")),
                        "Quantity": int(i.get("Quantity", 1)),
                        "Rate (₹)": float(i.get("Rate (₹)", i.get("Rate", 0.0)))
                    }
                    for i in extracted
                ]
                st.session_state["parsed_items"] = clean
                st.session_state["last_up"] = file_id
        
        items = st.session_state.get("parsed_items", [])
        if items:
            st.success(t["upload_success"])
            st.info(t["edit_instruction"])
            
            df_edit = st.data_editor(
                pd.DataFrame(items),
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "Item Name": st.column_config.TextColumn("Product SKU", required=True),
                    "Quantity": st.column_config.NumberColumn("Qty", min_value=1, step=1, required=True),
                    "Rate (₹)": st.column_config.NumberColumn("Rate (₹)", min_value=0.0, step=0.5, format="₹%.2f", required=True)
                }
            )
            
            if st.button(f"✅ {t['save_stock_btn']}", use_container_width=True, type="primary"):
                db.add_or_update_stock(store_phone, df_edit.to_dict(orient="records"))
                st.balloons()
                st.success(t["stock_updated_toast"])
                st.session_state["parsed_items"] = None
                st.rerun()

# --- TAB 2: Live Real-Time Stock Table ---
with tab2:
    st.subheader(t["tab_stock"])
    df_live = db.get_inventory_dataframe(store_phone)
    if not df_live.empty:
        st.dataframe(df_live, use_container_width=True)
    else:
        st.info("No stock recorded yet! Scan an invoice in Tab 1 to populate inventory.")

# --- TAB 3: Demand Radar & Weather Signal Alerts ---
with tab3:
    st.subheader(t["tab_alerts"])
    st.warning(t["dead_stock_alert"])
    st.info(t["weather_alert"])

# --- TAB 4: Udhar (Credit) Ledger & Real NPCI UPI Payments / WhatsApp Reminders ---
with tab4:
    st.subheader(t["tab_udhar"])
    
    with st.expander(t["add_udhar_btn"]):
        with st.form("new_udhar_form"):
            c_name = st.text_input(t["customer_name"])
            c_phone = st.text_input(t["phone_number"], placeholder="e.g. 9822123456")
            c_amount = st.number_input(t["udhar_amount"], min_value=1.0, step=10.0, value=250.0)
            c_items = st.text_input(t["items_taken"], placeholder="e.g. 1L Oil, 1kg Sugar")
            c_due = st.date_input(t["due_date"], min_value=date.today())
            
            if st.form_submit_button(t["save_udhar"], use_container_width=True):
                if c_name and c_phone:
                    clean_phone = c_phone.replace("+91", "").replace(" ", "").strip()
                    db.add_udhar_entry(store_phone, c_name, clean_phone, c_amount, c_items, c_due)
                    st.success("Udhar entry saved!")
                    st.rerun()
                else:
                    st.error("Please enter both customer name and mobile number.")
                    
    df_udhar = db.get_udhar_records(store_phone)
    
    if not df_udhar.empty:
        for idx, row in df_udhar.iterrows():
            if row["status"] != "Paid":
                with st.container(border=True):
                    col_info, col_actions = st.columns([2, 1])
                    
                    with col_info:
                        st.markdown(f"**👤 {row['customer_name']}** (📞 `+91 {row['customer_phone']}`)")
                        st.markdown(f"💰 **Amount Due:** ₹{row['amount']:,.2f} | 📅 **Due Date:** `{row['due_date']}`")
                        if row["items_note"]:
                            st.caption(f"Items Taken: {row['items_note']}")
                            
                    with col_actions:
                        # Genuine NPCI Standard UPI URI (Opens GPay / PhonePe / Paytm directly)
                        upi_payload = f"upi://pay?pa={shop_upi}&pn={urllib.parse.quote(shop_name)}&am={row['amount']}&cu=INR&tn=Udhar_{row['id']}"
                        
                        # Generate Scannable Dynamic NPCI QR Code
                        qr = qrcode.QRCode(box_size=4, border=1)
                        qr.add_data(upi_payload)
                        qr.make(fit=True)
                        img_qr = qr.make_image(fill_color="black", back_color="white")
                        buf = io.BytesIO()
                        img_qr.save(buf, format="PNG")
                        
                        with st.expander("📲 Scan UPI QR"):
                            st.image(buf.getvalue(), caption=f"Scan to Pay ₹{row['amount']} to {shop_upi}", width=150)
                        
                        # Multilingual WhatsApp Reminder Link
                        if lang_key == "mr":
                            msg = f"नमस्कार {row['customer_name']}जी, {shop_name} दुकानाची ₹{row['amount']} उधारी बाकी आहे (वस्तू: {row['items_note']}). देय तारीख: {row['due_date']}. थेट UPI द्वारे पैसे भरण्यासाठी लिंक: {upi_payload}"
                        elif lang_key == "hi":
                            msg = f"नमस्ते {row['customer_name']}जी, {shop_name} की ₹{row['amount']} उधारी बकाया है (सामान: {row['items_note']}). अंतिम तिथि: {row['due_date']}. UPI भुगतान लिंक: {upi_payload}"
                        else:
                            msg = f"Dear {row['customer_name']}, reminder for pending store credit of ₹{row['amount']} at {shop_name}. Due Date: {row['due_date']}. Pay via UPI: {upi_payload}"
                        
                        wa_url = f"https://wa.me/91{row['customer_phone']}?text={urllib.parse.quote(msg)}"
                        st.link_button("📲 Send WhatsApp", wa_url, use_container_width=True)
                        
                        if st.button(t["mark_paid"], key=f"settle_{row['id']}", use_container_width=True):
                            db.settle_udhar(row["id"])
                            st.toast(f"Payment settled for {row['customer_name']}!")
                            st.rerun()
    else:
        st.info("No pending Udhar records for this store.")
