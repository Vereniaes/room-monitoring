import json
import os
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(ROOT_DIR, "settings.json")
MOCK_EMAIL_LOG = os.path.join(ROOT_DIR, "mock_emails.log")

# --- HELPER MEMBACA PENGATURAN BERSAMA ---
def load_settings():
    default_settings = {
        "recipient_email": "admin@kampus.ac.id",
        "email_alerts_enabled": True,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_password": ""
    }
    
    if not os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(default_settings, f, indent=4)
        except Exception:
            pass
        return default_settings
        
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
            # Isi kolom kosong dengan default
            for k, v in default_settings.items():
                if k not in settings:
                    settings[k] = v
            return settings
    except Exception:
        return default_settings

# --- FUNGSI UTAMA: PENGIRIMAN EMAIL (ASYNC & SAFE MOCK) ---
def _send_email_worker(subject, body):
    settings = load_settings()
    
    if not settings.get("email_alerts_enabled", True):
        return
        
    recipient = "titasaripratiwi8@gmail.com"  # Hardcode penerima
    smtp_user = "titasaripratiwi8@gmail.com"  # Email pengirim Gmail
    smtp_password = "vycqnyqljbbdzqrs" # App Password Gmail
    smtp_host = "smtp.gmail.com"
    smtp_port = 587
    
    # 1. KASUS MOCK MODE: SMTP tidak dikonfigurasi (Kredensial Kosong)
    # Ini sangat penting agar sistem tidak crash saat simulasi offline/tanpa akun Google asli!
    if not smtp_user or not smtp_password:
        mock_log = f"[{settings.get('recipient_email')}] | SUBJECT: {subject} | BODY: {body.replace(chr(10), ' ')}"
        print(f"\033[94m[MOCK EMAIL ALERT SENT TO {recipient}]\033[0m {subject}")
        try:
            with open(MOCK_EMAIL_LOG, "a") as f:
                f.write(f"Timestamp: {os.popen('date').read().strip()} | TO: {recipient} | SUBJECT: {subject}\nCONTENT:\n{body}\n{'-'*50}\n")
        except Exception:
            pass
        return
        
    # 2. KASUS RIIL MODE: SMTP terkonfigurasi (Mengirim Email Asli)
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = recipient
        msg['Subject'] = f"🛡️ IoT Security: {subject}"
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Inisialisasi koneksi SMTP
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()  # Enkripsi SSL/TLS
        server.login(smtp_user, smtp_password)
        text = msg.as_string()
        server.sendmail(smtp_user, recipient, text)
        server.quit()
        
        print(f"\033[92m[REAL EMAIL ALERT SENT TO {recipient}]\033[0m {subject}")
    except Exception as e:
        # Jika pengiriman riil gagal, jangan crash! Catat eror dan simpan sebagai mock fallback
        error_msg = f"[REAL EMAIL FAILED: {e}] TO: {recipient} | SUBJECT: {subject}\nCONTENT:\n{body}\n{'-'*50}\n"
        print(f"\033[91m[EMAIL ERROR]\033[0m Gagal mengirim email riil via SMTP: {e}. Disimpan ke log mock.")
        try:
            with open(MOCK_EMAIL_LOG, "a") as f:
                f.write(error_msg)
        except Exception:
            pass

# Menjalankan pengiriman email di background thread agar tidak men-delay request utama (Async)
def send_email_alert(subject, body):
    thread = threading.Thread(target=_send_email_worker, args=(subject, body))
    thread.daemon = True
    thread.start()
