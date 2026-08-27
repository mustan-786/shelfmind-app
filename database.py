import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "shelfmind.db"


def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    """Initializes isolated tables for Shopkeepers, Store Inventories, and Udhar Records."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Shopkeeper Profiles
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shopkeepers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_name TEXT NOT NULL,
            owner_name TEXT NOT NULL,
            phone_number TEXT UNIQUE NOT NULL,
            upi_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # 2. Store Inventory (Starts Empty)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_phone TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            wholesale_rate REAL NOT NULL DEFAULT 0.0,
            last_restocked TEXT NOT NULL,
            status TEXT DEFAULT 'Active',
            UNIQUE(store_phone, item_name)
        )
    """)

    # 3. Udhar / Credit Ledger (Starts Empty)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS udhar_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_phone TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            amount REAL NOT NULL,
            items_note TEXT,
            credit_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    """)

    conn.commit()
    conn.close()


# Shopkeeper Profile Handlers
def register_shopkeeper(shop_name, owner_name, phone_number, upi_id):
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        cursor.execute("""
            INSERT INTO shopkeepers (shop_name, owner_name, phone_number, upi_id, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (shop_name.strip(), owner_name.strip(), phone_number.strip(), upi_id.strip(), created_at))
        conn.commit()
        success, err = True, ""
    except sqlite3.IntegrityError:
        success, err = False, "This mobile number is already registered. Please log in."
    conn.close()
    return success, err


def get_shopkeeper(phone_number):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT shop_name, owner_name, phone_number, upi_id FROM shopkeepers WHERE phone_number = ?",
                   (phone_number.strip(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"shop_name": row[0], "owner_name": row[1], "phone_number": row[2], "upi_id": row[3]}
    return None


def update_shopkeeper_upi(phone_number, new_upi_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE shopkeepers SET upi_id = ? WHERE phone_number = ?",
                   (new_upi_id.strip(), phone_number.strip()))
    conn.commit()
    conn.close()


# Inventory Handlers
def add_or_update_stock(store_phone, items_list):
    conn = get_connection()
    cursor = conn.cursor()
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    for item in items_list:
        name = str(item.get("Item Name", "")).strip()
        if not name:
            continue
        qty = int(item.get("Quantity", 1))
        rate = float(item.get("Rate (₹)", item.get("Rate", 0.0)))

        cursor.execute("SELECT quantity FROM inventory WHERE store_phone = ? AND item_name = ?", (store_phone, name))
        row = cursor.fetchone()

        if row:
            new_qty = row[0] + qty
            cursor.execute("""
                UPDATE inventory 
                SET quantity = ?, wholesale_rate = ?, last_restocked = ?, status = 'Active / Restocked'
                WHERE store_phone = ? AND item_name = ?
            """, (new_qty, rate, today_str, store_phone, name))
        else:
            cursor.execute("""
                INSERT INTO inventory (store_phone, item_name, quantity, wholesale_rate, last_restocked, status)
                VALUES (?, ?, ?, ?, ?, 'New SKU')
            """, (store_phone, name, qty, rate, today_str))

    conn.commit()
    conn.close()


def get_inventory_dataframe(store_phone):
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT item_name AS 'Item SKU', quantity AS 'Stock Qty', wholesale_rate AS 'Rate (₹)', 
               (quantity * wholesale_rate) AS 'Total Capital (₹)', status AS 'Status', last_restocked AS 'Last Updated' 
        FROM inventory WHERE store_phone = ? ORDER BY id DESC
    """, conn, params=(store_phone,))
    conn.close()
    return df


def get_kpi_metrics(store_phone):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(quantity * wholesale_rate) FROM inventory WHERE store_phone = ?",
                   (store_phone,))
    row = cursor.fetchone()
    total_skus = row[0] or 0
    total_capital = row[1] or 0.0

    cursor.execute(
        "SELECT SUM(quantity * wholesale_rate) FROM inventory WHERE store_phone = ? AND (status LIKE '%Dead%' OR status LIKE '%Stagnant%')",
        (store_phone,))
    dead_capital = cursor.fetchone()[0] or 0.0
    conn.close()
    return total_skus, round(total_capital, 2), round(dead_capital, 2)


# Udhar Handlers
def add_udhar_entry(store_phone, customer_name, customer_phone, amount, items_note, due_date):
    conn = get_connection()
    cursor = conn.cursor()
    credit_date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        INSERT INTO udhar_ledger (store_phone, customer_name, customer_phone, amount, items_note, credit_date, due_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending')
    """, (store_phone, customer_name.strip(), customer_phone.strip(), amount, items_note.strip(), credit_date,
          str(due_date)))
    conn.commit()
    conn.close()


def get_udhar_records(store_phone):
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT id, customer_name, customer_phone, amount, items_note, credit_date, due_date, status 
        FROM udhar_ledger WHERE store_phone = ? ORDER BY due_date ASC
    """, conn, params=(store_phone,))
    conn.close()
    return df


def settle_udhar(record_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE udhar_ledger SET status = 'Paid' WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def get_total_udhar_pending(store_phone):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(amount) FROM udhar_ledger WHERE store_phone = ? AND status != 'Paid'", (store_phone,))
    total = cursor.fetchone()[0] or 0.0
    conn.close()
    return round(total, 2)
