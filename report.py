# report.py
import os
import sqlite3
import requests
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "Details_data", "Record.db")

# === CONFIG ===
ADMIN_PHONE = "7700927099"
SMS_API_KEY = "8BcfYi72sCeWhgqlpkIDwbZS9M3vV1mR6Xn5tzLrjNUOaHAQFySMeFi4fb8cRDmQp1qakE3VWTNxshvK"
SENDER_ID = "AVSHKR"

# ============================= MAIN ALERT =============================
def send_silent_alert(scan_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT * FROM scans WHERE id = ?", (scan_id,))
    scan = c.fetchone()
    c.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 1")
    session = c.fetchone()
    conn.close()

    if not scan: return

    image_path = scan[1]
    basename = scan[2]
    skin = scan[3]
    score = scan[4]
    verdict = scan[5]
    scan_time = scan[6]

    user_name = session[1] if session else "Unknown"
    user_phone = session[3] if session else "Unknown"
    user_aadhaar = session[5] if session else "Unknown"

    # === 1. SAVE REPORT TXT ===
    report = f"""
PREVENTIVE CYBER ALERT 
-------------------------------------------
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Scan ID: {scan_id}

VIOLATION:
- File: {basename}
- Path: {image_path}
- Skin %: {skin:.1f}%
- NSFW Score: {score}%
- Verdict: {verdict}
- Detected At: {scan_time}

SUSPECT:
- Name: {user_name}
- Phone: {user_phone}
- ID: {user_aadhaar}

ACTION: Immediate monitoring advised.
    """.strip()

    report_file = os.path.join(os.path.dirname(DB_FILE), f"PREVENTIVE_ALERT_{scan_id}.txt")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"[BACKEND] Report saved: {report_file}")

    # === 2. SEND SMS (NEW API LOGIC) ===
    sms_sent = False
    try:
        sms_text = f"PREVENTIVE: NSFW by {user_name} | {user_phone} | {basename} | {score}%"
        url = "https://www.fast2sms.com/dev/bulkV2"
        payload = {
            "sender_id": SENDER_ID,
            "message": sms_text,
            "numbers": ADMIN_PHONE,
            "route": "q"
        }
        headers = {"authorization": SMS_API_KEY}
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        
        response = r.json()
        print(f"[DEBUG] Fast2SMS Response: {response}")  # ← YE DEKHO

        # NEW: Check "status" instead of "return"
        if response.get("status") == "success" or response.get("return") == True:
            sms_sent = True
            print(f"[BACKEND] SMS SENT → {ADMIN_PHONE}")
        else:
            print(f"[BACKEND] SMS FAILED → {response}")
    except Exception as e:
        print(f"[BACKEND] SMS ERROR → {e}")

    # === 3. STATUS ===
    print("\n" + "="*70)
    print("   PREVENTIVE REPORT STATUS (BACKEND)")
    print("="*70)
    print(f"   File: PREVENTIVE_ALERT_{scan_id}.txt → CREATED")
    print(f"   SMS:  {'SENT' if sms_sent else 'FAILED'} → {ADMIN_PHONE}")
    print("="*70 + "\n")

# ============================= ATTEMPT ALERT =============================
def send_attempt_alert(scan_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM scans WHERE id = ?", (scan_id,))
    scan = c.fetchone()
    conn.close()
    if not scan: return

    try:
        sms_text = f"ALERT: NSFW attempt closed | {scan[2]} | {scan[4]}%"
        url = "https://www.fast2sms.com/dev/bulkV2"
        payload = {"sender_id": SENDER_ID, "message": sms_text, "numbers": ADMIN_PHONE, "route": "q"}
        headers = {"authorization": SMS_API_KEY}
        r = requests.post(url, json=payload, headers=headers, timeout=5)
        response = r.json()
        if response.get("status") == "success" or response.get("return") == True:
            print(f"[BACKEND] Attempt alert sent to {ADMIN_PHONE}")
        else:
            print(f"[BACKEND] Attempt SMS failed: {response}")
    except Exception as e:
        print(f"[BACKEND] Attempt SMS error: {e}")