import os
import datetime
import logging
from pathlib import Path
from flask import Flask, request, jsonify
import requests
from email_helper import send_email_alert

# ======
# Load konfigurasi dari .env (untuk development lokal)
# Di Cloud Run, env var di-inject langsung via --set-env-vars
# ======
def _load_env():
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())

_load_env()

app = Flask(__name__)

# ======
# CHECKLIST A: API Security

# - API Key validation: SECURE_TOKEN divalidasi di setiap endpoint sensitif
# - Bearer Token / JWT: Header Authorization: Bearer <token> wajib pada /write & /set_light
# - Expired session token: Token statis (simulasi) — di produksi gunakan JWT dengan exp claim
# ======
# --- KONFIGURASI KEAMANAN ---
SHARED_KEY = "RAHASIA_KAMPUS_UNTUK_DEKRIPSI"   # Kunci XOR bersama antara device dan gateway
SECURE_TOKEN = "token_aman_smartroom_2026"      # Bearer Token valid satu-satunya
DEFAULT_PASSWORD = "admin123"  # Menyimulasikan celah keamanan lama (VULNERABLE baseline)
# =======
# DONE CHECKLIST A (API Security)
# =======

# ======
# CHECKLIST A: Device Authentication
# - Device ID validation: Setiap request wajib membawa header X-Device-ID yang cocok
# - Token pairing antar device: SECURE_TOKEN dipasangkan khusus dengan DEVICE_ID "PICO-W-CLASS-A"
# ======
# ID perangkat yang sah (hanya device ini yang diizinkan menulis data)
REGISTERED_DEVICE_ID = "PICO-W-CLASS-A"
# =======
# DONE CHECKLIST A (Device Authentication)
# =======

# Konfigurasi InfluxDB Cloud (dibaca dari env var)
# - INFLUXDB_URL    : https://us-east-1-1.aws.cloud2.influxdata.com
# - INFLUXDB_TOKEN  : API token InfluxDB Cloud
# - INFLUXDB_ORG    : nama organisasi
# - INFLUXDB_BUCKET : nama bucket
_influx_base = os.environ.get("INFLUXDB_URL", "").rstrip("/")
_influx_org   = os.environ.get("INFLUXDB_ORG", "")
_influx_bucket= os.environ.get("INFLUXDB_BUCKET", "")
INFLUX_URL    = f"{_influx_base}/api/v2/write?org={_influx_org}&bucket={_influx_bucket}&precision=s"
INFLUX_TOKEN  = os.environ.get("INFLUXDB_TOKEN", "")

# --- STATE DATABASE DALAM MEMORI (IN-MEMORY) ---
failed_attempts = {}    # {ip: count} — melacak percobaan gagal per IP
blocked_ips = set()     # {blocked_ip} — daftar IP yang diblokir permanen oleh IDS
light_state = "off"     # Status lampu kampus: 'on' atau 'off'
security_mode = True    # True = Setelah Keamanan (Strict), False = Sebelum Keamanan (Lembek)

# --- DEVICE SESSION TRACKER ---
# Melacak setiap device yang login: {device_id: {"ip": str, "first_seen": datetime, "last_seen": datetime}}
# Digunakan untuk mendeteksi koneksi baru vs koneksi rutin, agar email tidak terkirim setiap 15 detik
device_sessions = {}            # {device_id: {"ip": str, "first_seen": dt, "last_seen": dt}}
DEVICE_TIMEOUT_MINUTES = 5     # Jika device tidak kirim data > 5 menit, dianggap "reconnect" saat kembali

# ======
# CHECKLIST C: Activity Logging
# - Menyimpan log: waktu login, IP address, status sukses/gagal
# - Setiap event keamanan dicatat ke file security_activity.log secara real-time
# ======
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(ROOT_DIR, "security_activity.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
# =======
# DONE CHECKLIST C (Activity Logging)
# =======

# Helper untuk mencetak log ke console dan file sekaligus
def log_event(level, ip, action, status, details):
    msg = f"IP: {ip} | ACTION: {action} | STATUS: {status} | DETAILS: {details}"
    if level == "INFO":
        logging.info(msg)
        print(f"\033[92m[INFO]\033[0m {msg}")
    elif level == "WARNING":
        logging.warning(msg)
        print(f"\033[93m[WARN]\033[0m {msg}")
    elif level == "CRITICAL":
        logging.critical(msg)
        print(f"\033[91m[CRITICAL ALARM]\033[0m {msg}")

# ======
# CHECKLIST B: Payload Encryption
# - AES encryption sederhana (implementasi menggunakan XOR Hex Cipher sebagai simulasi enkripsi ringan di MicroPython)
# - Enkripsi data sensor sebelum dikirim: Gateway mendekripsi hex payload yang dikirim device
# ======
def decrypt_payload(hex_str, key=SHARED_KEY):
    """Mendekripsi payload Hex yang dienkripsi XOR oleh device IoT."""
    try:
        cipher_bytes = bytes.fromhex(hex_str)
        decrypted = "".join(chr(b ^ ord(key[i % len(key)])) for i, b in enumerate(cipher_bytes))
        return decrypted
    except Exception as e:
        return None
# =======
# DONE CHECKLIST B (Payload Encryption)
# =======

# ======
# CHECKLIST C: Alert System
# - Discord/Telegram alert jika login gagal atau device asing terhubung
# - Alarm otomatis dikirim ke Discord Webhook saat terjadi intrusi atau IP diblokir
# ======
# Ganti dengan Webhook URL Discord asli Anda untuk mendapatkan notifikasi real-time di HP!
DISCORD_WEBHOOK_URL = ""

def send_alert_to_discord(title, description, level="HIGH"):
    """Mengirim notifikasi alert ke Discord melalui Webhook (Intrusion Detection Alert)."""
    if not DISCORD_WEBHOOK_URL:
        return
    color = 15158332 if level == "HIGH" else 3066993  # Merah (bahaya) atau Hijau (aman)
    payload = {
        "embeds": [{
            "title": f"🚨 IoT SECURITY ALERT: {title}",
            "description": description,
            "color": color,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=3)
    except Exception:
        pass
# =======
# DONE CHECKLIST C (Alert System)
# =======

# ======
# CHECKLIST C: Login Protection — Auto Block IP/Device
# - Maksimal 3 kali percobaan gagal sebelum IP diblokir permanen oleh IDS
# - Auto block IP/device: setiap request dicek apakah IP sudah masuk daftar cekal
# ======
@app.before_request
def check_intrusion():
    """Middleware IDS: cek setiap request masuk, tolak jika IP sudah diblokir."""
    ip = request.remote_addr
    # Jika IP berada di daftar cekal, tolak semua request tanpa pengecualian
    if ip in blocked_ips:
        log_event("CRITICAL", ip, request.path, "REJECTED", "Akses ditolak. IP ini telah diblokir permanen.")
        return jsonify({"error": "IP Blocked", "message": "Your IP has been blocked due to multiple security violations."}), 403
# =======
# DONE CHECKLIST C (Login Protection)
# =======

# --- ENDPOINT 1: PENGIRIMAN DATA SENSOR REAL-TIME (/write) ---
@app.route("/write", methods=["POST"])
def write_data():
    ip = request.remote_addr
    auth_header = request.headers.get("Authorization")
    
    # 1. KASUS SEBELUM KEAMANAN (Jika Modus Strict Mati atau Menggunakan Password Default)
    if not security_mode:
        log_event("WARNING", ip, "WRITE", "BYPASS", "Menerima data tanpa enkripsi/autentikasi (Mode Lama).")
        # Langsung terima payload mentah (raw text) dan forward ke InfluxDB
        raw_data = request.data.decode("utf-8")
        # Forward ke InfluxDB
        headers = {"Authorization": "Token " + INFLUX_TOKEN, "Content-Type": "text/plain"}
        res = requests.post(INFLUX_URL, headers=headers, data=raw_data)
        return "", res.status_code

    # 2. KASUS SESUDAH KEAMANAN (Strict Mode Aktif)
    # ======
    # CHECKLIST A: Device Authentication — Device ID validation
    # Cek X-Device-ID header: hanya device terdaftar yang boleh mengirim data
    # ======
    device_id = request.headers.get("X-Device-ID")
    if device_id != REGISTERED_DEVICE_ID:
        log_event("WARNING", ip, "WRITE", "REJECTED_DEVICE", f"Device ID tidak sah: '{device_id}'")
        send_email_alert(
            "🚨 WARNING: Unregistered Device Connection Attempt",
            f"Sistem mendeteksi percobaan pengiriman data oleh perangkat asing tidak dikenal.\n\nDetail Perangkat:\n- Device ID Terdeteksi: '{device_id}'\n- IP Address: {ip}\n- Waktu: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return jsonify({"error": "Unauthorized", "message": "Unknown or unregistered Device ID."}), 401
    # =======
    # DONE CHECKLIST A (Device Authentication)
    # =======

    # Cek kredensial (API Security - Checklist A)
    if not auth_header or not auth_header.startswith("Bearer "):
        # Brute force check / Invalid auth
        failed_attempts[ip] = failed_attempts.get(ip, 0) + 1
        log_event("WARNING", ip, "WRITE", "UNAUTHORIZED", f"Gagal autentikasi (Percobaan: {failed_attempts[ip]}/3)")
        
        if failed_attempts[ip] >= 3:
            blocked_ips.add(ip)
            log_event("CRITICAL", ip, "IDS_BLOCK", "BLOCKED", "IP resmi DIBLOKIR akibat percobaan ilegal berulang.")
            send_alert_to_discord(
                "IP Address Blocked!",
                f"IP `{ip}` telah diblokir secara otomatis oleh sistem deteksi intrusi setelah 3 kali gagal autentikasi.",
                level="HIGH"
            )
            send_email_alert(
                "🚨 CRITICAL: Device Brute-Force Blocked",
                f"Sistem Intrusion Detection (IDS) pada API Gateway telah MEMBLOKIR IP '{ip}' secara permanen.\n\nDetail:\n- Waktu: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n- IP Address: {ip}\n- Penyebab: Percobaan pengiriman data sensor tanpa token berulang-ulang."
            )
            return jsonify({"error": "Forbidden", "message": "Intrusion detected. Your IP is blocked."}), 403
            
        return jsonify({"error": "Unauthorized", "message": "Valid Bearer Token is required."}), 401

    token = auth_header.split(" ")[1]
    if token != SECURE_TOKEN:
        failed_attempts[ip] = failed_attempts.get(ip, 0) + 1
        log_event("WARNING", ip, "WRITE", "INVALID_TOKEN", f"Token salah. Percobaan: {failed_attempts[ip]}/3")
        if failed_attempts[ip] >= 3:
            blocked_ips.add(ip)
            log_event("CRITICAL", ip, "IDS_BLOCK", "BLOCKED", "IP resmi DIBLOKIR akibat token salah berulang.")
            send_email_alert(
                "🚨 CRITICAL: Device Token Brute-Force Blocked",
                f"Sistem Intrusion Detection (IDS) pada API Gateway telah MEMBLOKIR IP '{ip}' secara permanen.\n\nDetail:\n- Waktu: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n- IP Address: {ip}\n- Penyebab: Percobaan brute-force menggunakan token salah secara berulang-ulang."
            )
            return jsonify({"error": "Forbidden", "message": "Intrusion detected. Your IP is blocked."}), 403
        return jsonify({"error": "Unauthorized", "message": "Invalid token."}), 401

    # Token valid! Reset hitungan gagal
    failed_attempts[ip] = 0

    # ------------------------------------------------------------------
    # DEVICE LOGIN EMAIL ALERT
    # Kirim email ke alamat yang diset di halaman Settings jika:
    #   1. Device ini pertama kali terhubung sejak gateway dijalankan, ATAU
    #   2. Device ini baru reconnect setelah tidak aktif > DEVICE_TIMEOUT_MINUTES
    # Ini mencegah email terkirim setiap 15 detik (setiap siklus sensor).
    # ------------------------------------------------------------------
    now = datetime.datetime.now()
    existing_session = device_sessions.get(device_id)

    is_new_connection = existing_session is None
    is_reconnect = (
        existing_session is not None and
        (now - existing_session["last_seen"]).total_seconds() > DEVICE_TIMEOUT_MINUTES * 60
    )

    if is_new_connection or is_reconnect:
        # Tentukan label event untuk subjek email
        event_label = "Koneksi Pertama" if is_new_connection else "Reconected (setelah offline)"
        first_seen_str = (
            now.strftime("%Y-%m-%d %H:%M:%S")
            if is_new_connection
            else existing_session["first_seen"].strftime("%Y-%m-%d %H:%M:%S")
        )
        offline_since = (
            "-"
            if is_new_connection
            else existing_session["last_seen"].strftime("%Y-%m-%d %H:%M:%S")
        )

        log_event("INFO", ip, "DEVICE_LOGIN", event_label.upper(), f"Device '{device_id}' berhasil login dari IP {ip}")

        send_email_alert(
            f"📡 Device Login: {device_id} [{event_label}]",
            f"Halo Admin,\n\nSistem IoT Smart Room mendeteksi perangkat yang berhasil terautentikasi dan terhubung ke API Gateway.\n\n"
            f"{'=' * 45}\n"
            f"  DETAIL KONEKSI DEVICE\n"
            f"{'=' * 45}\n"
            f"  Device ID      : {device_id}\n"
            f"  IP Address     : {ip}\n"
            f"  Event          : {event_label}\n"
            f"  Waktu Login    : {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"  Pertama Online : {first_seen_str}\n"
            f"  Terakhir Aktif : {offline_since}\n"
            f"{'=' * 45}\n\n"
            f"Perangkat ini menggunakan Bearer Token yang valid dan Device ID terdaftar.\n"
            f"Jika Anda tidak mengenali perangkat ini, segera periksa infrastruktur Anda.\n\n"
            f"-- IoT Security Gateway, Smart Room UNJ --"
        )

    # Perbarui / buat session record untuk device ini
    if is_new_connection:
        device_sessions[device_id] = {
            "ip": ip,
            "first_seen": now,
            "last_seen": now
        }
    else:
        device_sessions[device_id]["last_seen"] = now
        device_sessions[device_id]["ip"] = ip   # update IP jika berubah (DHCP)
    # ------------------------------------------------------------------

    # Memproses payload terenkripsi
    req_json = request.get_json()
    if not req_json or "encrypted_data" not in req_json:
        log_event("WARNING", ip, "WRITE", "BAD_REQUEST", "Payload tidak memiliki format encrypted_data.")
        return jsonify({"error": "Bad Request", "message": "encrypted_data field is required."}), 400

    encrypted_hex = req_json["encrypted_data"]
    decrypted_line_protocol = decrypt_payload(encrypted_hex)

    if not decrypted_line_protocol:
        log_event("WARNING", ip, "WRITE", "DECRYPTION_FAILED", "Gagal mendekripsi payload. Kunci salah.")
        return jsonify({"error": "Decryption Failed", "message": "Could not decrypt payload."}), 400

    log_event("INFO", ip, "WRITE", "SUCCESS", f"Data sukses didekripsi: {decrypted_line_protocol}")

    # Meneruskan data bersih ke InfluxDB lokal
    try:
        headers = {
            "Authorization": "Token " + INFLUX_TOKEN,
            "Content-Type": "text/plain; charset=utf-8"
        }
        res_influx = requests.post(INFLUX_URL, headers=headers, data=decrypted_line_protocol, timeout=5)
        log_event("INFO", ip, "FORWARD", f"INFLUXDB_{res_influx.status_code}", "Sukses meneruskan data ke database.")
        # Return 200 + JSON (bukan 204) — urequests MicroPython hang pada 204 No Content
        # karena tidak ada body/Content-Length untuk menandai akhir response
        return jsonify({"status": "ok", "code": res_influx.status_code}), 200
    except Exception as e:
        log_event("CRITICAL", ip, "FORWARD", "INFLUXDB_ERROR", f"Gagal tersambung ke InfluxDB: {e}")
        return jsonify({"error": "Database Error", "message": "Could not forward to InfluxDB."}), 500


# --- ENDPOINT 2: PENGONTROL LAMPU KAMPUS (/set_light) ---
# Mensimulasikan serangan hacker yang mencoba menghidupkan seluruh lampu gedung di jam 02.00 pagi
@app.route("/set_light", methods=["POST"])
def set_light():
    global light_state
    ip = request.remote_addr
    auth_header = request.headers.get("Authorization")
    
    # 1. KASUS SEBELUM KEAMANAN
    if not security_mode:
        # Siapa pun (tanpa token) bisa menyalakan lampu
        state = request.args.get("state", "off")
        light_state = state
        log_event("WARNING", ip, "SET_LIGHT", "SUCCESS_BYPASS", f"Lampu gedung diubah menjadi {state.upper()} oleh IP luar tanpa autentikasi (Default Password aktif)!")
        send_email_alert(
            "⚠️ SECURITY BREACH: Lighting Control Bypassed",
            f"Peringatan: Lampu gedung kampus telah diubah menjadi {state.upper()} oleh IP luar {ip} tanpa autentikasi karena mode keamanan dinonaktifkan.\n\nHarap aktifkan kembali mode keamanan secepatnya!"
        )
        return jsonify({"status": "success", "light": light_state, "security": "DISABLED"})

    # 2. KASUS SESUDAH KEAMANAN
    if not auth_header or not auth_header.startswith("Bearer "):
        log_event("WARNING", ip, "SET_LIGHT", "REJECTED_UNAUTHORIZED", "Percobaan merubah lampu gedung diblokir. Tanpa Autentikasi!")
        send_email_alert(
            "🚨 WARNING: Unauthorized Control Center Bypass",
            f"Sistem mendeteksi percobaan pengubahan lampu gedung secara ilegal tanpa autentikasi.\n\nDetail:\n- IP Address: {ip}\n- Tindakan: Perubahan lampu diblokir oleh Gateway.\n- Waktu: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return jsonify({"error": "Unauthorized", "message": "Bearer Token required to control campus systems."}), 401
        
    token = auth_header.split(" ")[1]
    if token != SECURE_TOKEN:
        log_event("WARNING", ip, "SET_LIGHT", "REJECTED_INVALID_TOKEN", "Percobaan merubah lampu gedung diblokir. Token salah!")
        send_email_alert(
            "🚨 WARNING: Unauthorized Control Center Bypass (Invalid Token)",
            f"Sistem mendeteksi percobaan pengubahan lampu gedung secara ilegal dengan token salah.\n\nDetail:\n- IP Address: {ip}\n- Token dicoba: '{token}'\n- Waktu: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return jsonify({"error": "Unauthorized", "message": "Invalid token."}), 401

    # Berhasil terotentikasi
    state = request.args.get("state", "off")
    light_state = state
    log_event("INFO", ip, "SET_LIGHT", "SUCCESS_SECURE", f"Lampu gedung sukses diubah menjadi {state.upper()} oleh Admin resmi.")
    return jsonify({"status": "success", "light": light_state, "security": "ENABLED"})


# --- ENDPOINT 3: POLING COMMAND UNTUK WOKWI DEVICE (/get_command) ---
@app.route("/get_command", methods=["GET"])
def get_command():
    # Perangkat Wokwi akan memanggil ini untuk mengetahui apakah harus menyalakan lampu atau tidak
    return jsonify({"light": light_state})


# --- ENDPOINT 4: STATUS SEMUA DEVICE YANG PERNAH LOGIN (/device_sessions) ---
@app.route("/device_sessions", methods=["GET"])
def get_device_sessions():
    """Mengembalikan daftar semua device yang pernah login beserta waktu aktif terakhirnya."""
    result = {}
    now = datetime.datetime.now()
    for dev_id, sess in device_sessions.items():
        elapsed = (now - sess["last_seen"]).total_seconds()
        result[dev_id] = {
            "ip": sess["ip"],
            "first_seen": sess["first_seen"].strftime("%Y-%m-%d %H:%M:%S"),
            "last_seen": sess["last_seen"].strftime("%Y-%m-%d %H:%M:%S"),
            "status": "online" if elapsed < DEVICE_TIMEOUT_MINUTES * 60 else "offline",
            "seconds_since_last_ping": int(elapsed)
        }
    return jsonify(result)


# --- ENDPOINT TAMBAHAN: SWITCH SECURITY MODE (Untuk Simulasi Presentasi) ---
@app.route("/toggle_security", methods=["POST"])
def toggle_security():
    global security_mode
    security_mode = not security_mode
    status_str = "AKTIF" if security_mode else "MATI"
    log_event("INFO", request.remote_addr, "TOGGLE_SECURITY", "CHANGED", f"Mode Keamanan diubah menjadi {status_str}")
    return jsonify({"security_mode": security_mode, "status": f"Keamanan IoT {status_str}"})


# --- ENDPOINT TAMBAHAN: UNBLOCK ALL IPS (Untuk Reset Pengujian) ---
@app.route("/unblock_ips", methods=["POST"])
def unblock_ips():
    global blocked_ips, failed_attempts
    blocked_ips.clear()
    failed_attempts.clear()
    log_event("INFO", request.remote_addr, "UNBLOCK_IPS", "RESET", "Semua daftar blokir IP dibersihkan.")
    return jsonify({"status": "reset", "message": "All blocked IPs cleared."})


if __name__ == "__main__":
    print("-" * 50)
    print("🛡️  IoT SECURITY API GATEWAY SEDANG BERJALAN...")
    print("📂 Log aktivitas forensik disimpan di: security_activity.log")
    print("📍 Port: 5000 | Mengamankan Database InfluxDB dan Kontrol Lampu")
    print("-" * 50)
    app.run(host="0.0.0.0", port=5000, debug=False)
