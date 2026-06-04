# 🛡️ IoT Smart Room Security — Lembar Kerja 5

> **Sistem Keamanan IoT Terintegrasi** untuk Smart Room Kampus UNJ  
> Berbasis Raspberry Pi Pico W (Wokwi) + API Gateway + InfluxDB + Streamlit Dashboard

---

## 📋 Daftar Isi

- [Skenario Kasus](#-skenario-kasus)
- [1. Arsitektur Sistem](#1-arsitektur-sistem)
  - [Sebelum Keamanan (Vulnerable)](#-sebelum-keamanan-vulnerable)
  - [Sesudah Keamanan (Secured)](#-sesudah-keamanan-secured)
  - [Alur Autentikasi & Komunikasi Aman](#-alur-autentikasi--komunikasi-aman)
- [2. Bukti Implementasi](#2-bukti-implementasi)
  - [Sebelum Keamanan](#sebelum-keamanan)
  - [Sesudah Keamanan](#sesudah-keamanan)
- [3. Dokumentasi Teknis](#3-dokumentasi-teknis)
  - [Teknologi yang Digunakan](#teknologi-yang-digunakan)
  - [Konfigurasi Keamanan](#konfigurasi-keamanan)
  - [Potongan Kode Penting](#potongan-kode-penting)
  - [Hasil Pengujian](#hasil-pengujian)
- [Cara Menjalankan](#-cara-menjalankan)

---

## 🌌 Skenario Kasus

> Pukul **02:00 dini hari**, seluruh lampu gedung kampus menyala secara bersamaan tanpa perintah operator karena:
> - Password default `admin123` masih aktif
> - Broker MQTT diserang brute-force
> - Sensor IoT mengirimkan data tanpa autentikasi apapun
>
> **Misi:** Sebagai *Cyber Security Engineer IoT*, amankan komunikasi data, hentikan akses ilegal, deteksi penyusup, dan tampilkan monitoring real-time pada Dashboard Streamlit.

---

## 1. Arsitektur Sistem

###  Sebelum Keamanan 

```mermaid
graph TD
    PicoW["🤖 Wokwi Pico W\n(Firmware: main.py)"]
    InfluxDB[("🗄️ InfluxDB :8086\nDocker Container")]
    Hacker["💀 Hacker\n(IP Asing)"]
    Lampu["💡 Lampu Gedung"]

    PicoW -->|"❌ HTTP Plain Text\nPassword: admin123\nNo Token / No Encryption"| InfluxDB
    Hacker -->|"❌ Direct Access\nNo Auth Required\nPOST /set_light?state=on"| Lampu

    style PicoW fill:#374151,color:#fff,stroke:#6b7280
    style InfluxDB fill:#7c2d12,color:#fff,stroke:#ef4444
    style Hacker fill:#7f1d1d,color:#fff,stroke:#ef4444
    style Lampu fill:#713f12,color:#fff,stroke:#f59e0b
```

**Kelemahan yang ada:**
| # | Kerentanan | Dampak |
|---|-----------|--------|
| 1 | HTTP tanpa enkripsi | Data sensor bisa di-sniffing siapapun |
| 2 | Password default `admin123` | Mudah ditebak, tidak aman |
| 3 | Tidak ada validasi token | Siapapun bisa mengirim data palsu |
| 4 | Tidak ada Device ID | Device asing bisa menyambung |
| 5 | Tidak ada IDS | Brute-force tidak terdeteksi |
| 6 | Kontrol lampu tanpa auth | Hacker bisa nyalakan lampu kapanpun |

---

### 🛡️ Sesudah Keamanan (Secured)

```mermaid
graph TD
    PicoW["IOT"]
    Pinggy["HTTPS \nSSL/TLS Termination"]
    Gateway["API Gateway\nIDS + Auth + Decrypt"]
    InfluxDB[("Database")]
    Dashboard["Dashboard\nLogin Protected"]
    Admin["Admin\nBrowser"]
    Hacker["Hacker / Attack Simulator"]
    Email["Email Alert"]

    PicoW -->|"1️⃣ HTTPS POST\nBearer Token + Device ID\nXOR Hex Encrypted Payload"| Pinggy
    Pinggy -->|"2️⃣ Forward ke lokal"| Gateway
    Gateway -->|"3️⃣ Dekripsi + Validasi\nInflux Line Protocol"| InfluxDB
    InfluxDB -->|"4️⃣ Query 7 hari terakhir"| Dashboard
    Admin -->|"5️⃣ Login SHA-256\nSession Lockout 3x"| Dashboard
    Hacker -->|"6️⃣ Serangan Brute-force\nToken / No Auth"| Gateway
    Gateway -->|"7️⃣ Block IP setelah 3x\n+ Email Alert"| Email
    Gateway -->|"❌ HTTP 401/403\nAkses Ditolak"| Hacker

    style PicoW fill:#1e3a5f,color:#fff,stroke:#3b82f6
    style Pinggy fill:#14532d,color:#fff,stroke:#22c55e
    style Gateway fill:#3b0764,color:#fff,stroke:#a855f7
    style InfluxDB fill:#164e63,color:#fff,stroke:#06b6d4
    style Dashboard fill:#1e3a5f,color:#fff,stroke:#3b82f6
    style Admin fill:#14532d,color:#fff,stroke:#22c55e
    style Hacker fill:#7f1d1d,color:#fff,stroke:#ef4444
    style Email fill:#78350f,color:#fff,stroke:#f59e0b
```

---

### 🔐 Alur Autentikasi & Komunikasi Aman

```mermaid
sequenceDiagram
    participant D as 🤖 Wokwi(Device)
    participant P as 🔒 (HTTPS)
    participant G as 🛡️ API Gateway
    participant I as 🗄️ Database
    participant E as 📧 Email Alert

    Note over D,I: ALUR KONEKSI NORMAL 

    D->>D: 1. Baca sensor (suhu, kelembaban, cahaya, gerakan)
    D->>D: 2. Format Line Protocol
    D->>D: 3. Enkripsi XOR Hex Cipher<br/>plain → "4a3f7c1b..."
    D->>P: 4. HTTPS POST /write<br/>Header: Authorization: Bearer token_aman_smartroom_2026<br/>Header: X-Device-ID: PICO-W-CLASS-A<br/>Body: {"encrypted_data": "4a3f7c1b..."}
    P->>G: 5. Forward via TLS tunnel
    G->>G: 6. Cek X-Device-ID == "PICO-W-CLASS-A" ✅
    G->>G: 7. Cek Bearer Token valid ✅
    G->>G: 8. Dekripsi XOR Hex → Line Protocol
    G->>E: 9. Email: "Device PICO-W-CLASS-A login" (hanya first connect / reconnect)
    G->>I: 10. POST Line Protocol ke DB
    I-->>G: HTTP 204 No Content ✅
    G-->>D: HTTP 204 No Content ✅

    Note over D,I: ALUR SERANGAN (BRUTE-FORCE)

    participant H as 💀 Hacker

    H->>G: POST /write Bearer: admin123 [Percobaan 1]
    G-->>H: HTTP 401 Unauthorized ❌
    H->>G: POST /write Bearer: password_dosen [Percobaan 2]
    G-->>H: HTTP 401 Unauthorized ❌
    H->>G: POST /write Bearer: token_palsu [Percobaan 3]
    G->>G: 3x gagal → Tambah IP ke blocked_ips
    G->>E: 🚨 Email CRITICAL: IP Diblokir Permanen!
    G-->>H: HTTP 403 Forbidden — IP BLOCKED ❌

    Note over D,I:  ALUR LOGIN DASHBOARD 

    participant A as 👨‍💼 Admin Browser

    A->>A: Buka dashboard
    A->>A: Input: login credential
    A->>A: SHA-256 hash password
    A->>A: Bandingkan hash ✅
    A->>E: Email: "Login Dashboard Successful"
    A->>A: Session aktif → Akses penuh dashboard
```

**Penjelasan Alur (Tabel Ringkasan):**

| Fase | Pelaku (Aktor) | Deskripsi Langkah | Hasil / Status |
| --- | --- | --- | --- |
| **Koneksi Normal** | Device (Pico W) | Membaca sensor, memformat, & mengenkripsi data (XOR Hex). Mengirim data via HTTPS POST disertai *Bearer Token* & *Device-ID*. | Data aman dari *sniffing*. |
| | API Gateway | Memvalidasi token & ID. Mendekripsi data Hex. Mengirim Email notifikasi (jika device baru *login*). | Validasi Sukses ✅ |
| | Database | Menerima data bersih dari Gateway dan menyimpannya. | HTTP 204 No Content ✅ |
| **Serangan Brute-Force**| Hacker | Mengirim data berulang dengan menebak token sembarangan (misal: `admin123`). | Ditolak (401 Unauthorized) ❌ |
| | API Gateway | Menghitung gagal *login*. Pada kegagalan ke-3, Firewall (IDS) memblokir permanen IP penyerang dan melapor ke Admin. | **IP Terblokir (403 Forbidden) 🚫** + Email Peringatan 🚨 |
| **Login Dashboard** | Admin | Memasukkan kredensial di Web, lalu diverifikasi menggunakan *hash* SHA-256. | Akses Sesi Terbuka ✅ + Email Login Sukses 📧 |

---

### 🛡️ Penjelasan Skenario Pengujian (Attack Simulator)

Script `attack_simulator.py` digunakan untuk mendemonstrasikan bahwa lapisan keamanan yang telah diimplementasikan benar-benar bekerja.

**A. Pengujian Akses Ilegal (Nyalakan Lampu Tanpa Token)**
1. **Skenario:** Menguji apakah peretas dapat mengubah kondisi lampu kampus secara paksa tanpa hak akses. Simulator akan menembak *endpoint* `POST /set_light` tanpa menyertakan *header Authorization* sama sekali.
2. **Hasil yang Diharapkan:** Gateway mendeteksi tidak adanya token. Akses langsung diblokir (*HTTP 401 Unauthorized*), aktivitas dicatat dalam log forensik, dan lampu kampus tetap aman.

**B. Pengujian Serangan Brute-Force Token (Intrusion Detection)**
1. **Skenario:** Menguji kepekaan sistem IDS (*Intrusion Detection System*) Gateway. Simulator akan berperan sebagai *Hacker* yang menjalankan skrip pembobolan otomatis, mengirimkan 4 token tebakan (`admin123`, `password_dosen`, dll) secara berturut-turut untuk mencoba menembus sistem.
2. **Hasil yang Diharapkan:** Pada tebakan ke-1 dan ke-2, server hanya merespon dengan pesan gagal (*401 Unauthorized*). Namun, tepat pada kegagalan ke-3, algoritma IDS akan terpicu. Gateway secara otomatis menambahkan IP penyerang ke dalam *Blacklist*, mengembalikan *403 Forbidden - IP BLOCKED*, lalu mengirimkan notifikasi Email Darurat (*CRITICAL*) kepada Admin.

---

## 2. Bukti Implementasi

### Sebelum Keamanan

#### ❌ Login Tanpa Autentikasi (HTTP Plain Text)

Firmware `iot-code/main.py` (vulnerable baseline) mengirim data **tanpa token** dan **tanpa enkripsi**:

```python
# VULNERABLE: Header hanya berisi password default, bukan Bearer Token
headers = {
    "Password-Login": "admin123",      # ❌ Plain password di header HTTP
    "Content-Type": "text/plain; charset=utf-8",
}

# VULNERABLE: Data sensor dikirim PLAIN TEXT — siapapun bisa membaca isinya
data_influx = "smart_room,lokasi=Ruang_Kelas_A suhu=28.5,kelembaban=65,cahaya=42000,gerakan=1,daya_listrik=3500.0"

# ❌ HTTP biasa — tidak ada enkripsi transit
res_in = requests.post("http://xxxjg.run.pinggy-free.link/api/v2/write", headers=headers, data=data_influx)
# → Server mengembalikan HTTP 401: Unauthorized (password default ditolak)
```

**Output Serial Monitor (Wokwi) — Sebelum Keamanan:**
```
--------------------------------------------------
📍 Lokasi: Ruang_Kelas_A (NO SECURITY MODE - VULNERABLE)
>> ❌ Mengirim Data Tanpa Enkripsi (HTTP Plain Text) - VULNERABLE...
   Data terkirim: smart_room,lokasi=Ruang_Kelas_A suhu=28.5,kelembaban=65,...
>> Status HTTP: 401
   ❌ [DITOLAK] Server menolak karena tidak ada autentikasi valid!
   ⚠️  Screenshot log ini sebagai BUKTI celah keamanan
⚠️  PERINGATAN: Kode ini adalah BASELINE RENTAN untuk perbandingan!
```

---

#### ❌ Data MQTT Terbaca Bebas (Sniffing Simulation)

Karena tidak ada enkripsi, payload yang terbang di jaringan bisa dibaca langsung:
```
# Packet yang terlihat di Wireshark / network sniffing:
POST /api/v2/write HTTP/1.1
Host: xxxjg.run.pinggy-free.link
Password-Login: admin123
Content-Type: text/plain

smart_room,lokasi=Ruang_Kelas_A suhu=28.5,kelembaban=65,cahaya=42000,gerakan=1,daya_listrik=3500.0
```
> Semua data sensor terbaca jelas — suhu, kelembaban, status gerak, dan estimasi daya listrik.

---

#### ❌ Password Default Aktif

Simulasi hacker mengirim request kontrol lampu **tanpa token apapun** (mode keamanan dinonaktifkan):

```
POST http://localhost:5000/set_light?state=on
(Tanpa header Authorization)

→ HTTP 200 OK
→ {"status": "success", "light": "on", "security": "DISABLED"}
🚨 [HASIL SERANGAN] SUKSES! Lampu gedung menyala tanpa izin!
```

---

### Sesudah Keamanan

#### ✅ Login Berhasil dengan Token & Device ID yang Benar

**Output Serial Monitor Wokwi — Sesudah Keamanan:**
```
--------------------------------------------------
📍 Lokasi: Ruang_Kelas_A [SECURE MODE AKTIF]
Suhu: 28.5 C | Kelembaban: 65 %
Cahaya: 42318 | Gerakan: 1
Daya Listrik (Estimasi): 3500.0 Watt

>> Data Terenkripsi (Hex):
   3b1a4f2e7c0d1e5f3a2b4c...  ← tidak bisa dibaca tanpa kunci!
>> Mengirim data terenkripsi via API Gateway (HTTPS)...
>> Status HTTP Gateway: 204
   ✅ [AMAN] Data sensor sukses didekripsi & disimpan ke InfluxDB!
   📊 Total berhasil kirim: 1
--------------------------------------------------
✅ [SECURE] Semua security layer aktif. Menunggu 15 detik...
```

**Log API Gateway — Koneksi Device Pertama:**
```
[INFO] IP: 110.138.80.6 | ACTION: DEVICE_LOGIN | STATUS: KONEKSI PERTAMA
       | DETAILS: Device 'PICO-W-CLASS-A' berhasil login dari IP 110.138.80.6
[INFO] IP: 110.138.80.6 | ACTION: WRITE | STATUS: SUCCESS
       | DETAILS: Data sukses didekripsi: smart_room,lokasi=Ruang_Kelas_A suhu=28.5,...
[INFO] IP: 110.138.80.6 | ACTION: FORWARD | STATUS: INFLUXDB_204
       | DETAILS: Sukses meneruskan data ke database.
```

---

#### ❌ Login Gagal jika Credential Salah (Dashboard)

Dashboard Streamlit menerapkan lockout 3 percobaan:

```
Percobaan 1: Username: admin | Password: salah1  → ❌ Sisa 2 percobaan
Percobaan 2: Username: admin | Password: salah2  → ❌ Sisa 1 percobaan
Percobaan 3: Username: admin | Password: salah3  → 🚨 AKSES TERKUNCI!

# Log forensik yang tercatat:
2026-05-31 20:25:10 | WARNING | IP: 127.0.0.1 | ACTION: DASHBOARD_LOGIN | STATUS: FAILED
                    | DETAILS: Gagal login (User: 'admin'). Percobaan ke-3/3
2026-05-31 20:25:10 | CRITICAL | IP: 127.0.0.1 | ACTION: DASHBOARD_LOGIN | STATUS: LOCKED_OUT
                    | DETAILS: Akun dikunci otomatis oleh IDS (brute-force terdeteksi).
```

---

#### ✅ Data Terenkripsi / Akses Ditolak saat Token Salah

**Simulasi Brute-Force (attack_simulator.py — Serangan B):**
```
🔥 SIMULASI SERANGAN SIBER: Percobaan Serangan Brute-Force Token API

⚡ Percobaan #1: Token 'admin123'
   [HTTP RESPONSE] 401 {"error": "Unauthorized", "message": "Invalid token."}

⚡ Percobaan #2: Token 'password_dosen'
   [HTTP RESPONSE] 401 {"error": "Unauthorized", "message": "Invalid token."}

⚡ Percobaan #3: Token 'token_palsu_999'
   [HTTP RESPONSE] 403 {"error": "Forbidden", "message": "Intrusion detected. Your IP is blocked."}
   🛡️ [IDS ACTION] Sistem mendeteksi Brute-Force! IP Anda sekarang resmi DIBLOKIR permanen!
```

**Log API Gateway — Deteksi & Blokir:**
```
[WARN]     IP: 127.0.0.1 | ACTION: WRITE | STATUS: INVALID_TOKEN | Token salah. Percobaan: 1/3
[WARN]     IP: 127.0.0.1 | ACTION: WRITE | STATUS: INVALID_TOKEN | Token salah. Percobaan: 2/3
[CRITICAL] IP: 127.0.0.1 | ACTION: IDS_BLOCK | STATUS: BLOCKED
           | DETAILS: IP resmi DIBLOKIR akibat token salah berulang.
```

---

## 3. Dokumentasi Teknis

### Teknologi yang Digunakan

| Layer | Teknologi | Versi | Fungsi |
|-------|-----------|-------|--------|
| **IoT Device** | MicroPython / Wokwi | Pico W | Firmware sensor + enkripsi |
| **Sensor** | DHT22, LDR (ADC), PIR | — | Suhu, cahaya, gerak |
| **Output** | LCD I2C 16×2, LED, Buzzer | — | Display lokal + aktuator |
| **Tunnel** | Pinggy SSH Tunnel | Free tier | HTTPS ke localhost |
| **API Gateway** | Python Flask | 3.1.3 | Auth, IDS, Decrypt, Forward |
| **Database** | InfluxDB | v2.9.1 | Time-series sensor storage |
| **Dashboard** | Streamlit | 1.57.0 | Web UI + forensik log |
| **Email Alert** | SMTP (smtplib) | — | Notifikasi keamanan |
| **Runtime** | Python | 3.10.12 | Server-side (Linux/WSL) |
| **Container** | Docker | — | InfluxDB container |

---

### Konfigurasi Keamanan

#### A. Autentikasi & Akses

```json
// Konfigurasi API Gateway (api_gateway.py)
{
  "SECURE_TOKEN":          "token_aman_smartroom_2026",
  "REGISTERED_DEVICE_ID":  "PICO-W-CLASS-A",
  "MAX_FAILED_ATTEMPTS":    3,
  "AUTO_BLOCK_IP":          true
}

// Konfigurasi Device (iot-code/main_secure.py)
{
  "GATEWAY_URL":   "https://<pinggy-url>.run.pinggy-free.link",
  "SECURE_TOKEN":  "token_aman_smartroom_2026",
  "DEVICE_ID":     "PICO-W-CLASS-A",
  "SHARED_KEY":    "RAHASIA_KAMPUS_UNTUK_DEKRIPSI"
}

// Konfigurasi Dashboard (dashboard.py)
{
  "ADMIN_USER":     "admin",
  "AUTH_METHOD":    "SHA-256 hash comparison",
  "MAX_LOGIN_FAIL": 3,
  "LOCKOUT":        "session-based"
}
```

#### B. Email Alert (settings.json)

```json
{
  "recipient_email":      "admin@kampus.ac.id",
  "email_alerts_enabled": true,
  "smtp_host":            "smtp.gmail.com",
  "smtp_port":            587,
  "smtp_user":            "",
  "smtp_password":        ""
}
```
> Jika `smtp_user` kosong → sistem otomatis pakai **Mock Mode** (simpan ke `mock_emails.log`).

#### C. Pemicu Email Alert Otomatis

| Event | Pemicu | Severity |
|-------|--------|----------|
| Device login pertama kali | `/write` endpoint, session baru | INFO |
| Device reconnect (>5 menit offline) | `/write` endpoint, timeout sesi | INFO |
| Login dashboard berhasil | Form login dashboard | INFO |
| Login dashboard gagal | Percobaan login salah | WARNING |
| Dashboard dikunci (3x gagal) | Lockout tercapai | CRITICAL |
| Device asing terhubung | X-Device-ID tidak dikenal | WARNING |
| IP diblokir (brute-force) | `blocked_ips.add(ip)` | CRITICAL |

---

### Potongan Kode Penting

#### 1. Enkripsi Payload di Device (XOR Hex Cipher)

```python
# iot-code/main_secure.py
SHARED_KEY = "RAHASIA_KAMPUS_UNTUK_DEKRIPSI"

def encrypt_payload(text, key=SHARED_KEY):
    """
    Enkripsi XOR: setiap karakter di-XOR dengan karakter kunci secara siklik.
    Input : "smart_room,lokasi=Ruang_Kelas_A suhu=28.5,kelembaban=65,..."
    Output: "3b1a4f2e7c0d..." (hex string — tidak terbaca tanpa kunci)
    """
    cipher_bytes = bytes([ord(c) ^ ord(key[i % len(key)]) for i, c in enumerate(text)])
    return "".join("{:02x}".format(b) for b in cipher_bytes)

# Penggunaan di main loop:
raw_line_protocol = "smart_room,lokasi=Ruang_Kelas_A suhu={},kelembaban={},cahaya={},gerakan={},daya_listrik={}".format(
    temp, hum, ldr_val, pir_event, daya_listrik
)
encrypted_hex = encrypt_payload(raw_line_protocol)
```

#### 2. Pengiriman Aman dengan Bearer Token + Device ID

```python
# iot-code/main_secure.py
headers = {
    "Authorization": "Bearer " + SECURE_TOKEN,  # ✅ Bearer Token
    "X-Device-ID":   DEVICE_ID,                 # ✅ Device Identity
    "Content-Type":  "application/json"
}
json_payload = {"encrypted_data": encrypted_hex}

# HTTPS request via Pinggy TLS tunnel
res = requests.post(GATEWAY_URL + "/write", headers=headers, json=json_payload)
```

#### 3. IDS — Blokir IP Otomatis (API Gateway)

```python
# api_gateway.py
@app.before_request
def check_intrusion():
    ip = request.remote_addr
    if ip in blocked_ips:          # ← Cek daftar cekal di setiap request
        log_event("CRITICAL", ip, request.path, "REJECTED", "IP diblokir permanen.")
        return jsonify({"error": "IP Blocked"}), 403

# Di dalam endpoint /write — setelah token gagal 3x:
failed_attempts[ip] = failed_attempts.get(ip, 0) + 1
if failed_attempts[ip] >= 3:
    blocked_ips.add(ip)            # ← Blokir permanen
    send_email_alert("🚨 CRITICAL: Brute-Force Blocked", ...)
    return jsonify({"error": "Forbidden", "message": "Intrusion detected."}), 403
```

#### 4. Dekripsi Payload di Gateway

```python
# api_gateway.py
def decrypt_payload(hex_str, key=SHARED_KEY):
    """Dekripsi XOR Hex yang dikirim device — kebalikan dari encrypt_payload."""
    cipher_bytes = bytes.fromhex(hex_str)
    return "".join(chr(b ^ ord(key[i % len(key)])) for i, b in enumerate(cipher_bytes))

# Di dalam /write endpoint:
encrypted_hex = req_json["encrypted_data"]
decrypted_line_protocol = decrypt_payload(encrypted_hex)
# → "smart_room,lokasi=Ruang_Kelas_A suhu=28.5,kelembaban=65,..."

# Forward ke InfluxDB dalam bentuk plain Line Protocol (internal — tidak ke internet)
requests.post(INFLUX_URL, headers={"Authorization": "Token " + INFLUX_TOKEN}, data=decrypted_line_protocol)
```

#### 5. Login Dashboard dengan SHA-256 Hash

```python
# dashboard/dashboard.py
import hashlib

ADMIN_PASSWORD_HASH = hashlib.sha256("admin_password_2026".encode()).hexdigest()

# Saat submit form login:
input_hash = hashlib.sha256(pwd.encode()).hexdigest()
if user == ADMIN_USER and input_hash == ADMIN_PASSWORD_HASH:
    st.session_state["logged_in"] = True
    # → Kirim email konfirmasi login
else:
    st.session_state["failed_attempts"] += 1
    if st.session_state["failed_attempts"] >= 3:
        st.session_state["locked_out"] = True   # ← Lockout aktif
```

#### 6. Device Session Tracker — Email Login Device

```python
# api_gateway.py
device_sessions = {}          # {device_id: {ip, first_seen, last_seen}}
DEVICE_TIMEOUT_MINUTES = 5

# Setelah token & device_id valid:
existing = device_sessions.get(device_id)
is_new   = existing is None
is_recon = existing and (now - existing["last_seen"]).total_seconds() > DEVICE_TIMEOUT_MINUTES * 60

if is_new or is_recon:
    send_email_alert(
        f"📡 Device Login: {device_id} [{'Koneksi Pertama' if is_new else 'Reconnect'}]",
        f"Device ID: {device_id}\nIP: {ip}\nWaktu: {now}"
    )
device_sessions[device_id] = {"ip": ip, "first_seen": ..., "last_seen": now}
```

---

### Hasil Pengujian

#### Skenario 1: Data Sensor Aman (Sebelum vs Sesudah)

| Aspek | Sebelum Keamanan | Sesudah Keamanan |
|-------|-----------------|-----------------|
| Protokol | HTTP (plain) | HTTPS (TLS via Pinggy) |
| Payload | `suhu=28.5,kelembaban=65,...` (terbaca) | `3b1a4f2e7c0d...` (hex terenkripsi) |
| Auth Header | `Password-Login: admin123` | `Authorization: Bearer token_aman_smartroom_2026` |
| Device ID | Tidak ada | `X-Device-ID: PICO-W-CLASS-A` |
| Status Server | `HTTP 401` (ditolak) | `HTTP 204` (sukses tersimpan) |

---

#### Skenario 2: Kontrol Lampu Ilegal (Sebelum vs Sesudah)

| Kondisi | Request | Status | Hasil |
|---------|---------|--------|-------|
| Sebelum keamanan (mode OFF) | `POST /set_light?state=on` — tanpa token | `200 OK` | 💡 Lampu menyala — **BERHASIL DISERANG** |
| Sesudah keamanan (mode ON) | `POST /set_light?state=on` — tanpa token | `401 Unauthorized` | 🛡️ Lampu aman — **SERANGAN DITOLAK** |
| Sesudah keamanan (mode ON) | `POST /set_light?state=on` — token valid | `200 OK` | ✅ Admin resmi berhasil kontrol |

---

#### Skenario 3: Brute-Force API Token (IDS)

| Percobaan | Token Digunakan | HTTP Status | IDS Action |
|-----------|----------------|-------------|------------|
| #1 | `admin123` | `401` | Catat gagal (1/3) |
| #2 | `password_dosen` | `401` | Catat gagal (2/3) |
| #3 | `token_palsu_999` | `403` | 🚫 **IP DIBLOKIR PERMANEN** + Email CRITICAL dikirim |
| #4+ | apapun | `403` | Ditolak langsung tanpa proses |

---

#### Skenario 4: Login Dashboard Brute-Force

| Percobaan | Aksi | Hasil |
|-----------|------|-------|
| #1 gagal | Password salah | ⚠️ Peringatan — sisa 2 percobaan |
| #2 gagal | Password salah | ⚠️ Peringatan — sisa 1 percobaan |
| #3 gagal | Password salah | 🚨 **AKSES TERKUNCI** — email CRITICAL terkirim |
| Login berhasil | Password benar | ✅ Masuk dashboard + email INFO terkirim |

---

#### Log Forensik Aktual (security_activity.log)

```
2026-05-31 20:27:10 | INFO    | IP: 127.0.0.1 | ACTION: DASHBOARD_LOGIN  | STATUS: SUCCESS  | Admin berhasil login ke dashboard.
2026-05-31 20:28:18 | INFO    | IP: 127.0.0.1 | ACTION: TOGGLE_SECURITY  | STATUS: CHANGED  | Mode Keamanan diubah menjadi MATI
2026-05-31 20:28:19 | INFO    | IP: 127.0.0.1 | ACTION: TOGGLE_SECURITY  | STATUS: CHANGED  | Mode Keamanan diubah menjadi AKTIF
2026-05-31 20:28:21 | INFO    | IP: 127.0.0.1 | ACTION: UNBLOCK_IPS      | STATUS: RESET    | Semua daftar blokir IP dibersihkan.
```

---

#### Email Alert Aktual (mock_emails.log)

```
Timestamp: Sun May 31 20:27:10 WIB 2026
TO: admin@kampus.ac.id
SUBJECT: Dashboard Login Successful

Halo Admin,
Login sukses ke Dashboard Web Control Center.
Detail:
- Waktu: 2026-05-31 20:27:10
- IP: 127.0.0.1
- Status: SUKSES
```

---

## 🚀 Cara Menjalankan

```bash
# Terminal 1 — Start InfluxDB Docker
docker start influxdb_tugas

# Terminal 2 — Install dependency + jalankan API Gateway
pip3 install influxdb-client
cd /home/vereniaes/project/iot-room
python3 api_gateway.py

# Terminal 3 — Buka Pinggy HTTPS Tunnel ke port 5000
ssh -p 443 -R0:localhost:5000 a.pinggy.io
# → Salin URL HTTPS ke variabel GATEWAY_URL di main_secure.py (Wokwi)

# Terminal 4 — Jalankan Streamlit Dashboard
cd /home/vereniaes/project/iot-room
streamlit run dashboard/dashboard.py
# → Buka browser: http://localhost:8501
# → Login: admin / admin_password_2026

# (Opsional) Terminal 5 — Simulasi Serangan
python3 attack_simulator.py
```

---

## 📁 Struktur File

```
iot-room/
├── iot-code/
│   ├── main.py              ← Firmware VULNERABLE (baseline sebelum keamanan)
│   ├── main_secure.py       ← Firmware AMAN (digunakan di Wokwi)
│   ├── i2c_lcd.py           ← Driver LCD I2C
│   ├── lcd_api.py           ← LCD API
│   └── diagram.json         ← Wiring diagram Wokwi
├── dashboard/
│   ├── dashboard.py         ← Web Dashboard Streamlit (5 Tab)
│   └── data_sensor_1_minggu_lineprotocol.txt  ← Data dummy 1 minggu
├── api_gateway.py           ← Flask API Gateway (Auth + IDS + Decrypt)
├── email_helper.py          ← Email alert helper (SMTP + Mock fallback)
├── attack_simulator.py      ← Simulator serangan siber interaktif
├── settings.json            ← Konfigurasi email alert (dari halaman Settings)
├── security_activity.log    ← Log forensik aktivitas keamanan
├── mock_emails.log          ← Email yang tertangkap di mode Mock
└── README.md                ← Dokumentasi ini
```

---

## ✅ Ringkasan Checklist Keamanan

| # | Checklist | Implementasi | File | Status |
|---|-----------|-------------|------|--------|
| A1 | MQTT Auth (simulasi) | WiFi password + ACL simulasi | `main_secure.py` | ✅ Simulasi |
| A2 | API Key Validation | Bearer Token di header | `api_gateway.py` | ✅ Aktif |
| A3 | Bearer Token / JWT | `token_aman_smartroom_2026` | `main_secure.py` + `api_gateway.py` | ✅ Aktif |
| A4 | Expired Session Token | Lockout session dashboard | `dashboard.py` | ✅ Simulasi |
| A5 | Device ID Validation | Header `X-Device-ID` | `api_gateway.py` | ✅ Aktif |
| A6 | Token Pairing Device | SECURE_TOKEN + DEVICE_ID pair | keduanya | ✅ Aktif |
| B1 | HTTPS / SSL/TLS | Pinggy HTTPS Tunnel | `main_secure.py` | ✅ Aktif |
| B2 | Payload Encryption | XOR Hex Cipher | `main_secure.py` + `api_gateway.py` | ✅ Aktif |
| B3 | Secure WiFi | Wokwi-GUEST (simulasi WPA2) | `main_secure.py` | ✅ Simulasi |
| C1 | Login Protection (3x) | `st.session_state` lockout | `dashboard.py` | ✅ Aktif |
| C2 | Auto Block IP | `blocked_ips` set + IDS middleware | `api_gateway.py` | ✅ Aktif |
| C3 | Activity Logging | `security_activity.log` | `api_gateway.py` + `dashboard.py` | ✅ Aktif |
| C4 | Email Alert | SMTP async + Mock fallback | `email_helper.py` | ✅ Aktif |
| C5 | Device Login Alert | Session tracker + email | `api_gateway.py` | ✅ Aktif |
| C6 | Discord Webhook | `DISCORD_WEBHOOK_URL` config | `api_gateway.py` | ⚙️ Config needed |

---

*Dibuat untuk Lembar Kerja 5 — IoT Security | Smart Room UNJ*
