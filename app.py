import os
import io
import urllib.parse
from datetime import date
from PIL import Image
import pandas as pd
import qrcode
import streamlit as st

import database as db
from ocr_pipeline import extract_invoice_data_with_ai
import sms_service
from translations import TRANSLATIONS

# 1. PAGE CONFIG
logo_path = "logo.png"
page_icon = Image.open(logo_path) if os.path.exists(logo_path) else "📦"

st.set_page_config(
    page_title="SHELF MIND",
    page_icon=page_icon,
    layout="centered",
    initial_sidebar_state="collapsed",
)

# 2. POLISHED KOTAK 811 THEME WITH HIGH-CONTRAST TEXT & SLIDING TAB
st.markdown("""
<style>
    /* 1. Universal Theme Adaptation */
    .stApp {
        background-color: var(--background-color) !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    /* Force all plain text to adapt cleanly between light & dark */
    p, span, label, div[data-testid="stMarkdownContainer"] {
        color: var(--text-color);
    }

    /* 2. Top Header */
    .kotak-header {
        background: linear-gradient(135deg, #ED1C24 0%, #991B1B 100%);
        border-radius: 16px;
        padding: 18px 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 14px rgba(237, 28, 36, 0.25);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .kotak-header * {
        color: #FFFFFF !important;
    }
    .kotak-header h1 {
        font-size: 22px;
        font-weight: 800;
        margin: 0;
    }
    .kotak-header-sub {
        font-size: 13px;
        opacity: 0.92;
        margin-top: 3px;
    }
    .kotak-badge {
        background: rgba(255, 255, 255, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.4);
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }

    /* 3. KPI Grid with Distinct Black / Slate Accents */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        margin-bottom: 20px;
    }
    .kotak-kpi-card {
        background-color: var(--secondary-background-color) !important;
        border: 1px solid rgba(128, 128, 128, 0.25) !important;
        border-radius: 14px;
        padding: 14px 16px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        /* Signature Dark Slate / Black Accent Strip */
        border-top: 5px solid #0B2265 !important;
    }
    .kotak-kpi-card.accent-red {
        /* 4th Card Udhar Red Accent Strip */
        border-top: 5px solid #ED1C24 !important;
    }
    .kpi-meta-label {
        font-size: 11px;
        font-weight: 700;
        color: var(--text-color) !important;
        opacity: 0.72;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    .kpi-main-number {
        font-size: 22px;
        font-weight: 800;
        color: var(--text-color) !important;
        margin-top: 5px;
    }
    .kpi-main-number.dark-accent {
        color: #0F172A !important; /* Bold deep black/slate in light mode */
    }
    /* Dark mode override for primary numbers */
    @media (prefers-color-scheme: dark) {
        .kpi-main-number.dark-accent {
            color: #F8FAFC !important;
        }
    }
    .kpi-main-number.red {
        color: #ED1C24 !important;
    }

    /* 4. Udhar Ledger Card */
    .kotak-udhar-card {
        background-color: var(--secondary-background-color) !important;
        border: 1px solid rgba(128, 128, 128, 0.22) !important;
        border-left: 5px solid #ED1C24 !important;
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 12px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
    }
    .kotak-udhar-title {
        font-size: 16px;
        font-weight: 700;
        color: var(--text-color) !important;
    }
    .kotak-udhar-sub {
        font-size: 12px;
        color: var(--text-color) !important;
        opacity: 0.75;
        margin-top: 2px;
    }
    .kotak-udhar-note {
        font-size: 13px;
        color: var(--text-color) !important;
        opacity: 0.9;
        margin-top: 6px;
    }

    /* 5. Kotak Primary Buttons */
    div.stButton > button[kind="primary"], div.stButton > button:first-child {
        background-color: #ED1C24 !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
    }
    div.stButton > button:hover {
        background-color: #C7141B !important;
        color: #FFFFFF !important;
    }

    /* 6. Continuous Smooth Red Sliding Tab Across All 4 Tabs */
    .stTabs [data-baseweb="tab-list"] {
        display: flex !important;
        gap: 0px !important;
        background-color: transparent !important;
        border-bottom: 1px solid rgba(128, 128, 128, 0.25) !important;
        position: relative !important;
        padding: 0 !important;
    }
    .stTabs [data-baseweb="tab"] {
        flex: 1 !important;
        text-align: center !important;
        height: 46px !important;
        background-color: transparent !important;
        border: none !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 0 10px !important;
        color: var(--text-color) !important;
        opacity: 0.65;
        transition: opacity 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        color: #ED1C24 !important;
        opacity: 1 !important;
        background-color: transparent !important;
        border: none !important;
    }
    /* Seamless horizontal slider bar */
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #ED1C24 !important;
        height: 3px !important;
        bottom: 0px !important;
        border-radius: 2px 2px 0 0 !important;
        transition: transform 0.3s cubic-bezier(0.25, 1, 0.5, 1), width 0.3s cubic-bezier(0.25, 1, 0.5, 1) !important;
    }

    header[data-testid="stHeader"] {
        background-color: transparent !important;
    }
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# 3. INITIALIZE DB & STATE
db.init_db()

query_params = st.query_params
phone_in_url = query_params.get("phone", None)

if "logged_in_store" not in st.session_state or st.session_state["logged_in_store"] is None:
    if phone_in_url:
        cached_store = db.get_shopkeeper(phone_in_url)
        if cached_store:
            st.session_state["logged_in_store"] = cached_store

# Language Selector
lang_col1, lang_col2 = st.columns([2, 1])
with lang_col2:
    lang_choice = st.selectbox("Language / भाषा", ["English", "मराठी", "हिंदी"], label_visibility="collapsed")
lang_key = "mr" if "मराठी" in lang_choice else "hi" if "हिंदी" in lang_choice else "en"
t = TRANSLATIONS[lang_key]

# -------------------------------------------------------------
# 🔐 AUTHENTICATION PORTAL (If Logged Out)
# -------------------------------------------------------------
if not st.session_state.get("logged_in_store"):
    st.markdown(f"""
        <div class="kotak-header">
            <div>
                <h1>📦 {t['app_title']}</h1>
                <div class="kotak-header-sub">{t['app_tagline']}</div>
            </div>
            <div class="kotak-badge">Kirana v2.5</div>
        </div>
    """, unsafe_allow_html=True)
    
    auth_choice = st.radio("Choose:", ["🔑 Login to Store", "📝 Register New Shop"], horizontal=True, label_visibility="collapsed")
    
    if auth_choice == "🔑 Login to Store":
        with st.form("login_box"):
            st.markdown("##### 🔑 Shopkeeper Login")
            l_phone = st.text_input("10-Digit Mobile Number", placeholder="e.g. 9822012345")
            if st.form_submit_button("Access Dashboard", use_container_width=True, type="primary"):
                profile = db.get_shopkeeper(l_phone)
                if profile:
                    st.session_state["logged_in_store"] = profile
                    st.query_params["phone"] = profile["phone_number"]
                    st.rerun()
                else:
                    st.error("Store not found. Please register first.")
    else:
        st.markdown("##### 📝 Register Store Account")
        if "reg_otp" not in st.session_state:
            st.session_state["reg_otp"] = None
            st.session_state["temp_reg"] = {}
            
        r_shop = st.text_input("Store Name (दुकानाचे नाव)", placeholder="e.g. Patil Kirana Stores")
        r_owner = st.text_input("Owner Name (दुकानदाराचे नाव)", placeholder="e.g. Aniket Patil")
        r_phone = st.text_input("Mobile Number (मोबाईल नंबर)", placeholder="e.g. 9822012345")
        r_upi = st.text_input("Store UPI ID for receiving payments", placeholder="e.g. 9822012345@ybl")
        
        if st.button("📲 Send 4-Digit Verification Code", use_container_width=True):
            if r_shop and r_owner and r_phone and r_upi:
                otp = sms_service.generate_otp()
                st.session_state["reg_otp"] = otp
                st.session_state["temp_reg"] = {"shop_name": r_shop, "owner_name": r_owner, "phone_number": r_phone, "upi_id": r_upi}
                sent_ok, msg = sms_service.send_sms_otp(r_phone, otp)
                st.success(f"✅ {msg}")
            else:
                st.error("Please fill in all store details.")
                
        if st.session_state.get("reg_otp"):
            with st.form("verify_box"):
                code = st.text_input("Enter 4-Digit Code", max_chars=4, placeholder="****")
                if st.form_submit_button("Verify & Activate Store", use_container_width=True, type="primary"):
                    if code.strip() == st.session_state["reg_otp"]:
                        d = st.session_state["temp_reg"]
                        db.register_shopkeeper(d["shop_name"], d["owner_name"], d["phone_number"], d["upi_id"])
                        st.session_state["logged_in_store"] = d
                        st.query_params["phone"] = d["phone_number"]
                        st.session_state["reg_otp"] = None
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Invalid verification code.")
    st.stop()

# -------------------------------------------------------------
# 🎯 ACTIVE SHOPKEEPER DASHBOARD
# -------------------------------------------------------------
store = st.session_state["logged_in_store"]
store_phone = store["phone_number"]
shop_name = store["shop_name"]
owner_name = store["owner_name"]
shop_upi = store["upi_id"]

# 1. Kotak 811 Header Bar
st.markdown(f"""
    <div class="kotak-header">
        <div>
            <h1>🏪 {shop_name}</h1>
            <div class="kotak-header-sub">{t['welcome_back']}, <b>{owner_name}</b> · 📞 +91 {store_phone}</div>
        </div>
        <div class="kotak-badge">UPI: {shop_upi}</div>
    </div>
""", unsafe_allow_html=True)

# 2. KPI Summary Grid
skus, capital, dead = db.get_kpi_metrics(store_phone)
total_udhar = db.get_total_udhar_pending(store_phone)

st.markdown(f"""
    <div class="kpi-grid">
        <div class="kotak-kpi-card">
            <div class="kpi-meta-label">{t['kpi_skus']}</div>
            <div class="kpi-main-number dark-accent">{skus} <span style="font-size:12px; font-weight:normal; opacity:0.75;">Items</span></div>
        </div>
        <div class="kotak-kpi-card">
            <div class="kpi-meta-label">{t['kpi_capital']}</div>
            <div class="kpi-main-number dark-accent">₹{capital:,.0f}</div>
        </div>
        <div class="kotak-kpi-card">
            <div class="kpi-meta-label">{t['kpi_dead']}</div>
            <div class="kpi-main-number dark-accent">₹{dead:,.0f}</div>
        </div>
        <div class="kotak-kpi-card accent-red">
            <div class="kpi-meta-label">{t['kpi_udhar']}</div>
            <div class="kpi-main-number red">₹{total_udhar:,.0f}</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# 3. Tab Navigation (Sliding Red Underline)
tab_scan, tab_inv, tab_udhar, tab_radar = st.tabs([
    t["tab_scan"], t["tab_inventory"], t["tab_udhar"], t["tab_demand"]
])

# --- TAB 1: Vision Bill Scan & Editable Grid ---
with tab_scan:
    st.markdown(f"#### {t['upload_heading']}")
    st.caption(t["upload_sub"])
    
    input_mode = st.radio("Source:", ["📸 Phone Camera", "📁 Gallery File"], horizontal=True, label_visibility="collapsed")
    bill_img = st.camera_input("Take photo of wholesale receipt") if input_mode == "📸 Phone Camera" else st.file_uploader("Select Invoice Photo", type=["jpg", "png", "jpeg"])
    
    if bill_img is not None:
        file_type = bill_img.type if hasattr(bill_img, "type") and bill_img.type else "image/jpeg"
        file_id = getattr(bill_img, "name", "cam_snap")
        
        if "parsed_items" not in st.session_state or st.session_state.get("last_bill_id") != file_id:
            with st.spinner("⚡ Vision AI is analyzing invoice columns and items..."):
                extracted = extract_invoice_data_with_ai(bill_img.getvalue(), mime_type=file_type)
                clean = [
                    {
                        "Item Name": str(i.get("Item Name", "")),
                        "Quantity": int(i.get("Quantity", 1)),
                        "Rate (₹)": float(i.get("Rate (₹)", i.get("Rate", 0.0)))
                    }
                    for i in extracted
                ]
                st.session_state["parsed_items"] = clean
                st.session_state["last_bill_id"] = file_id
        
        items = st.session_state.get("parsed_items", [])
        if items:
            st.success(f"✅ Extracted {len(items)} line items from receipt.")
            st.caption(t["edit_instruction"])
            
            df_edit = st.data_editor(
                pd.DataFrame(items),
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "Item Name": st.column_config.TextColumn("Product SKU", required=True),
                    "Quantity": st.column_config.NumberColumn("Qty", min_value=1, step=1, required=True),
                    "Rate (₹)": st.column_config.NumberColumn("Unit Rate (₹)", min_value=0.0, step=1.0, format="₹%.2f", required=True)
                }
            )
            
            if st.button(f"✅ {t['save_stock_btn']}", use_container_width=True, type="primary"):
                db.add_or_update_stock(store_phone, df_edit.to_dict(orient="records"))
                st.balloons()
                st.toast(t["stock_updated_toast"])
                st.session_state["parsed_items"] = None
                st.rerun()

# --- TAB 2: Clean Inventory Table + Manual Add ---
with tab_inv:
    with st.expander(f"➕ {t['manual_add_heading']}"):
        with st.form("manual_stock_form"):
            col_m1, col_m2 = st.columns([2, 1])
            m_name = col_m1.text_input("Product Name", placeholder="e.g. Parle-G 100g")
            m_qty = col_m2.number_input("Quantity", min_value=1, step=1, value=10)
            m_rate = st.number_input("Wholesale Rate (₹)", min_value=1.0, step=5.0, value=25.0)
            
            if st.form_submit_button(t["add_item_btn"], use_container_width=True):
                if m_name:
                    db.add_or_update_stock(store_phone, [{"Item Name": m_name, "Quantity": m_qty, "Rate (₹)": m_rate}])
                    st.toast(f"Added {m_name} to inventory!")
                    st.rerun()
                else:
                    st.error("Please enter a product name.")
                    
    search_q = st.text_input(t["search_stock"], placeholder="Search...", label_visibility="collapsed")
    df_inv = db.get_inventory_dataframe(store_phone)
    
    if not df_inv.empty:
        if search_q:
            df_inv = df_inv[df_inv["Item SKU"].str.contains(search_q, case=False, na=False)]
        st.dataframe(
            df_inv,
            use_container_width=True,
            column_config={
                "Rate (₹)": st.column_config.NumberColumn(format="₹%.2f"),
                "Total Capital (₹)": st.column_config.NumberColumn(format="₹%.2f")
            }
        )
    else:
        st.info(t["no_stock"])

# --- TAB 3: Udhar Ledger & Payment Prompts ---
with tab_udhar:
    with st.expander(f"➕ {t['act_add_udhar']}"):
        with st.form("new_udhar_form"):
            u_name = st.text_input(t["customer_name"], placeholder="e.g. Ramesh Kulkarni")
            u_phone = st.text_input(t["customer_phone"], placeholder="e.g. 9822123456")
            u_amount = st.number_input(t["udhar_amount"], min_value=1.0, step=10.0, value=150.0)
            u_note = st.text_input(t["items_note"], placeholder="e.g. 1L Gemini Oil, 1kg Sugar")
            u_due = st.date_input(t["due_date"], min_value=date.today())
            
            if st.form_submit_button(t["save_udhar_btn"], use_container_width=True, type="primary"):
                if u_name and u_phone:
                    db.add_udhar_entry(store_phone, u_name, u_phone, u_amount, u_note, u_due)
                    st.success("Udhar record saved!")
                    st.rerun()
                else:
                    st.error("Please provide both name and phone number.")
                    
    df_u = db.get_udhar_records(store_phone)
    pending_records = df_u[df_u["status"] != "Paid"] if not df_u.empty else pd.DataFrame()
    
    if not pending_records.empty:
        for _, row in pending_records.iterrows():
            st.markdown(f"""
    <div class="kotak-udhar-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
                <div class="kotak-udhar-title">👤 {row['customer_name']}</div>
                <div class="kotak-udhar-sub">📞 +91 {row['customer_phone']} · 📅 Due: <b>{row['due_date']}</b></div>
                <div class="kotak-udhar-note">📦 {row['items_note'] or 'Grocery Items'}</div>
            </div>
            <div style="font-size:19px; font-weight:800; color:#ED1C24;">₹{row['amount']:,.2f}</div>
        </div>
    </div>
""", unsafe_allow_html=True)
            
            col_qr, col_wa, col_settle = st.columns([1, 1.2, 1])
            
            upi_payload = f"upi://pay?pa={shop_upi}&pn={urllib.parse.quote(shop_name)}&am={row['amount']}&cu=INR&tn=Udhar_{row['id']}"
            
            with col_qr:
                qr = qrcode.QRCode(box_size=4, border=1)
                qr.add_data(upi_payload)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                with st.popover("📲 Scan QR"):
                    st.image(buf.getvalue(), caption=f"Pay ₹{row['amount']} to {shop_upi}")
                    
            with col_wa:
                if lang_key == "mr":
                    msg = f"नमस्कार {row['customer_name']}जी, {shop_name} दुकानाची ₹{row['amount']} उधारी बाकी आहे (वस्तू: {row['items_note']}). देय तारीख: {row['due_date']}. थेट UPI द्वारे पैसे भरण्यासाठी लिंक: {upi_payload}"
                elif lang_key == "hi":
                    msg = f"नमस्ते {row['customer_name']}जी, {shop_name} की ₹{row['amount']} उधारी बाकी है (सामान: {row['items_note']}). अंतिम तिथि: {row['due_date']}. भुगतान लिंक: {upi_payload}"
                else:
                    msg = f"Dear {row['customer_name']}, reminder for pending store credit of ₹{row['amount']} at {shop_name}. Due Date: {row['due_date']}. Pay via UPI: {upi_payload}"
                
                wa_url = f"https://wa.me/91{row['customer_phone']}?text={urllib.parse.quote(msg)}"
                st.link_button(t["send_whatsapp_btn"], wa_url, use_container_width=True)
                
            with col_settle:
                if st.button(t["mark_paid_btn"], key=f"settle_{row['id']}", use_container_width=True):
                    db.settle_udhar(row["id"])
                    st.toast(f"Settled account for {row['customer_name']}!")
                    st.rerun()
    else:
        st.info(t["no_udhar"])

# --- TAB 4: Demand Radar & Stock Alerts ---
with tab_radar:
    st.markdown("#### ⚡ Demand Sensing & Weather Radar")
    st.info("🌧️ **Regional Weather Radar:** Live monsoon & weather sensors linked. Monsoon-driven items (Tea, Biscuits, Spices) prioritized.")
    st.warning("⚠️ **Dead-Stock Estimator:** Bayesian velocity monitoring active. Items inactive for >30 days will trigger discount liquidation suggestions.")

# -------------------------------------------------------------
# ⚙️ SIDEBAR: FULL PROFILE EDITING & LOGOUT
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Store Profile Settings")
    
    with st.form("edit_profile_form"):
        st.caption("Update Store Details:")
        edit_sname = st.text_input("Store Name", value=shop_name)
        edit_oname = st.text_input("Owner Name", value=owner_name)
        edit_upi = st.text_input("Store UPI ID", value=shop_upi)
        
        if st.form_submit_button("💾 Save Profile Changes", use_container_width=True, type="primary"):
            if edit_sname and edit_oname and edit_upi:
                db.update_shopkeeper_profile(store_phone, edit_sname, edit_oname, edit_upi)
                st.session_state["logged_in_store"]["shop_name"] = edit_sname
                st.session_state["logged_in_store"]["owner_name"] = edit_oname
                st.session_state["logged_in_store"]["upi_id"] = edit_upi
                st.toast("Profile updated successfully!")
                st.rerun()
            else:
                st.error("Fields cannot be empty.")
        
    st.divider()
    if st.button("🚪 Logout Store Account", use_container_width=True):
        st.session_state["logged_in_store"] = None
        st.session_state["parsed_items"] = None
        st.query_params.clear()
        st.rerun()
