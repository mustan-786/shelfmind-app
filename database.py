import json
import sqlite3
from datetime import datetime, timedelta
import pandas as pd

DB_NAME = "shelfmind.db"


def get_connection():
  return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
  conn = get_connection()
  cursor = conn.cursor()

  # 1. Shopkeeper Accounts
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

  # 2. Store Inventory
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

  # 3. Udhar / Credit Ledger
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

  # 4. Shelf Photo Audits (Weekly / Periodic Scan Tracking)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS shelf_audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_phone TEXT NOT NULL,
            audit_date TEXT NOT NULL,
            detected_items TEXT NOT NULL,
            photo_notes TEXT
        )
    """)
  conn.commit()
  conn.close()


def register_shopkeeper(shop_name, owner_name, phone_number, upi_id):
  conn = get_connection()
  cursor = conn.cursor()
  created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
  clean_phone = phone_number.replace("+91", "").replace(" ", "").strip()
  try:
    cursor.execute(
        """
            INSERT INTO shopkeepers (shop_name, owner_name, phone_number, upi_id, created_at)
            VALUES (?, ?, ?, ?, ?)
        """,
        (
            shop_name.strip(),
            owner_name.strip(),
            clean_phone,
            upi_id.strip(),
            created_at,
        ),
    )
    conn.commit()
    success, err = True, ""
  except sqlite3.IntegrityError:
    success, err = (
        False,
        "This mobile number is already registered. Please log in.",
    )
  conn.close()
  return success, err


def get_shopkeeper(phone_number):
  conn = get_connection()
  cursor = conn.cursor()
  clean_phone = phone_number.replace("+91", "").replace(" ", "").strip()
  cursor.execute(
      "SELECT shop_name, owner_name, phone_number, upi_id FROM shopkeepers"
      " WHERE phone_number = ?",
      (clean_phone,),
  )
  row = cursor.fetchone()
  conn.close()
  if row:
    return {
        "shop_name": row[0],
        "owner_name": row[1],
        "phone_number": row[2],
        "upi_id": row[3],
    }
  return None


def update_shopkeeper_profile(
    phone_number, new_shop_name, new_owner_name, new_upi_id
):
  conn = get_connection()
  cursor = conn.cursor()
  clean_phone = phone_number.replace("+91", "").replace(" ", "").strip()
  cursor.execute(
      """
        UPDATE shopkeepers 
        SET shop_name = ?, owner_name = ?, upi_id = ? 
        WHERE phone_number = ?
    """,
      (
          new_shop_name.strip(),
          new_owner_name.strip(),
          new_upi_id.strip(),
          clean_phone,
      ),
  )
  conn.commit()
  conn.close()


def add_or_update_stock(store_phone, items_list):
  conn = get_connection()
  cursor = conn.cursor()
  today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
  clean_phone = store_phone.replace("+91", "").replace(" ", "").strip()

  for item in items_list:
    name = str(item.get("Item Name", "")).strip()
    if not name:
      continue
    qty = int(item.get("Quantity", 1))
    rate = float(item.get("Rate (₹)", item.get("Rate", 0.0)))

    cursor.execute(
        "SELECT quantity FROM inventory WHERE store_phone = ? AND item_name ="
        " ?",
        (clean_phone, name),
    )
    row = cursor.fetchone()

    if row:
      new_qty = row[0] + qty
      cursor.execute(
          """
                UPDATE inventory 
                SET quantity = ?, wholesale_rate = ?, last_restocked = ?, status = 'Active / Restocked'
                WHERE store_phone = ? AND item_name = ?
            """,
          (new_qty, rate, today_str, clean_phone, name),
      )
    else:
      cursor.execute(
          """
                INSERT INTO inventory (store_phone, item_name, quantity, wholesale_rate, last_restocked, status)
                VALUES (?, ?, ?, ?, ?, 'Active')
            """,
          (clean_phone, name, qty, rate, today_str),
      )

  conn.commit()
  conn.close()


def get_inventory_dataframe(store_phone):
  conn = get_connection()
  clean_phone = store_phone.replace("+91", "").replace(" ", "").strip()
  df = pd.read_sql_query(
      """
        SELECT item_name AS 'Item SKU', quantity AS 'Stock Qty', wholesale_rate AS 'Rate (₹)', 
               (quantity * wholesale_rate) AS 'Total Capital (₹)', status AS 'Status', last_restocked AS 'Last Updated' 
        FROM inventory WHERE store_phone = ? ORDER BY id DESC
    """,
      conn,
      params=(clean_phone,),
  )
  conn.close()
  return df


def get_dead_stock_candidates(store_phone, days_threshold=30):
  conn = get_connection()
  cursor = conn.cursor()
  clean_phone = store_phone.replace("+91", "").replace(" ", "").strip()
  cursor.execute(
      """
        SELECT item_name, quantity, wholesale_rate, last_restocked, status
        FROM inventory
        WHERE store_phone = ? AND quantity > 0
    """,
      (clean_phone,),
  )
  rows = cursor.fetchall()
  conn.close()

  candidates = []
  now = datetime.now()

  for r in rows:
    name, qty, rate, restocked_str, status = r[0], r[1], r[2], r[3], r[4]
    days_idle = days_threshold
    if restocked_str:
      try:
        dt = datetime.strptime(str(restocked_str)[:10], "%Y-%m-%d")
        days_idle = (now - dt).days
      except Exception:
        days_idle = days_threshold

    is_marked_dead = "dead" in str(status).lower() or "stagnant" in str(
        status
    ).lower()

    if days_idle >= days_threshold or is_marked_dead:
      candidates.append({
          "item_name": name,
          "quantity": qty,
          "rate": rate,
          "capital_blocked": round(qty * rate, 2),
          "days_idle": max(days_idle, days_threshold),
      })

  return candidates


def get_kpi_metrics(store_phone):
  conn = get_connection()
  cursor = conn.cursor()
  clean_phone = store_phone.replace("+91", "").replace(" ", "").strip()
  cursor.execute(
      "SELECT COUNT(*), SUM(quantity * wholesale_rate) FROM inventory WHERE"
      " store_phone = ?",
      (clean_phone,),
  )
  row = cursor.fetchone()
  total_skus = row[0] or 0
  total_capital = row[1] or 0.0
  conn.close()

  dead_candidates = get_dead_stock_candidates(clean_phone, days_threshold=30)
  dead_capital = sum(item["capital_blocked"] for item in dead_candidates)

  return total_skus, round(total_capital, 2), round(dead_capital, 2)


def save_shelf_audit(store_phone, detected_items, notes=""):
  conn = get_connection()
  cursor = conn.cursor()
  today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
  clean_phone = store_phone.replace("+91", "").replace(" ", "").strip()
  cursor.execute(
      """
        INSERT INTO shelf_audits (store_phone, audit_date, detected_items, photo_notes)
        VALUES (?, ?, ?, ?)
    """,
      (clean_phone, today_str, json.dumps(detected_items), notes),
  )
  conn.commit()
  conn.close()


def get_latest_shelf_audits(store_phone, limit=4):
  conn = get_connection()
  cursor = conn.cursor()
  clean_phone = store_phone.replace("+91", "").replace(" ", "").strip()
  cursor.execute(
      """
        SELECT audit_date, detected_items, photo_notes
        FROM shelf_audits
        WHERE store_phone = ?
        ORDER BY id DESC LIMIT ?
    """,
      (clean_phone, limit),
  )
  rows = cursor.fetchall()
  conn.close()

  history = []
  for r in rows:
    try:
      history.append({
          "date": r[0],
          "items": json.loads(r[1]),
          "notes": r[2] or "",
      })
    except Exception:
      pass
  return history
  def get_audit_comparison_pair(store_phone):
    """
    Returns the two most recent shelf audits to enable side-by-side comparison.
    Returns (latest_audit, previous_audit) or (None, None) if fewer than 2 exist.
    """
    conn = get_connection()
    cursor = conn.cursor()
    clean_phone = store_phone.replace("+91", "").replace(" ", "").strip()
    cursor.execute("""
        SELECT audit_date, detected_items, photo_notes 
        FROM shelf_audits 
        WHERE store_phone = ? 
        ORDER BY id DESC LIMIT 2
    """, (clean_phone,))
    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 2:
        return None, None

    try:
        latest = {
            "date": rows[0][0],
            "items": json.loads(rows[0][1]),
            "notes": rows[0][2] or ""
        }
        previous = {
            "date": rows[1][0],
            "items": json.loads(rows[1][1]),
            "notes": rows[1][2] or ""
        }
        return latest, previous
    except Exception:
        return None, None
  def get_audit_comparison_pair(store_phone):
    """
    Returns the two most recent shelf audits to enable side-by-side comparison.
    Returns (latest_audit, previous_audit) or None if fewer than 2 exist.
    """
    conn = get_connection()
    cursor = conn.cursor()
    clean_phone = store_phone.replace("+91", "").replace(" ", "").strip()
    cursor.execute("""
        SELECT audit_date, detected_items, photo_notes 
        FROM shelf_audits 
        WHERE store_phone = ? 
        ORDER BY id DESC LIMIT 2
    """, (clean_phone,))
    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 2:
        return None, None

    try:
        latest = {"date": rows[0][0], "items": json.loads(rows[0][1]), "notes": rows[0][2]}
        previous = {"date": rows[1][0], "items": json.loads(rows[1][1]), "notes": rows[1][2]}
        return latest, previous
    except Exception:
        return None, None


def add_udhar_entry(
    store_phone, customer_name, customer_phone, amount, items_note, due_date
):
  conn = get_connection()
  cursor = conn.cursor()
  credit_date = datetime.now().strftime("%Y-%m-%d")
  clean_store = store_phone.replace("+91", "").replace(" ", "").strip()
  clean_cust = customer_phone.replace("+91", "").replace(" ", "").strip()
  cursor.execute(
      """
        INSERT INTO udhar_ledger (store_phone, customer_name, customer_phone, amount, items_note, credit_date, due_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending')
    """,
      (
          clean_store,
          customer_name.strip(),
          clean_cust,
          amount,
          items_note.strip(),
          credit_date,
          str(due_date),
      ),
  )
  conn.commit()
  conn.close()


def get_udhar_records(store_phone):
  conn = get_connection()
  clean_phone = store_phone.replace("+91", "").replace(" ", "").strip()
  df = pd.read_sql_query(
      """
        SELECT id, customer_name, customer_phone, amount, items_note, credit_date, due_date, status 
        FROM udhar_ledger WHERE store_phone = ? ORDER BY due_date ASC
    """,
      conn,
      params=(clean_phone,),
  )
  conn.close()
  return df


def settle_udhar(record_id):
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute(
      "UPDATE udhar_ledger SET status = 'Paid' WHERE id = ?", (record_id,)
  )
  conn.commit()
  conn.close()


def get_total_udhar_pending(store_phone):
  conn = get_connection()
  cursor = conn.cursor()
  clean_phone = store_phone.replace("+91", "").replace(" ", "").strip()
  cursor.execute(
      "SELECT SUM(amount) FROM udhar_ledger WHERE store_phone = ? AND status !="
      " 'Paid'",
      (clean_phone,),
  )
  total = cursor.fetchone()[0] or 0.0
  conn.close()
  return round(total, 2)
