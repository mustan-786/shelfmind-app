import io
import os
import urllib.parse
from datetime import date

import pandas as pd
import qrcode
import streamlit as st
from PIL import Image

import database as db
import sms_service
from ocr_pipeline import extract_invoice_data_with_ai
from translations import TRANSLATIONS

# -----------------------------------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------------------------------
LOGO_PATH = "logo.png"
page_icon = Image.open(LOGO_PATH) if os.path.exists(LOGO_PATH) else "📦"
st.set_page_config(
    page_title="SHELF MIND",
    page_icon=page_icon,
    layout="centered",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# VISUAL SYSTEM — mobile-first, professional Kirana app
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --sm-green: #176B4D;
        --sm-green-dark: #0E4D37;
        --sm-green-soft: #EAF5F0;
        --sm-cream: #F7F7F2;
        --sm-border: #E5E7EB;
        --sm-text: #18221D;
        --sm-muted: #68736D;
        --sm-red: #B42318;
        --sm-amber: #B54708;
    }

    .stApp {
        background: var(--sm-cream);
    }

    [data-testid="stHeader"] {
        background: rgba(247,247,242,0.94);
    }

    .block-container {
        max-width: 980px;
        padding: 1rem 1rem 5rem 1rem;
    }

    .sm-brand {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 4px 0 16px 0;
    }
    .sm-brand img {
        width: 48px;
        height: 48px;
        border-radius: 14px;
        object-fit: cover;
    }
    .sm-brand-title {
        font-size: 1.55rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: var(--sm-text);
        line-height: 1.05;
    }
    .sm-brand-subtitle {
        color: var(--sm-muted);
        font-size: 0.78rem;
        margin-top: 4px;
    }

    .sm-welcome {
        background: white;
        border: 1px solid var(--sm-border);
        border-radius: 20px;
        padding: 20px;
        margin: 4px 0 16px 0;
        box-shadow: 0 3px 14px rgba(16,24,40,0.04);
    }
    .sm-eyebrow {
        color: var(--sm-green);
        font-size: 0.76rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: .08em;
    }
    .sm-welcome h2 {
        margin: 5px 0 3px 0;
        color: var(--sm-text);
        font-size: 1.45rem;
    }
    .sm-welcome p {
        margin: 0;
        color: var(--sm-muted);
        font-size: .88rem;
    }

    .sm-section-title {
        color: var(--sm-text);
        font-size: 1.08rem;
        font-weight: 800;
        margin: 20px 0 10px 0;
    }

    .sm-card {
        background: white;
        border: 1px solid var(--sm-border);
        border-radius: 18px;
        padding: 16px;
        min-height: 105px;
        box-shadow: 0 3px 14px rgba(16,24,40,0.035);
    }
    .sm-card-label {
        color: var(--sm-muted);
        font-size: .76rem;
        font-weight: 700;
    }
    .sm-card-value {
        color: var(--sm-text);
        font-size: 1.38rem;
        font-weight: 850;
        margin-top: 6px;
    }
    .sm-card-icon {
        font-size: 1.1rem;
        margin-bottom: 5px;
    }

    .sm-alert {
        border-radius: 16px;
        padding: 14px 16px;
        background: white;
        border: 1px solid var(--sm-border);
        margin: 8px 0;
    }
    .sm-alert strong { color: var(--sm-text); }
    .sm-alert span { color: var(--sm-muted); font-size: .84rem; }

    .sm-footer {
        text-align: center;
        color: #8A938E;
        font-size: .72rem;
        padding-top: 28px;
    }

    div[data-testid="stTabs"] button {
        font-weight: 750;
        font-size: .82rem;
    }

    div.stButton > button, div.stLinkButton > a, button[kind="primary"] {
        border-radius: 12px !important;
        min-height: 44px;
        font-weight: 750 !important;
    }

    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid var(--sm-border);
        border-radius: 16px;
        padding: 12px 14px;
    }

    @media (max-width: 640px) {
        .block-container { padding: .75rem .75rem 4rem .75rem; }
        .sm-card { min-height: 92px; padding: 13px; }
        .sm-card-value { font-size: 1.2rem; }
        div[data-testid="stTabs"] button { font-size: .72rem; padding-left: 5px; padding-right: 5px; }
        .sm-welcome { padding: 17px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Manifest/meta hints retained for mobile browsers where supported.
st.markdown(
    """
    <link rel="manifest" href="manifest.json">
    <link rel="apple-touch-icon" href="logo.png">
    <meta name="apple-mobile-web-app-title" content="SHELF MIND">
    <meta name="application-name" content="SHELF MIND">
    <meta name="mobile-web-app-capable" content="yes">
    """,
    unsafe_allow_html=True,
)


def brand_header():
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            logo_b64 = __import__("base64").b64encode(f.read()).decode("utf-8")
        src = f"data:image/png;base64,{logo_b64}"
        st.markdown(
            f'''<div class="sm-brand"><img src="{src}"><div><div class="sm-brand-title">SHELF MIND</div><div class="sm-brand-subtitle">Smart tools for everyday kirana business</div></div></div>''',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="sm-brand"><div><div class="sm-brand-title">📦 SHELF MIND</div><div class="sm-brand-subtitle">Smart tools for everyday kirana business</div></div></div>',
            unsafe_allow_html=True,
        )


brand_header()
db.init_db()

# -----------------------------------------------------------------------------
# LANGUAGE
# -----------------------------------------------------------------------------
lang_choice = st.selectbox(
    "🌐 Language / भाषा / भाषा",
    ["English", "मराठी (Marathi)", "हिंदी (Hindi)"],
    index=0,
)
lang_key = "mr" if "Marathi" in lang_choice else "hi" if "Hindi" in lang_choice else "en"
t = TRANSLATIONS[lang_key]

# -----------------------------------------------------------------------------
# SESSION / PERSISTENT LOGIN
# -----------------------------------------------------------------------------
phone_in_url = st.query_params.get("phone", None)
if "logged_in_store" not in st.session_state or st.session_state["logged_in_store"] is None:
    if phone_in_url:
        cached_store = db.get_shopkeeper(phone_in_url)
        if cached_store:
            st.session_state["logged_in_store"] = cached_store

# -----------------------------------------------------------------------------
# AUTHENTICATION
# -----------------------------------------------------------------------------
if not st.session_state.get("logged_in_store"):
    st.markdown(
        '<div class="sm-welcome"><div class="sm-eyebrow">Kirana Business App</div><h2>Run your shop, simply.</h2><p>Scan bills, manage stock and track customer credit from one place.</p></div>',
        unsafe_allow_html=True,
    )

    auth_mode = st.radio(
        "",
        ["🔑 Login with Mobile", "📝 Register New Shop"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if auth_mode == "🔑 Login with Mobile":
        with st.container(border=True):
            st.subheader("Welcome back")
            st.caption("Enter the mobile number registered with your shop.")
            with st.form("login_form"):
                phone_input = st.text_input(
                    "10-Digit Mobile Number",
                    placeholder="e.g. 9822012345",
                )
                submit_login = st.form_submit_button(
                    "Access Store Dashboard",
                    use_container_width=True,
                    type="primary",
                )
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
        with st.container(border=True):
            st.subheader("Register your shop")
            st.caption("Create your store profile and verify the mobile number.")
            if "reg_otp" not in st.session_state:
                st.session_state["reg_otp"] = None
                st.session_state["temp_reg_data"] = {}

            new_shop = st.text_input("Store Name", placeholder="e.g. Patil Super Shoppe")
            new_owner = st.text_input("Owner Name", placeholder="e.g. Aniket Patil")
            new_phone = st.text_input("10-Digit Mobile Number", placeholder="e.g. 9822012345")
            new_upi = st.text_input("Store UPI ID", placeholder="e.g. 9822012345@ybl")

            if st.button("📲 Send 4-Digit OTP", use_container_width=True):
                if new_shop and new_owner and new_phone and new_upi:
                    generated_otp = sms_service.generate_otp()
                    st.session_state["reg_otp"] = generated_otp
                    st.session_state["temp_reg_data"] = {
                        "shop_name": new_shop,
                        "owner_name": new_owner,
                        "phone_number": new_phone,
                        "upi_id": new_upi,
                    }
                    sent_ok, msg = sms_service.send_sms_otp(new_phone, generated_otp)
                    if sent_ok:
                        st.success(f"✅ {msg}")
                    else:
                        st.warning(f"⚠️ {msg}")
                else:
                    st.error("Please fill in all shop details before requesting OTP.")

            if st.session_state.get("reg_otp"):
                st.divider()
                with st.form("otp_verification_form"):
                    entered_otp = st.text_input("Enter 4-Digit OTP", max_chars=4, placeholder="••••")
                    verify_btn = st.form_submit_button(
                        "Verify OTP & Create Store",
                        use_container_width=True,
                        type="primary",
                    )
                    if verify_btn:
                        if entered_otp.strip() == st.session_state["reg_otp"]:
                            d = st.session_state["temp_reg_data"]
                            success, err = db.register_shopkeeper(
                                d["shop_name"], d["owner_name"], d["phone_number"], d["upi_id"]
                            )
                            if success:
                                st.session_state["logged_in_store"] = d
                                st.query_params["phone"] = d["phone_number"]
                                st.session_state["reg_otp"] = None
                                st.session_state["temp_reg_data"] = {}
                                st.success("🎉 Store verified and registered successfully!")
                                st.rerun()
                            else:
                                st.error(err)
                        else:
                            st.error("❌ Invalid OTP. Please enter the correct 4-digit code.")

    st.markdown('<div class="sm-footer">SHELF MIND • Simple technology for small businesses</div>', unsafe_allow_html=True)
    st.stop()

# -----------------------------------------------------------------------------
# ACTIVE STORE
# -----------------------------------------------------------------------------
current_store = st.session_state["logged_in_store"]
store_phone = current_store["phone_number"]
shop_name = current_store["shop_name"]
owner_name = current_store["owner_name"]
shop_upi = current_store["upi_id"]

# Sidebar remains for settings and logout; main experience is simplified.
with st.sidebar:
    st.markdown(f"### 🏪 {shop_name}")
    st.caption(f"👤 {owner_name}")
    st.caption(f"📞 +91 {store_phone}")
    st.divider()
    st.markdown("**Payment UPI**")
    st.code(shop_upi, language=None)

    with st.expander("⚙️ Store Settings"):
        with st.form("edit_profile_form"):
            updated_shop_name = st.text_input("Store Name", value=shop_name)
            updated_owner_name = st.text_input("Owner Name", value=owner_name)
            updated_upi = st.text_input("Store UPI ID", value=shop_upi)
            save_changes = st.form_submit_button("Save Changes", use_container_width=True, type="primary")
            if save_changes:
                if updated_shop_name and updated_owner_name and updated_upi:
                    db.update_shopkeeper_profile(store_phone, updated_shop_name, updated_owner_name, updated_upi)
                    st.session_state["logged_in_store"].update(
                        {"shop_name": updated_shop_name, "owner_name": updated_owner_name, "upi_id": updated_upi}
                    )
                    st.toast("Store details updated successfully!")
                    st.rerun()
                else:
                    st.error("Please fill in all fields.")

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["logged_in_store"] = None
        st.session_state["parsed_items"] = None
        st.query_params.clear()
        st.rerun()

# -----------------------------------------------------------------------------
# DASHBOARD HOME
# -----------------------------------------------------------------------------
total_skus, total_capital, dead_stock = db.get_kpi_metrics(store_phone)
total_udhar = db.get_total_udhar_pending(store_phone)

display_name = owner_name.split()[0] if owner_name else shop_name
st.markdown(
    f'<div class="sm-welcome"><div class="sm-eyebrow">Today at {shop_name}</div><h2>Namaste, {display_name} 👋</h2><p>Your shop at a glance. Use the quick actions below to get work done faster.</p></div>',
    unsafe_allow_html=True,
)

st.markdown('<div class="sm-section-title">Shop Overview</div>', unsafe_allow_html=True)
k1, k2 = st.columns(2)
k1.markdown(f'<div class="sm-card"><div class="sm-card-icon">📦</div><div class="sm-card-label">{t["total_skus"]}</div><div class="sm-card-value">{total_skus}</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="sm-card"><div class="sm-card-icon">💼</div><div class="sm-card-label">{t["working_capital"]}</div><div class="sm-card-value">₹{total_capital:,.0f}</div></div>', unsafe_allow_html=True)
k3, k4 = st.columns(2)
k3.markdown(f'<div class="sm-card"><div class="sm-card-icon">⚠️</div><div class="sm-card-label">{t["dead_stock"]}</div><div class="sm-card-value">₹{dead_stock:,.0f}</div></div>', unsafe_allow_html=True)
k4.markdown(f'<div class="sm-card"><div class="sm-card-icon">💰</div><div class="sm-card-label">{t["total_udhar"]}</div><div class="sm-card-value">₹{total_udhar:,.0f}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="sm-section-title">Quick Actions</div>', unsafe_allow_html=True)
a1, a2 = st.columns(2)
with a1:
    st.info("📷 **Scan Invoice**\n\nAdd incoming stock from a wholesale bill.")
    if st.button("Open Invoice Scanner →", key="quick_scan", use_container_width=True, type="primary"):
        st.session_state["active_tab"] = 0
        st.rerun()
with a2:
    st.info("💰 **Add Udhar**\n\nRecord customer credit and due date.")
    if st.button("Open Udhar Ledger →", key="quick_udhar", use_container_width=True):
        st.session_state["active_tab"] = 3
        st.rerun()

if total_udhar > 0:
    st.markdown(
        f'<div class="sm-alert"><strong>💰 Pending Udhar</strong><br><span>₹{total_udhar:,.0f} is currently outstanding. Open the Udhar Ledger to review customers and payment options.</span></div>',
        unsafe_allow_html=True,
    )
if total_skus == 0:
    st.markdown(
        '<div class="sm-alert"><strong>📦 Your inventory is empty</strong><br><span>Scan your first wholesale invoice to start building your digital stock.</span></div>',
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# WORKSPACE TABS
# -----------------------------------------------------------------------------
st.markdown('<div class="sm-section-title">Manage Your Shop</div>', unsafe_allow_html=True)
tab1, tab2, tab3, tab4 = st.tabs(
    [t["tab_upload"], t["tab_stock"], t["tab_alerts"], t["tab_udhar"]]
)

# TAB 1 — Invoice
with tab1:
    st.subheader(t["upload_heading"])
    st.caption("Take a clear photo of a wholesale bill. AI will extract the items for you.")
    input_mode = st.radio(
        "Capture Method",
        ["📸 Open Phone Camera", "📁 Upload from Gallery"],
        horizontal=True,
    )
    image_file = (
        st.camera_input("Take photo of wholesale bill")
        if input_mode == "📸 Open Phone Camera"
        else st.file_uploader(t["upload_btn"], type=["jpg", "png", "jpeg"])
    )

    if image_file is not None:
        file_type = image_file.type if hasattr(image_file, "type") and image_file.type else "image/jpeg"
        file_id = getattr(image_file, "name", "cam_snap")
        if "parsed_items" not in st.session_state or st.session_state.get("last_up") != file_id:
            with st.spinner("⚡ SHELF MIND is reading the invoice..."):
                extracted = extract_invoice_data_with_ai(image_file.getvalue(), mime_type=file_type)
                clean = []
                for i in extracted:
                    try:
                        clean.append(
                            {
                                "Item Name": str(i.get("Item Name", "")).strip(),
                                "Quantity": max(1, int(i.get("Quantity", 1))),
                                "Rate (₹)": max(0.0, float(i.get("Rate (₹)", i.get("Rate", 0.0)))),
                            }
                        )
                    except (TypeError, ValueError):
                        continue
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
                    "Item Name": st.column_config.TextColumn("Product", required=True),
                    "Quantity": st.column_config.NumberColumn("Qty", min_value=1, step=1, required=True),
                    "Rate (₹)": st.column_config.NumberColumn("Rate (₹)", min_value=0.0, step=0.5, format="₹%.2f", required=True),
                },
            )
            if st.button(f"✅ {t['save_stock_btn']}", use_container_width=True, type="primary"):
                db.add_or_update_stock(store_phone, df_edit.to_dict(orient="records"))
                st.balloons()
                st.success(t["stock_updated_toast"])
                st.session_state["parsed_items"] = None
                st.session_state["last_up"] = None
                st.rerun()

# TAB 2 — Stock
with tab2:
    st.subheader(t["tab_stock"])
    df_live = db.get_inventory_dataframe(store_phone)
    if not df_live.empty:
        st.dataframe(df_live, use_container_width=True, hide_index=True)
        st.caption("Tip: Scan another wholesale bill to increase quantities for existing products.")
    else:
        st.info("No stock recorded yet. Scan an invoice to populate inventory.")

# TAB 3 — Alerts
with tab3:
    st.subheader(t["tab_alerts"])
    st.markdown(
        f'<div class="sm-alert"><strong>⚠️ {t["dead_stock_alert"].replace("**", "")}</strong><br><span>Stock health analytics will become more useful as sales history is added.</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="sm-alert"><strong>🌦️ Weather Signal</strong><br><span>{t["weather_alert"].replace("**", "")}</span></div>',
        unsafe_allow_html=True,
    )
    st.caption("These alerts are currently informational; real demand forecasting requires sales history and a live weather data source.")

# TAB 4 — Udhar
with tab4:
    st.subheader(t["tab_udhar"])
    with st.expander(t["add_udhar_btn"], expanded=False):
        with st.form("new_udhar_form"):
            c_name = st.text_input(t["customer_name"])
            c_phone = st.text_input(t["phone_number"], placeholder="e.g. 9822123456")
            c_amount = st.number_input(t["udhar_amount"], min_value=1.0, step=10.0, value=250.0)
            c_items = st.text_input(t["items_taken"], placeholder="e.g. 1L Oil, 1kg Sugar")
            c_due = st.date_input(t["due_date"], min_value=date.today())
            if st.form_submit_button(t["save_udhar"], use_container_width=True, type="primary"):
                if c_name and c_phone:
                    clean_phone = c_phone.replace("+91", "").replace(" ", "").replace("-", "").strip()
                    if len(clean_phone) == 10 and clean_phone.isdigit():
                        db.add_udhar_entry(store_phone, c_name, clean_phone, c_amount, c_items, c_due)
                        st.success("Udhar entry saved!")
                        st.rerun()
                    else:
                        st.error("Please enter a valid 10-digit customer mobile number.")
                else:
                    st.error("Please enter both customer name and mobile number.")

    df_udhar = db.get_udhar_records(store_phone)
    pending = df_udhar[df_udhar["status"] != "Paid"] if not df_udhar.empty else df_udhar
    if not pending.empty:
        for _, row in pending.iterrows():
            with st.container(border=True):
                st.markdown(f"### 👤 {row['customer_name']}")
                st.caption(f"📞 +91 {row['customer_phone']}")
                amount_col, date_col = st.columns(2)
                amount_col.metric("Amount Due", f"₹{row['amount']:,.0f}")
                date_col.metric("Due Date", str(row["due_date"]))
                if row["items_note"]:
                    st.caption(f"🛍️ {row['items_note']}")

                upi_payload = (
                    f"upi://pay?pa={shop_upi}&pn={urllib.parse.quote(shop_name)}&am={row['amount']}&cu=INR&tn=Udhar_{row['id']}"
                )
                qr = qrcode.QRCode(box_size=4, border=1)
                qr.add_data(upi_payload)
                qr.make(fit=True)
                img_qr = qr.make_image(fill_color="black", back_color="white")
                buf = io.BytesIO()
                img_qr.save(buf, format="PNG")

                b1, b2 = st.columns(2)
                with b1:
                    with st.expander("📲 Show UPI QR"):
                        st.image(buf.getvalue(), caption=f"Pay ₹{row['amount']:,.2f}", width=180)
                with b2:
                    if lang_key == "mr":
                        msg = f"नमस्कार {row['customer_name']}जी, {shop_name} दुकानाची ₹{row['amount']} उधारी बाकी आहे. देय तारीख: {row['due_date']}. UPI भुगतान लिंक: {upi_payload}"
                    elif lang_key == "hi":
                        msg = f"नमस्ते {row['customer_name']}जी, {shop_name} की ₹{row['amount']} उधारी बकाया है। अंतिम तिथि: {row['due_date']}. UPI भुगतान लिंक: {upi_payload}"
                    else:
                        msg = f"Dear {row['customer_name']}, ₹{row['amount']} credit is pending at {shop_name}. Due date: {row['due_date']}. Pay via UPI: {upi_payload}"
                    wa_url = f"https://wa.me/91{row['customer_phone']}?text={urllib.parse.quote(msg)}"
                    st.link_button("📲 WhatsApp Reminder", wa_url, use_container_width=True)

                if st.button(t["mark_paid"], key=f"settle_{row['id']}", use_container_width=True, type="primary"):
                    db.settle_udhar(row["id"])
                    st.toast(f"Payment settled for {row['customer_name']}!")
                    st.rerun()
    else:
        st.info("No pending Udhar records for this store.")

st.markdown('<div class="sm-footer">SHELF MIND • Smart tools for small retailers</div>', unsafe_allow_html=True)
