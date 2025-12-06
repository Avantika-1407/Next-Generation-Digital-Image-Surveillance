# main.py
import os
import time
import threading
import sqlite3
import random
import requests
import shutil  # ← YE ADD KIYA HAI
from datetime import datetime
import comtypes
from comtypes import client
import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox, scrolledtext

# ============================= CONFIG =============================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_DATA_DIR = os.path.join(PROJECT_ROOT, "Details_data")
os.makedirs(APP_DATA_DIR, exist_ok=True)

LOG_FILE = os.path.join(APP_DATA_DIR, 'guard.log')
DB_FILE  = os.path.join(APP_DATA_DIR, 'Record.db')
OTP_FILE = os.path.join(APP_DATA_DIR, 'temp_otp.txt')

API_KEY   = "8BcfYi72sCeWhgqlpkIDwbZS9M3vV1mR6Xn5tzLrjNUOaHAQFySMeFi4fb8cRDmQp1qakE3VWTNxshvK"
SENDER_ID = "FSTSMS"

# ← YE TUMHARA UPLOAD FOLDER (OneDrive Desktop)
UPLOAD_FOLDER = r"C:\Users\anish\OneDrive\Desktop\photo store"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

consent_window_open = False
current_scanned_image_path = None  # Global variable to track current NSFW image

# ============================= LOGGING =============================
def log(msg: str):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + "\n")
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO activities (message) VALUES (?)", (msg,))
        conn.commit()
        conn.close()
    except: pass

# ============================= DATABASE =============================
def init_db():
    print(f"[DATABASE] Creating at: {DB_FILE}")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT, age INTEGER, phone TEXT, email TEXT, aadhaar TEXT,
                    session_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_path TEXT, basename TEXT,
                    skin_percent REAL, score REAL, verdict TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()
    print("[SUCCESS] Database ready!")

# ============================= OTP =============================
def send_otp(phone: str):
    otp = random.randint(100000, 999999)
    url = "https://www.fast2sms.com/dev/bulkV2"
    payload = {"sender_id": SENDER_ID, "message": f"Verification OTP: {otp}", "numbers": phone, "route": "q"}
    headers = {"authorization": API_KEY}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        if r.json().get("return"):
            log(f"OTP sent to {phone}")
    except Exception as e:
        log(f"OTP failed: {e}")
    with open(OTP_FILE, "w") as f:
        f.write(f"{phone}:{otp}:{time.time()}")

def verify_otp(phone: str, user_otp: str) -> bool:
    if not os.path.exists(OTP_FILE):
        return False
    try:
        with open(OTP_FILE, "r") as f:
            data = f.read().strip().split(":")
        if len(data) == 3 and data[0] == phone and data[1] == user_otp and time.time() - float(data[2]) < 300:
            os.remove(OTP_FILE)
            log(f"OTP verified: {phone}")
            return True
    except: pass
    log(f"OTP failed: {phone}")
    return False

def save_session(name, age, phone, email="", aadhaar=""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO sessions (name, age, phone, email, aadhaar) VALUES (?, ?, ?, ?, ?)",
              (name, age, phone, email, aadhaar))
    conn.commit()
    conn.close()
    log(f"Session saved: {name}")

# ============================= CONSENT GUI =============================
def launch_consent_gui_with_report(scan_id: int):
    global consent_window_open
    if consent_window_open:
        return
    consent_window_open = True
    log("Launching consent form")

    root = tk.Tk()
    root.title("Consent form")
    root.geometry("850x780")
    root.configure(bg="#0d1b2a")

    canvas = tk.Canvas(root, bg="#0d1b2a", highlightthickness=0)
    scrollbar = tk.Scrollbar(root, command=canvas.yview)
    frame = tk.Frame(canvas, bg="#0d1b2a")
    canvas.create_window((0,0), window=frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    tk.Label(frame, text="Consent Form", font=("Impact", 36, "bold"), fg="#00ff41", bg="#0d1b2a").pack(pady=20)
    tk.Label(frame, text="Verify Identity", font=("Arial", 12, "bold"), fg="#ff4444", bg="#0d1b2a").pack()

    entries = []
    for label in ["Full Name *", "Age *", "Phone (10 digits) *", "Email *", "Aadhaar / PAN *"]:
        row = tk.Frame(frame, bg="#0d1b2a")
        row.pack(pady=8, padx=60, fill="x")
        tk.Label(row, text=label, font=("Arial", 12, "bold"), fg="white", bg="#0d1b2a", width=28, anchor="w").pack(side="left")
        e = tk.Entry(row, width=38, bg="#1e2a38", fg="white")
        e.pack(side="right")
        entries.append(e)

    tc_frame = tk.Frame(frame, bg="#1e2a38", relief="sunken", bd=2)
    tc_frame.pack(padx=60, pady=15, fill="both", expand=True)
    tc = scrolledtext.ScrolledText(tc_frame, width=88, height=12, bg="#1e2a38", fg="#e0e1dd", font=("Arial", 10))
    tc.pack(padx=10, pady=10)

    terms = """
Concent form - TERMS & CONDITIONS
─────────────────────────────────────
1. OBSCENE EDITING DETECTED
2. This system prevents creation of revenge-porn/morphed images.
3. Enter your genuine 10-digit mobile number
4.OTP will be sent for verification
5. Verified number + image will be auto-saved as evidence
6. Silent alert will be sent to authority
7. Closing this window or wrong OTP → Alert & evidence still sent
8. You are above 18 and accept the above terms.
    """.strip()
    tc.insert("1.0", terms)
    tc.config(state="disabled")

    def proceed():
        name, age, phone, email, aadhaar = [e.get().strip() for e in entries]
        if not all([name, age.isdigit(), len(phone)==10, phone.isdigit(), email, aadhaar]):
            messagebox.showerror("Error", "Fill all fields!")
            return
        if int(age) < 18:
            messagebox.showerror("Blocked", "18+ only!")
            return

        send_otp(phone)
        win = tk.Toplevel(root)
        win.geometry("500x300")
        win.title("OTP")
        tk.Label(win, text="Enter OTP", font=("Arial", 18), fg="#00ff41", bg="#0d1b2a").pack(pady=30)
        otp_e = tk.Entry(win, font=("Arial", 20), justify="center", show="*", width=10)
        otp_e.pack(pady=20)

        def verify():
            global current_scanned_image_path
            if verify_otp(phone, otp_e.get()):
                save_session(name, int(age), phone, email, aadhaar)

                # ——— YE SABSE BADA KAAM ———
                if current_scanned_image_path and os.path.exists(current_scanned_image_path):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    original_name = os.path.basename(current_scanned_image_path)
                    new_filename = f"NSFW_PROOF_{timestamp}_{name}_{phone}_{original_name}"
                    destination = os.path.join(UPLOAD_FOLDER, new_filename)

                    try:
                        shutil.copy2(current_scanned_image_path, destination)
                        log(f"PHOTO UPLOADED TO ONEDRIVE: {new_filename}")
                        print(f"\n[EVIDENCE] PHOTO SAVED TO YOUR FOLDER:\n→ {destination}\n")
                    except Exception as e:
                        log(f"Upload failed: {e}")
                        print(f"[ERROR] Upload failed: {e}")

                messagebox.showinfo("Success", "Access Granted!\nPhoto saved as proof.")
                from report import send_silent_alert
                send_silent_alert(scan_id)
                root.destroy()
            else:
                messagebox.showerror("Failed", "Wrong OTP")

        tk.Button(win, text="VERIFY", bg="#00ff41", command=verify, width=20, height=2).pack(pady=10)

    btns = tk.Frame(frame, bg="#0d1b2a")
    btns.pack(pady=30)
    tk.Button(btns, text="I AGREE & SEND OTP", bg="#00ff41", fg="black", command=proceed, width=30, height=2).pack(side="left", padx=20)
    tk.Button(btns, text="EXIT", bg="#ff4444", command=lambda: on_close(scan_id), width=15, height=2).pack(side="left")

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def on_close(scan_id):
        log(f"Consent form closed | Scan ID: {scan_id}")
        from report import send_attempt_alert
        send_attempt_alert(scan_id)
        root.destroy()
        global consent_window_open
        consent_window_open = False

    root.protocol("WM_DELETE_WINDOW", lambda: on_close(scan_id))
    root.mainloop()
    consent_window_open = False

# ============================= SCANNER =============================
def avishkar_final_scan(image_path: str):
    global current_scanned_image_path
    image_path = image_path.strip().strip('"').strip("'")
    current_scanned_image_path = image_path  # Track this image

    if not os.path.exists(image_path):
        log(f"File not found: {image_path}")
        return

    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        log(f"Cannot read: {image_path}")
        return

    h, w = img.shape[:2]
    total = h * w
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    skin_mask = cv2.inRange(hsv, (0,15,50), (30,255,255))
    kernel = np.ones((10,10), np.uint8)
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
    skin_percent = (cv2.countNonZero(skin_mask) / total) * 100

    if skin_percent <= 50:
        verdict = "SAFE"
        score = min(50, round(skin_percent * 1.1, 1))
    else:
        verdict = "NSFW"
        score = round(51 + (skin_percent - 50) * 3.2, 1)
        if score > 100: score = 100

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO scans (image_path, basename, skin_percent, score, verdict) VALUES (?, ?, ?, ?, ?)",
                  (image_path, os.path.basename(image_path), skin_percent, score, verdict))
        scan_id = c.lastrowid
        conn.commit()
        conn.close()

        threading.Thread(target=launch_consent_gui_with_report, args=(scan_id,), daemon=True).start()

    # Always log scan
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO scans (image_path, basename, skin_percent, score, verdict) VALUES (?, ?, ?, ?, ?)",
              (image_path, os.path.basename(image_path), skin_percent, score, verdict))
    conn.commit()
    conn.close()

    print(f"\n   VERDICT: {verdict} | Score: {score}% | Skin: {skin_percent:.1f}%")
    log(f"Scanned: {os.path.basename(image_path)} → {verdict}")

# ============================= WATCHER =============================
class SelectionWatcher(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True
        self.last = None
        self.deselected = True

    def run(self):
        log("Watcher started")
        comtypes.CoInitialize()
        time.sleep(2.5)
        try:
            while self.running:
                path = self.get_path()
                if path is None:
                    if not self.deselected:
                        log("Selection cleared")
                    self.deselected = True
                    self.last = None
                elif (self.deselected and path != self.last and self.is_valid(path)):
                    self.last = path
                    self.deselected = False
                    log(f"Selected: {path}")
                    avishkar_final_scan(path)
                time.sleep(0.5)
        finally:
            comtypes.CoUninitialize()

    def get_path(self):
        try:
            shell = client.CreateObject("Shell.Application")
            for win in shell.Windows():
                if "explorer.exe" in win.FullName.lower():
                    sel = win.Document.SelectedItems()
                    if sel.Count > 0:
                        return sel.Item(0).Path
        except: pass
        return None

    def is_valid(self, p):
        if not os.path.isfile(p):
            return False
        ext = p.lower().split(".")[-1]
        if ext not in {"jpg","jpeg","png","bmp","gif","webp","heic","psd"}:
            return False
        img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
        return img is not None and img.size > 0

    def stop(self):
        self.running = False

# ============================= MAIN =============================
def main():
    init_db()
    log("=== SHIELDX PROTOCOL STARTED (ONE-DRIVE UPLOAD ACTIVE) ===")
    watcher = SelectionWatcher()
    watcher.start()
    print("\nSHIELDX ACTIVATED → Select any image → Proof auto-saved to OneDrive!")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("=== SHIELDX STOPPED ===")
        watcher.stop()
        watcher.join()

if __name__ == "__main__":
    main()