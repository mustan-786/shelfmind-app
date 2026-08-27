import streamlit as st
import pandas as pd
import urllib.parse
import qrcode
import io
import os
from PIL import Image
from datetime import date
from translations import TRANSLATIONS
from ocr_pipeline import extract_invoice_data_with_ai
import database as db

# Initialize SQLite Database Tables
db.init_db()

# Load Custom SHELF MIND App Icon if present
logo_path = "logo.png"
app_icon = Image.open(logo_path) if os.path.exists(logo_path) else "📦"

st.set_page_config(
    page_title="SHELF MIND",
    page_icon=app_icon,
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom PWA Meta Tags for Mobile Shortcut Branding
st.markdown("""
    <head>
        <title>SHELF MIND</title>
        <meta name="apple-mobile-web-app-title" content="SHELF MIND">
        <meta name="application-name" content="SHELF MIND">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="mobile-web-app-capable" content="yes">
    </head>
""", unsafe_allow_html=True)

# Language Selector
lang_choice = st.selectbox(
    "🌐 Language / भाषा निवडा / भाषा चुनें",
    ["English", "मराठी (Marathi)", "हिंदी (Hindi)"],
    index=0
)
lang_key = "mr" if "Marathi" in lang_choice else "hi" if "Hindi" in lang_choice else "en"
t = TRANSLATIONS[lang_key]

# -------------------------------------------------------------
# 🏪 SHOPKEEPER AUTHENTICATION & MULTI-STORE ONBOARDING
# -------------------------------------------------------------
if "logged_in_store" not in st.session_state:
    st.session_state["logged_in_store"] = None

if not st.session_state["logged_in_store"]:
    st.title("📦 SHELF MIND")
    st.subheader("🏪 Shopkeeper Portal / दुकानदार प्रवेश")

    auth_mode = st.radio("Choose Option:", ["🔑 Login to Store", "📝 Register New Shop Account"], horizontal=True)

    if auth_mode == "🔑 Login to Store":
        with st.form("login_form"):
            phone_input = st.text_input("Registered Mobile Number (मोबाईल नंबर)", placeholder="e.g. 9822012345")
            submit_login = st.form_submit_button("Access Store Dashboard", use_container_width=True, type="primary")

            if submit_login:
                profile = db.get_shopkeeper(phone_input)
                if profile:
                    st.session_state["logged_in_store"] = profile
                    st.toast(f"Welcome back, {profile['shop_name']}!")
                    st.rerun()
                else:
                    st.error("No store registered with this mobile number. Please register below.")

    else:
        with st.form("register_form"):
            st.markdown("### 📝 Register Store Account")
            new_shop = st.text_input("Store Name (दुकानाचे नाव)", placeholder="e.g. Patil Super Shoppe")
            new_owner = st.text_input("Owner Name (दुकानदाराचे नाव)", placeholder="e.g. Aniket Patil")
            new_phone = st.text_input("10-Digit Mobile Number (मोबाईल नंबर)", placeholder="e.g. 9822012345")
            new_upi = st.text_input("Store UPI ID for Customer Payments (उदा. yourname@oksbi / 9822012345@ybl)",
                                    placeholder="e.g. 9822012345@ybl")

            submit_reg = st.form_submit_button("Register & Launch Store", use_container_width=True, type="primary")
            if submit_reg:
                if new_shop and new_owner and new_phone and new_upi:
                    success, err = db.register_shopkeeper(new_shop, new_owner, new_phone, new_upi)
                    if success:
                        st.session_state["logged_in_store"] = {
                            "shop_name": new_shop,
                            "owner_name": new_owner,
                            "phone_number": new_phone,
                            "upi_id": new_upi
                        }
                        st.success("Store successfully registered!")
                        st.rerun()
                    else:
                        st.error(err)
                else:
                    st.error("Please fill in all fields including your UPI ID.")

    st.stop()

# -------------------------------------------------------------
# 🎯 ACTIVE STORE DASHBOARD (Logged In)
# -------------------------------------------------------------
current_store = st.session_state["logged_in_store"]
store_phone = current_store["phone_number"]
shop_name = current_store["shop_name"]
shop_upi = current_store["upi_id"]

# Sidebar Profile & Account Settings
st.sidebar.markdown(f"### 🏪 **{shop_name}**")
st.sidebar.caption(f"👤 Owner: {current_store['owner_name']}")
st.sidebar.caption(f"📞 Phone: {store_phone}")
st.sidebar.info(f"💳 Active UPI: `{shop_upi}`")

with st.sidebar.expander("⚙️ Update UPI ID"):
    new_upi_val = st.text_input("New UPI ID", value=shop_upi)
    if st.button("Save New UPI"):
        db.update_shopkeeper_upi(store_phone, new_upi_val)
        st.session_state["logged_in_store"]["upi_id"] = new_upi_val
        st.success("UPI ID updated!")
        st.rerun()

if st.sidebar.button("🚪 Logout Store", use_container_width=True):
    st.session_state["logged_in_store"] = None
    st.session_state["parsed_items"] = None
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

# --- TAB 1: Invoice Vision Ingestion + Editable Grid ---
with tab1:
    st.subheader(t["upload_heading"])
    input_mode = st.radio("Capture Method:", ["📸 Open Phone Camera", "📁 Upload from Gallery"], horizontal=True)
    image_file = st.camera_input(
        "Take photo of wholesale bill") if input_mode == "📸 Open Phone Camera" else st.file_uploader(t["upload_btn"],
                                                                                                     type=["jpg", "png",
                                                                                                           "jpeg"])

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

            # Interactive Editable Table for Human-in-the-Loop Corrections
            df_edit = st.data_editor(
                pd.DataFrame(items),
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "Item Name": st.column_config.TextColumn("Product SKU", required=True),
                    "Quantity": st.column_config.NumberColumn("Qty", min_value=1, step=1, required=True),
                    "Rate (₹)": st.column_config.NumberColumn("Rate (₹)", min_value=0.0, step=0.5, format="₹%.2f",
                                                              required=True)
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

# --- TAB 4: Udhar (Credit) Ledger & Custom NPCI QR / WhatsApp Reminders ---
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
                    clean_phone = c_phone.replace("+91", "").strip()
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
                        st.markdown(f"**👤 {row['customer_name']}** (📞 `{row['customer_phone']}`)")
                        st.markdown(f"💰 **Amount:** ₹{row['amount']:,.2f} | 📅 **Due:** `{row['due_date']}`")
                        if row["items_note"]:
                            st.caption(f"Items: {row['items_note']}")

                    with col_actions:
                        # Construct Standard NPCI UPI URI with this Shopkeeper's actual UPI ID
                        upi_payload = f"upi://pay?pa={shop_upi}&pn={urllib.parse.quote(shop_name)}&am={row['amount']}&cu=INR&tn=Udhar_{row['id']}"

                        # Generate dynamic QR Code
                        qr = qrcode.QRCode(box_size=4, border=1)
                        qr.add_data(upi_payload)
                        qr.make(fit=True)
                        img_qr = qr.make_image(fill_color="black", back_color="white")
                        buf = io.BytesIO()
                        img_qr.save(buf, format="PNG")

                        with st.expander("📲 QR Code"):
                            st.image(buf.getvalue(), caption=f"Pay ₹{row['amount']} to {shop_upi}", width=150)

                        # WhatsApp Reminder Message in the Selected Language
                        if lang_key == "mr":
                            msg = f"नमस्कार {row['customer_name']}जी, {shop_name} दुकानाची ₹{row['amount']} उधारी बाकी आहे (वस्तू: {row['items_note']}). देय तारीख: {row['due_date']}. थेट UPI द्वारे पैसे भरण्यासाठी लिंक: {upi_payload}"
                        elif lang_key == "hi":
                            msg = f"नमस्ते {row['customer_name']}जी, {shop_name} की ₹{row['amount']} उधारी बकाया है (सामान: {row['items_note']}). अंतिम तिथि: {row['due_date']}. UPI भुगतान लिंक: {upi_payload}"
                        else:
                            msg = f"Dear {row['customer_name']}, reminder for pending grocery credit of ₹{row['amount']} at {shop_name}. Due Date: {row['due_date']}. Pay via UPI: {upi_payload}"

                        wa_url = f"https://wa.me/91{row['customer_phone']}?text={urllib.parse.quote(msg)}"
                        st.link_button("📲 WhatsApp", wa_url, use_container_width=True)

                        if st.button(t["mark_paid"], key=f"settle_{row['id']}", use_container_width=True):
                            db.settle_udhar(row["id"])
                            st.toast(f"Payment settled for {row['customer_name']}!")
                            st.rerun()
    else:
        st.info("No pending Udhar records for this store.")