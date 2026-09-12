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

# 1. Mobile App Viewport & Page Setup
logo_path = "logo.png"
page_icon = Image.open(logo_path) if os.path.exists(logo_path) else "🏦"

st.set_page_config(
    page_title="ShelfMind 811",
    page_icon=page_icon,
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. Kotak 811 Native Mobile UI CSS Injection
st.markdown("""
<style>
    /* Viewport & Body constraints */
    .stApp {
        background-color: #F1F4F8 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 5rem !important;
        max-width: 450px !important; /* Locks width to standard mobile screen */
        margin: auto !important;
    }

    /* Top Kotak Profile Bar */
    .kotak-top-nav {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 4px 0 16px 0;
    }
    .profile-pill {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .avatar-circle {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #0B2265;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 16px;
    }
    .store-details {
        display: flex;
        flex-direction: column;
    }
    .store-name-text {
        font-size: 15px;
        font-weight: 700;
        color: #1A202C;
    }
    .crn-text {
        font-size: 11px;
        color: #718096;
        font-weight: 500;
    }

    /* 811 Signature Red Card */
    .kotak-hero-card {
        background: linear-gradient(135deg, #EE1C25 0%, #C4141C 100%);
        border-radius: 20px;
        padding: 20px 22px;
        color: #FFFFFF;
        box-shadow: 0 10px 25px rgba(238, 28, 37, 0.28);
        position: relative;
        margin-bottom: 22px;
        overflow: hidden;
    }
    .hero-card-type {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.8px;
        opacity: 0.9;
        text-transform: uppercase;
    }
    .hero-balance-label {
        font-size: 12px;
        opacity: 0.85;
        margin-top: 14px;
    }
    .hero-balance-amt {
        font-size: 32px;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin-top: 2px;
    }
    .hero-card-footer {
        display: flex;
        justify-content: space-between;
        margin-top: 18px;
        padding-top: 12px;
        border-top: 1px solid rgba(255, 255, 255, 0.2);
        font-size: 12px;
    }

    /* 4-Item Quick Action Row */
    .action-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        text-align: center;
        margin-bottom: 22px;
    }
    .action-btn-card {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 12px 6px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
    }
    .action-icon {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        background-color: #FDE8E9;
        color: #EE1C25;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
    }
    .action-title {
        font-size: 11px;
        font-weight: 600;
        color: #2D3748;
    }

    /* Section Subheaders */
    .kotak-section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        font-size: 14px;
        font-weight: 700;
        color: #0B2265;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* 811 Passbook Activity Item */
    .passbook-item {
        background: #FFFFFF;
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 10px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .pb-left {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .pb-avatar {
        width: 36px;
        height: 36px;
        border-radius: 10px;
        background-color: #EDF2F7;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
    }
    .pb-name {
        font-size: 14px;
        font-weight: 700;
        color: #1A202C;
    }
    .pb-sub {
        font-size: 11px;
        color: #718096;
    }
    .pb-amount {
        font-size: 15px;
        font-weight: 800;
        color: #EE1C25;
    }

    /* Primary Native-Style Red Buttons */
    div.stButton > button:first-child {
        background: #EE1C25 !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
        border: none !important;
        font-weight: 700 !important;
        height: 44px !important;
        box-shadow: 0 4px 12px rgba(238, 28, 37, 0.25) !important;
    }

    /* Segmented Navigation Bar */
    .stRadio [role="radiogroup"] {
        background-color: #E2E8F0;
        padding: 4px;
        border-radius: 12px;
        display: flex;
        gap: 4px;
    }
    .stRadio [role="radiogroup"] label {
        background-color: transparent;
        border-radius: 8px;
        padding: 6px 12px;
        font-weight: 600;
        font-size: 13px;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {background: transparent;}
</style>
""", unsafe_allow_html=True)

# 3. Backend Init & Auth
db.init_db()

query_params = st.query_params
phone_in_url = query_params.get("phone", None)

if "logged_in_store" not in st.session_state or st.session_state["logged_in_store"] is None:
    if phone_in_url:
        cached = db.get_shopkeeper(phone_in_url)
        if cached:
            st.session_state["logged_in_store"] = cached

# Language Bar
lang_col1, lang_col2 = st.columns([2, 1])
with lang_col2:
    lang_choice = st.selectbox("Lang", ["English", "मराठी", "हिंदी"], label_visibility="collapsed")
lang_key = "mr" if "मराठी" in lang_choice else "hi" if "हिंदी" in lang_choice else "en"
t = TRANSLATIONS[lang_key]

# -------------------------------------------------------------
# 🔐 AUTHENTICATION (Kotak 811 Onboarding Screen)
# -------------------------------------------------------------
if not st.session_state.get("logged_in_store"):
    st.markdown("""
        <div style="text-align:center; padding: 24px 0 16px 0;">
            <div style="font-size: 38px; color: #EE1C25; font-weight: 900; letter-spacing: -1px;">811</div>
            <div style="font-size: 18px; font-weight: 800; color: #0B2265; margin-top:-4px;">KIRANA BANKING</div>
            <div style="font-size: 12px; color: #718096; margin-top: 4px;">Zero Maintenance Digital Khata & Stock</div>
        </div>
    """, unsafe_allow_html=True)

    portal_tab = st.radio("Mode", ["🔑 Login", "📝 New Account"], horizontal=True, label_visibility="collapsed")

    if portal_tab == "🔑 Login":
        with st.form("login_form"):
            login_phone = st.text_input("Registered Mobile Number", placeholder="e.g. 9822012345")
            if st.form_submit_button("Proceed Securely", use_container_width=True):
                profile = db.get_shopkeeper(login_phone)
                if profile:
                    st.session_state["logged_in_store"] = profile
                    st.query_params["phone"] = profile["phone_number"]
                    st.rerun()
                else:
                    st.error("Account not registered. Please create an 811 account.")
    else:
        r_shop = st.text_input("Store Name", placeholder="e.g. Anand Super Market")
        r_owner = st.text_input("Owner Full Name", placeholder="e.g. Anand Rao")
        r_phone = st.text_input("Mobile Number", placeholder="e.g. 9822012345")
        r_upi = st.text_input("UPI VPA (for receipts)", placeholder="e.g. 9822012345@kotak")

        if st.button("Generate OTP", use_container_width=True):
            if r_shop and r_owner and r_phone and r_upi:
                otp = sms_service.generate_otp()
                st.session_state["reg_otp"] = otp
                st.session_state["temp_reg"] = {"shop_name": r_shop, "owner_name": r_owner, "phone_number": r_phone, "upi_id": r_upi}
                sms_service.send_sms_otp(r_phone, otp)
                st.success("Verification code sent.")
            else:
                st.error("Fill all details.")

        if st.session_state.get("reg_otp"):
            with st.form("otp_box"):
                code = st.text_input("4-Digit MPIN / Code", max_chars=4, placeholder="****")
                if st.form_submit_button("Verify & Activate 811 Store", use_container_width=True):
                    if code.strip() == st.session_state["reg_otp"]:
                        d = st.session_state["temp_reg"]
                        db.register_shopkeeper(d["shop_name"], d["owner_name"], d["phone_number"], d["upi_id"])
                        st.session_state["logged_in_store"] = d
                        st.query_params["phone"] = d["phone_number"]
                        st.session_state["reg_otp"] = None
                        st.rerun()
                    else:
                        st.error("Invalid Code.")
    st.stop()

# -------------------------------------------------------------
# 📱 KOTAK 811 ACTIVE MOBILE DASHBOARD
# -------------------------------------------------------------
store = st.session_state["logged_in_store"]
store_phone = store["phone_number"]
shop_name = store["shop_name"]
owner_name = store["owner_name"]
shop_upi = store["upi_id"]

skus, capital, dead = db.get_kpi_metrics(store_phone)
total_udhar = db.get_total_udhar_pending(store_phone)

# 1. Native Mobile Top Bar
first_char = owner_name[0].upper() if owner_name else "S"
st.markdown(f"""
    <div class="kotak-top-nav">
        <div class="profile-pill">
            <div class="avatar-circle">{first_char}</div>
            <div class="store-details">
                <span class="store-name-text">{shop_name}</span>
                <span class="crn-text">CRN: {store_phone[-5:]} · UPI: {shop_upi}</span>
            </div>
        </div>
        <div style="font-size: 20px;">🔔</div>
    </div>
""", unsafe_allow_html=True)

# 2. Kotak 811 Red Digital Debit / Passbook Card
st.markdown(f"""
    <div class="kotak-hero-card">
        <div class="hero-card-type">
            <span>811 Kirana Current</span>
            <span style="font-size:18px; font-weight:900;">kotak</span>
        </div>
        <div class="hero-balance-label">Total Outstanding Udhar (उधारी)</div>
        <div class="hero-balance-amt">₹{total_udhar:,.2f}</div>
        <div class="hero-card-footer">
            <span>Capital: <b>₹{capital:,.0f}</b></span>
            <span>Active SKUs: <b>{skus}</b></span>
        </div>
    </div>
""", unsafe_allow_html=True)

# 3. Segmented Navigation View
active_section = st.radio(
    "Nav",
    ["🏠 Home", "📸 Scan Bill", "📦 Stock", "👥 Udhar Khata"],
    horizontal=True,
    label_visibility="collapsed"
)

# -------------------------------------------------------------
# 🏠 VIEW: 811 HOME (Quick Actions & Passbook Feed)
# -------------------------------------------------------------
if active_section == "🏠 Home":
    st.markdown("""
        <div class="action-grid">
            <div class="action-btn-card">
                <div class="action-icon">📸</div>
                <div class="action-title">Scan Bill</div>
            </div>
            <div class="action-btn-card">
                <div class="action-icon">➕</div>
                <div class="action-title">Add SKU</div>
            </div>
            <div class="action-btn-card">
                <div class="action-icon">💸</div>
                <div class="action-title">Add Due</div>
            </div>
            <div class="action-btn-card">
                <div class="action-icon">📲</div>
                <div class="action-title">My QR</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Passbook: Recent Udhar Activity
    st.markdown('<div class="kotak-section-header"><span>Recent Udhar Ledger</span><span style="color:#EE1C25; font-size:12px;">View All</span></div>', unsafe_allow_html=True)
    
    df_u = db.get_udhar_records(store_phone)
    if not df_u.empty:
        pending = df_u[df_u["status"] != "Paid"].head(5)
        for _, r in pending.iterrows():
            st.markdown(f"""
                <div class="passbook-item">
                    <div class="pb-left">
                        <div class="pb-avatar">👤</div>
                        <div>
                            <div class="pb-name">{r['customer_name']}</div>
                            <div class="pb-sub">Due: {r['due_date']} · {r['items_note'] or 'Store Credit'}</div>
                        </div>
                    </div>
                    <div class="pb-amount">-₹{r['amount']:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No active credit accounts.")

# -------------------------------------------------------------
# 📸 VIEW: SCAN BILL (Vision AI OCR)
# -------------------------------------------------------------
elif active_section == "📸 Scan Bill":
    st.markdown("##### 📸 Vision Invoice OCR")
    bill_img = st.camera_input("Snap distributor receipt")
    if bill_img:
        with st.spinner("AI parsing line items..."):
            raw = extract_invoice_data_with_ai(bill_img.getvalue(), mime_type="image/jpeg")
            items = [{"Item Name": str(i.get("Item Name", "")), "Quantity": int(i.get("Quantity", 1)), "Rate (₹)": float(i.get("Rate (₹)", i.get("Rate", 0.0)))} for i in raw]
            
            df_edit = st.data_editor(pd.DataFrame(items), num_rows="dynamic", use_container_width=True)
            if st.button("Confirm & Add to 811 Ledger", use_container_width=True):
                db.add_or_update_stock(store_phone, df_edit.to_dict(orient="records"))
                st.toast("Stock ledger synchronized!")
                st.rerun()

# -------------------------------------------------------------
# 📦 VIEW: STOCK / INVENTORY
# -------------------------------------------------------------
elif active_section == "📦 Stock":
    st.markdown("##### 📦 Inventory Catalog")
    with st.expander("➕ Add Single Item"):
        with st.form("manual_sku"):
            n = st.text_input("Product SKU", placeholder="e.g. Tata Salt 1kg")
            q = st.number_input("Units", min_value=1, value=10)
            r = st.number_input("Wholesale Rate (₹)", min_value=1.0, value=22.0)
            if st.form_submit_button("Add to Stock", use_container_width=True):
                db.add_or_update_stock(store_phone, [{"Item Name": n, "Quantity": q, "Rate (₹)": r}])
                st.rerun()

    df_inv = db.get_inventory_dataframe(store_phone)
    if not df_inv.empty:
        st.dataframe(df_inv, use_container_width=True)
    else:
        st.info("No items in inventory.")

# -------------------------------------------------------------
# 👥 VIEW: UDHAR KHATA & PAYMENTS
# -------------------------------------------------------------
elif active_section == "👥 Udhar Khata":
    st.markdown("##### 👥 Credit Accounts")
    with st.expander("➕ Record New Customer Credit"):
        with st.form("add_udhar_k"):
            cn = st.text_input("Customer Name")
            cp = st.text_input("10-Digit Mobile")
            ca = st.number_input("Amount (₹)", min_value=1.0, value=100.0)
            ci = st.text_input("Items description")
            cd = st.date_input("Settlement Due Date", min_value=date.today())
            if st.form_submit_button("Record Khata Due", use_container_width=True):
                db.add_udhar_entry(store_phone, cn, cp, ca, ci, cd)
                st.rerun()

    df_u = db.get_udhar_records(store_phone)
    if not df_u.empty:
        for _, row in df_u[df_u["status"] != "Paid"].iterrows():
            st.markdown(f"""
                <div class="passbook-item">
                    <div>
                        <div class="pb-name">👤 {row['customer_name']}</div>
                        <div class="pb-sub">📞 {row['customer_phone']} · 📅 Due: {row['due_date']}</div>
                        <div style="font-size:12px; margin-top:4px;">📦 {row['items_note']}</div>
                    </div>
                    <div class="pb-amount">₹{row['amount']:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)

            c_wa, c_pay = st.columns([1.5, 1])
            with c_wa:
                wa_msg = f"Hello {row['customer_name']}, your pending dues at {shop_name} are ₹{row['amount']}. Pay via UPI: upi://pay?pa={shop_upi}&pn={urllib.parse.quote(shop_name)}&am={row['amount']}&cu=INR"
                st.link_button("📲 WhatsApp Notice", f"https://wa.me/91{row['customer_phone']}?text={urllib.parse.quote(wa_msg)}", use_container_width=True)
            with c_pay:
                if st.button("Settle", key=f"p_{row['id']}", use_container_width=True):
                    db.settle_udhar(row['id'])
                    st.rerun()

# -------------------------------------------------------------
# ⚙️ LOGOUT & PROFILE
# -------------------------------------------------------------
with st.sidebar:
    st.markdown(f"**Logged in as {owner_name}**")
    if st.button("Logout of 811 Session", use_container_width=True):
        st.session_state["logged_in_store"] = None
        st.query_params.clear()
        st.rerun()
