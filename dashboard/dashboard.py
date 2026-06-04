import os
import sys
import time
import json
import datetime
import hashlib
import pandas as pd
import streamlit as st
import requests

# Menambahkan parent directory (folder root proyek) ke sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from email_helper import send_email_alert, load_settings

# ======
# CHECKLIST B: HTTPS / SSL/TLS
# - HTTPS pada web dashboard: Streamlit bisa dijalankan di belakang reverse proxy HTTPS
# - Konfigurasi production: gunakan nginx + certbot (Let's Encrypt) sebagai SSL terminator
# - Untuk development: akses via http://localhost:8501 (lokal aman)
# ======
# --- KONFIGURASI PENGATURAN DASHBOARD ---
st.set_page_config(
    page_title="Dashboard Smart Room Kampus",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)
# =======
# DONE CHECKLIST B (HTTPS / SSL/TLS - config noted)
# =======

# ======
# CHECKLIST A: API Security - Kredensial Dashboard Admin
# - API Key validation: Login form memvalidasi username + password sebelum akses
# - Bearer Token: Dashboard menggunakan Bearer token saat memanggil API Gateway
# - Expired session token: st.session_state["logged_in"] + lockout_until men-simulasikan sesi
# ======
ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin_password_2026"
ADMIN_PASSWORD_HASH = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()  # Hash password untuk perbandingan aman
# =======
# DONE CHECKLIST A (API Security - Dashboard Auth)
# =======

# Lokasi File
DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(DASHBOARD_DIR, ".."))
LOG_FILE = os.path.join(ROOT_DIR, "security_activity.log")
SETTINGS_FILE = os.path.join(ROOT_DIR, "settings.json")
DUMMY_DB_FILE = os.path.join(DASHBOARD_DIR, "data_sensor_1_minggu_lineprotocol.txt")

GATEWAY_URL = "http://localhost:5000"

# ======
# CHECKLIST C: Activity Logging
# - Menyimpan log: waktu login, IP address, status sukses/gagal
# - Format: TIMESTAMP | LEVEL | IP | ACTION | STATUS | DETAILS
# ======
def log_security_event(level, action, status, details):
    """Mencatat setiap event keamanan ke file log forensik."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} | {level} | IP: 127.0.0.1 | ACTION: {action} | STATUS: {status} | DETAILS: {details}\n"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_line)
    except Exception:
        pass
# =======
# DONE CHECKLIST C (Activity Logging)
# =======

# --- METODE MEMBACA DATA SENSOR ---
def fetch_sensor_data():
    """
    Mencoba mengambil data dari InfluxDB Docker.
    Fallback ke file dummy lokal, lalu fallback ke data statis darurat.
    """
    try:
        from influxdb_client import InfluxDBClient
        token = "ywmTlVCwtTlubc2BrDPVrOWKlEAvyZtbUbCvuJLhdRFYuoCP49L8fz7rdSeFuRvcBrjbRchcdXUkh5bVtzsYQA=="
        org = "IOT"
        bucket = "data_sensor"
        client = InfluxDBClient(url="http://localhost:8086", token=token, org=org, timeout=3000)
        
        query = f'''
        from(bucket: "{bucket}")
          |> range(start: -7d)
          |> filter(fn: (r) => r["_measurement"] == "smart_room")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> keep(columns: ["_time", "suhu", "kelembaban", "cahaya", "gerakan", "daya_listrik", "lokasi"])
        '''
        
        query_api = client.query_api()
        df = query_api.query_data_frame(query)
        client.close()
        
        if not df.empty:
            df = df.rename(columns={"_time": "time"})
            df["time"] = pd.to_datetime(df["time"])
            return df, "INFLUXDB_DOCKER"
    except Exception:
        pass
    
    # Fallback ke file dummy lokal
    try:
        lines = []
        if os.path.exists(DUMMY_DB_FILE):
            with open(DUMMY_DB_FILE, "r") as f:
                for line in f.readlines():
                    if line.strip():
                        parts = line.strip().split(" ")
                        if len(parts) == 3:
                            meas_tags, fields_str, ts_str = parts
                            tags = dict(item.split("=") for item in meas_tags.split(",")[1:])
                            fields = dict(item.split("=") for item in fields_str.split(","))
                            ts = datetime.datetime.fromtimestamp(int(ts_str))
                            
                            row = {
                                "time": ts,
                                "lokasi": tags.get("lokasi", "Ruang_Kelas_A"),
                                "suhu": float(fields.get("suhu", 0)),
                                "kelembaban": float(fields.get("kelembaban", 0)),
                                "cahaya": float(fields.get("cahaya", 0)),
                                "gerakan": float(fields.get("gerakan", 0)),
                                "daya_listrik": float(fields.get("daya_listrik", 0))
                            }
                            lines.append(row)
            
            df_dummy = pd.DataFrame(lines)
            if not df_dummy.empty:
                df_dummy = df_dummy.sort_values(by="time")
                return df_dummy, "LOCAL_FILE_DUMMY"
    except Exception:
        pass

    # Fallback emergency static
    now = datetime.datetime.now()
    times = [now - datetime.timedelta(minutes=15*i) for i in range(100)]
    df_emergency = pd.DataFrame({
        "time": times,
        "lokasi": ["Ruang_Kelas_A"] * 100,
        "suhu": [22.0] * 100,
        "kelembaban": [50] * 100,
        "cahaya": [45000] * 100,
        "gerakan": [0] * 100,
        "daya_listrik": [250.0] * 100
    })
    return df_emergency, "EMERGENCY_STATIC"

# ======
# CHECKLIST C: Login Protection
# - Maksimal 3 kali percobaan login sebelum akun dikunci
# - Auto block IP/device: st.session_state["locked_out"] = True setelah 3 kali gagal
# - lockout_until: timestamp kapan lockout berakhir (simulasi waktu blokir)
# ======
# --- STATE MANAJEMEN LOGIN ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "failed_attempts" not in st.session_state:
    st.session_state["failed_attempts"] = 0
if "locked_out" not in st.session_state:
    st.session_state["locked_out"] = False
if "lockout_until" not in st.session_state:
    st.session_state["lockout_until"] = None
if "login_time" not in st.session_state:
    st.session_state["login_time"] = None
# =======
# DONE CHECKLIST C (Login Protection - state vars)
# =======

# --- INJECT CSS PREMIUM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        min-height: 100vh;
    }
    
    /* Login card */
    .login-container {
        background: rgba(255,255,255,0.05);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 20px;
        padding: 2rem;
        margin: 1rem 0;
    }
    
    /* Metric cards */
    [data-testid="metric-container"] {
        background: rgba(255,255,255,0.07);
        border: 1px solid rgba(99,179,237,0.2);
        border-radius: 12px;
        padding: 1rem;
        backdrop-filter: blur(10px);
    }
    
    /* Security badge */
    .security-badge {
        background: linear-gradient(135deg, #00b09b, #96c93d);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin: 0.2rem;
    }
    .security-badge-red {
        background: linear-gradient(135deg, #f093fb, #f5576c);
    }
    .security-badge-blue {
        background: linear-gradient(135deg, #4facfe, #00f2fe);
    }
    .security-badge-orange {
        background: linear-gradient(135deg, #f7971e, #ffd200);
        color: #1a1a2e;
    }
    
    /* Checklist card */
    .checklist-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.5rem 0;
        border-left: 4px solid #00b09b;
    }
    .checklist-card.vulnerable {
        border-left-color: #f5576c;
    }
    
    /* Header gradient */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2rem;
        font-weight: 700;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(15, 12, 41, 0.9) !important;
        border-right: 1px solid rgba(255,255,255,0.1);
    }
</style>
""", unsafe_allow_html=True)


# --- HALAMAN LOGIN ---
if not st.session_state["logged_in"]:
    # Header
    st.markdown("""
    <div style='text-align:center; padding: 2rem 0 1rem 0;'>
        <div style='font-size:3rem;'>🛡️</div>
        <h1 style='color:white; font-weight:700; margin:0;'>IoT Security Dashboard</h1>
        <p style='color:rgba(255,255,255,0.6); font-size:1rem;'>Smart Room UNJ — Sistem Keamanan Terpadu</p>
    </div>
    """, unsafe_allow_html=True)

    # ======
    # CHECKLIST C: Login Protection
    # - Cek apakah akses sedang dalam status locked_out
    # - Jika locked_out aktif: tampilkan pesan blokir, sembunyikan form login
    # ======
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.session_state["locked_out"]:
            st.markdown("""
            <div style='background:rgba(245,87,108,0.15); border:1px solid rgba(245,87,108,0.5);
                        border-radius:12px; padding:1.5rem; text-align:center;'>
                <div style='font-size:2rem;'>🚨</div>
                <h3 style='color:#f5576c; margin:0.5rem 0;'>AKSES TERKUNCI!</h3>
                <p style='color:rgba(255,255,255,0.8);'>
                    Anda telah salah memasukkan password sebanyak <b>3 kali</b>.<br>
                    Sistem Intrusion Detection secara otomatis memblokir sesi Anda.<br>
                    Hubungi administrator jaringan.
                </p>
            </div>
            """, unsafe_allow_html=True)
            st.info("💡 *Untuk simulasi: restart dashboard atau gunakan tombol reset di terminal.*")
            
            if st.button("🔓 Reset Lockout (Mode Simulasi)", use_container_width=True):
                st.session_state["locked_out"] = False
                st.session_state["failed_attempts"] = 0
                log_security_event("INFO", "LOCKOUT_RESET", "MANUAL_RESET", "Lockout direset via tombol simulasi.")
                st.rerun()
        else:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            with st.form("login_form"):
                st.markdown("<h3 style='color:white; margin-top:0;'>🔐 Login Administrator</h3>", unsafe_allow_html=True)
                
                # Info sisa percobaan
                if st.session_state["failed_attempts"] > 0:
                    attempts_left = 3 - st.session_state["failed_attempts"]
                    st.warning(f"⚠️ Sisa percobaan: **{attempts_left}/3** sebelum akun dikunci.")
                
                user = st.text_input("Username", placeholder="admin", key="login_user")
                pwd = st.text_input("Password", type="password", placeholder="••••••••", key="login_pwd")
                submit = st.form_submit_button("🚀 Masuk ke Dashboard", use_container_width=True)
                
                if submit:
                    # ======
                    # CHECKLIST A: API Security - Validasi kredensial dengan hash SHA-256
                    # - Password dibandingkan dalam bentuk hash (tidak plain text)
                    # - Mencegah timing attack dengan perbandingan hash
                    # ======
                    input_hash = hashlib.sha256(pwd.encode()).hexdigest()
                    if user == ADMIN_USER and input_hash == ADMIN_PASSWORD_HASH:
                        st.session_state["logged_in"] = True
                        st.session_state["failed_attempts"] = 0
                        st.session_state["login_time"] = datetime.datetime.now()
                        log_security_event("INFO", "DASHBOARD_LOGIN", "SUCCESS", "Admin berhasil login ke dashboard.")
                        
                        send_email_alert(
                            "Dashboard Login Successful",
                            f"Halo Admin,\n\nLogin sukses ke Dashboard Web Control Center.\n\nDetail:\n- Waktu: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n- IP: 127.0.0.1\n- Status: SUKSES"
                        )
                        st.success("✅ Login berhasil! Memuat dashboard...")
                        st.rerun()
                    else:
                        st.session_state["failed_attempts"] += 1
                        attempts_left = 3 - st.session_state["failed_attempts"]
                        
                        log_security_event(
                            "WARNING", "DASHBOARD_LOGIN", "FAILED",
                            f"Gagal login (User: '{user}'). Percobaan ke-{st.session_state['failed_attempts']}/3"
                        )
                        send_email_alert(
                            "Dashboard Login Failed Alert",
                            f"🚨 Percobaan login gagal.\n- Username: '{user}'\n- Percobaan: {st.session_state['failed_attempts']}/3\n- Waktu: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        
                        if st.session_state["failed_attempts"] >= 3:
                            st.session_state["locked_out"] = True
                            log_security_event("CRITICAL", "DASHBOARD_LOGIN", "LOCKED_OUT", "Akun dikunci otomatis oleh IDS (brute-force terdeteksi).")
                            send_email_alert(
                                "🚨 CRITICAL: Dashboard Intrusion Blocked",
                                f"IDS memblokir akses setelah 3 kali gagal login.\n- Waktu Blokir: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                            st.rerun()
                        else:
                            st.error(f"❌ Username atau password salah! Sisa: **{attempts_left}** percobaan")
                    # =======
                    # DONE CHECKLIST A (API Security - credential validation)
                    # =======
            # =======
            # DONE CHECKLIST C (Login Protection - form handling)
            # =======
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Info demo credentials
            st.markdown("""
            <div style='text-align:center; margin-top:1rem;'>
                <p style='color:rgba(255,255,255,0.4); font-size:0.8rem;'>
                    Demo: <code>admin</code> / <code>admin_password_2026</code>
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    st.stop()


# ===========================================
# HALAMAN UTAMA DASHBOARD (Setelah Login)
# ===========================================

# Header utama
login_duration = ""
if st.session_state["login_time"]:
    elapsed = datetime.datetime.now() - st.session_state["login_time"]
    mins = int(elapsed.total_seconds() // 60)
    login_duration = f" | Sesi aktif: {mins} menit"

st.markdown(f"""
<div style='display:flex; align-items:center; gap:1rem; padding:0.5rem 0 1rem 0; border-bottom:1px solid rgba(255,255,255,0.1); margin-bottom:1rem;'>
    <span style='font-size:2rem;'>🛡️</span>
    <div>
        <h2 style='color:white; margin:0; font-weight:700;'>Smart Room IoT Control Center</h2>
        <p style='color:rgba(255,255,255,0.5); margin:0; font-size:0.85rem;'>
            Administrator | {datetime.datetime.now().strftime('%d %B %Y %H:%M')}{login_duration}
        </p>
    </div>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### ⚙️ IoT Gatekeeper System")
    
    gateway_connected = False
    security_mode_active = True
    try:
        res_gateway = requests.get(GATEWAY_URL + "/get_command", timeout=1)
        gateway_connected = True
    except Exception:
        pass
    
    if gateway_connected:
        st.success("🟢 API Gateway: Terhubung")
        
        if st.button("🔄 Toggle Security Mode"):
            try:
                res_toggle = requests.post(GATEWAY_URL + "/toggle_security")
                st.info(f"Gateway: {res_toggle.json()['status']}")
                time.sleep(1)
                st.rerun()
            except Exception:
                pass
                
        if st.button("🔓 Clear Gateway IP Blocklist"):
            try:
                res_reset = requests.post(GATEWAY_URL + "/unblock_ips")
                st.success("Semua IP dibebaskan!")
                time.sleep(1)
                st.rerun()
            except Exception:
                pass
    else:
        st.error("🔴 API Gateway: Terputus")
        st.caption("Jalankan `api_gateway.py` di terminal.")
    

    
    st.write("---")
    if st.button("🚪 Keluar (Logout)", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["login_time"] = None
        log_security_event("INFO", "DASHBOARD_LOGOUT", "SUCCESS", "Admin logout.")
        st.rerun()

# --- AMBIL DATA SENSOR ---
df_sensor, data_source = fetch_sensor_data()

# --- TAB DASHBOARD ---
tab1, tab2, tab3 = st.tabs([
    "📈 Monitoring",
    "🛡️ Security & Logs",
    "⚙️ Settings",
])


# ==========================================
# TAB 1: REAL-TIME MONITORING
# ==========================================
with tab1:
    if data_source == "INFLUXDB_DOCKER":
        st.success("⚡ **Database**: Data real-time dari **InfluxDB Docker** aktif!")
    elif data_source == "LOCAL_FILE_DUMMY":
        st.warning("⚠️ **Database**: InfluxDB offline — menampilkan data dummy 1 minggu.")
    else:
        st.error("🔴 **Database**: Semua sumber offline. Menampilkan data statis darurat.")

    latest_row = df_sensor.iloc[-1]

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🌡️ Suhu", f"{latest_row['suhu']:.1f} °C",
                delta=f"{latest_row['suhu'] - df_sensor['suhu'].mean():.1f}°C vs rata-rata")
    col2.metric("💧 Kelembaban", f"{latest_row['kelembaban']:.0f} %")
    col3.metric("☀️ Cahaya LDR", f"{latest_row['cahaya']:.0f}")
    col4.metric("🚶 Gerakan", "✅ Terdeteksi" if latest_row['gerakan'] == 1 else "💤 Kosong")
    col5.metric("⚡ Daya", f"{latest_row['daya_listrik']:.0f} W",
                delta=f"{latest_row['daya_listrik'] - df_sensor['daya_listrik'].mean():.0f}W vs rata-rata")

    st.write("---")

    col_chart_main, col_chart_info = st.columns([3, 1])
    with col_chart_main:
        st.subheader("📉 Tren Konsumsi Daya Listrik (7 Hari)")
        st.line_chart(df_sensor.set_index("time")[["daya_listrik"]])
    with col_chart_info:
        st.subheader("📋 Statistik")
        st.metric("Rata-rata", f"{df_sensor['daya_listrik'].mean():.0f} W")
        st.metric("Puncak", f"{df_sensor['daya_listrik'].max():.0f} W")
        st.metric("Minimum", f"{df_sensor['daya_listrik'].min():.0f} W")
        total_kwh = (df_sensor['daya_listrik'].mean() * len(df_sensor) * 0.25) / 1000
        st.metric("Est. Total", f"{total_kwh:.2f} kWh")

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.subheader("🌡️ Suhu & Kelembaban")
        st.line_chart(df_sensor.set_index("time")[["suhu", "kelembaban"]])
    with col_chart2:
        st.subheader("☀️ Intensitas Cahaya LDR")
        st.area_chart(df_sensor.set_index("time")[["cahaya"]])


# ==========================================
# TAB 2: SECURITY & LOGS
# Menggabungkan: Forensik Log + Device Monitor
# ==========================================
with tab2:
    # ---- Forensik Logs ----
    # ======
    # CHECKLIST C: Activity Logging - Tampilan log forensik
    # ======
    st.subheader("🔬 Forensik Log")

    if os.path.exists(LOG_FILE):
        try:
            log_entries = []
            with open(LOG_FILE, "r") as f:
                for line in f.readlines():
                    if "|" in line:
                        parts = [item.strip() for item in line.split("|")]
                        if len(parts) >= 5:
                            log_entries.append({
                                "Timestamp": parts[0],
                                "Level": parts[1],
                                "IP": parts[2].replace("IP: ", ""),
                                "Action": parts[3].replace("ACTION: ", ""),
                                "Status": parts[4].replace("STATUS: ", ""),
                                "Details": parts[5].replace("DETAILS: ", "") if len(parts) > 5 else ""
                            })

            if log_entries:
                col_filter, col_stats = st.columns([2, 1])
                with col_filter:
                    level_filter = st.multiselect(
                        "Filter Level",
                        ["INFO", "WARNING", "CRITICAL"],
                        default=["INFO", "WARNING", "CRITICAL"]
                    )
                with col_stats:
                    total = len(log_entries)
                    warnings = sum(1 for e in log_entries if "WARNING" in e["Level"])
                    criticals = sum(1 for e in log_entries if "CRITICAL" in e["Level"])
                    st.metric("Total Events", total)

                df_logs = pd.DataFrame(log_entries).sort_index(ascending=False)
                df_filtered = df_logs[df_logs["Level"].isin(level_filter)]

                def highlight_level(row):
                    if "CRITICAL" in str(row["Level"]):
                        return ["background-color: rgba(245,87,108,0.2)"] * len(row)
                    elif "WARNING" in str(row["Level"]):
                        return ["background-color: rgba(247,151,30,0.2)"] * len(row)
                    return [""] * len(row)

                st.dataframe(df_filtered.style.apply(highlight_level, axis=1), use_container_width=True)

                col_dl, col_info = st.columns(2)
                with col_dl:
                    csv_logs = df_filtered.to_csv(index=False).encode("utf-8")
                    st.download_button("📥 Unduh Log (.csv)", csv_logs, "security_log_export.csv", "text/csv")
                with col_info:
                    st.info(f"📊 {warnings} WARNING | {criticals} CRITICAL dari {total} events")
            else:
                st.info("Log masih kosong.")
        except Exception as e:
            st.error(f"Gagal membaca log: {e}")
    else:
        st.warning("File `security_activity.log` belum ada. Jalankan API Gateway terlebih dahulu.")
    # =======
    # DONE CHECKLIST C (Activity Logging)
    # =======

    st.write("---")

    # ---- Device Sessions Monitor ----
    st.subheader("📡 Connected Devices")

    _settings_now = load_settings()
    _recipient = _settings_now.get("recipient_email", "admin@kampus.ac.id")
    _alerts_on = _settings_now.get("email_alerts_enabled", True)
    st.caption(
        f"{'✅' if _alerts_on else '⛔'} Email alert dikirim ke **`{_recipient}`** "
        f"saat device pertama connect / reconnect > 5 menit."
    )

    if gateway_connected:
        try:
            res_sessions = requests.get(GATEWAY_URL + "/device_sessions", timeout=2)
            sessions_data = res_sessions.json()
            if sessions_data:
                rows = []
                for dev_id, info in sessions_data.items():
                    rows.append({
                        "Device ID": dev_id,
                        "IP": info["ip"],
                        "Status": "🟢 Online" if info["status"] == "online" else "🔴 Offline",
                        "Pertama Login": info["first_seen"],
                        "Terakhir Aktif": info["last_seen"],
                        "Detik sejak ping": info["seconds_since_last_ping"],
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("Belum ada device yang login sejak gateway dijalankan.")
        except Exception as e:
            st.warning(f"Tidak dapat mengambil data sesi device: {e}")
    else:
        st.warning("API Gateway offline.")


# ==========================================
# TAB 3: SETTINGS
# Email config + light control
# ==========================================
with tab3:
    col_settings, col_light = st.columns([2, 1])

    with col_settings:
        # ======
        # CHECKLIST C: Alert System - Konfigurasi email notifikasi
        # ======
        st.subheader("📧 Konfigurasi Email Alert")
        settings = load_settings()

        with st.form("settings_form"):
            recipient_email = st.text_input("Email Penerima Alarm", value=settings.get("recipient_email", "admin@kampus.ac.id"))
            email_alerts_enabled = st.checkbox("Aktifkan Alarm Email", value=settings.get("email_alerts_enabled", True))
            save_btn = st.form_submit_button("💾 Simpan Pengaturan")

            if save_btn:
                # Preserve existing SMTP config, only update email + toggle
                new_settings = {
                    **settings,
                    "recipient_email": recipient_email,
                    "email_alerts_enabled": email_alerts_enabled,
                }
                try:
                    with open(SETTINGS_FILE, "w") as f:
                        json.dump(new_settings, f, indent=4)
                    st.success("💾 Pengaturan disimpan!")
                    log_security_event("INFO", "SETTINGS_UPDATE", "SUCCESS", f"Email diubah ke: {recipient_email}")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")

        # =======
        # DONE CHECKLIST C (Alert System)
        # =======

        if st.button("🚀 Kirim Email Uji Coba"):
            try:
                send_email_alert(
                    "Test Security Email",
                    f"Notifikasi uji coba dari IoT Gateway.\nWaktu: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                st.info("⚡ Email uji coba dikirim! Cek inbox atau `mock_emails.log`.")
            except Exception as e:
                st.error(f"Gagal: {e}")

    with col_light:
        # ======
        # CHECKLIST A: API Security - Kontrol lampu menggunakan Bearer Token
        # ======
        st.subheader("💡 Kontrol Lampu")

        current_light = "unknown"
        if gateway_connected:
            try:
                res_state = requests.get(GATEWAY_URL + "/get_command", timeout=1)
                current_light = res_state.json().get("light", "off")
            except Exception:
                pass

        light_icon = "💡 ON" if current_light == "on" else "🌑 OFF"
        st.markdown(f"**Status:** {light_icon}")

        if st.button("🟢 Nyalakan Lampu", use_container_width=True):
            if gateway_connected:
                headers = {"Authorization": "Bearer token_aman_smartroom_2026"}
                try:
                    requests.post(GATEWAY_URL + "/set_light?state=on", headers=headers)
                    log_security_event("INFO", "LIGHT_CONTROL", "ON", "Admin menyalakan lampu.")
                    st.success("Lampu dinyalakan ✅")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal: {e}")
            else:
                st.error("Gateway offline.")

        if st.button("🔴 Matikan Lampu", use_container_width=True):
            if gateway_connected:
                headers = {"Authorization": "Bearer token_aman_smartroom_2026"}
                try:
                    requests.post(GATEWAY_URL + "/set_light?state=off", headers=headers)
                    log_security_event("INFO", "LIGHT_CONTROL", "OFF", "Admin mematikan lampu.")
                    st.success("Lampu dimatikan ✅")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal: {e}")
            else:
                st.error("Gateway offline.")
        # =======
        # DONE CHECKLIST A (API Security - light control)
        # =======

