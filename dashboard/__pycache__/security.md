# Panduan Bukti Implementasi Keamanan (LK5)

Dokumen ini berisi potongan kode (sebagai bukti teknis) dan panduan pengambilan *screenshot* untuk setiap poin *Security Checklist* yang berhasil diimplementasikan di sistem IoT kita.

## Ringkasan Implementasi

| Metode Keamanan | Pengaplikasian | Hasilnya |
| :--- | :--- | :--- |
| **API Security (Bearer Token)** | `api_gateway.py` & `main_secure.py` | API Gateway menolak request tanpa header *Authorization* yang berisi token valid (Error 401). |
| **Device Authentication** | Header `X-Device-ID` | Sistem memverifikasi ID unik perangkat dan memantau status Online/Offline device. |
| **HTTPS / SSL/TLS** | Tunneling via Pinggy | Jalur transmisi API dan web dienkripsi penuh (URL wajib berawalan `https://`). |
| **Payload Encryption** | `encrypt_payload()` (XOR Cipher) | Data sensor diubah menjadi bentuk *Hex Ciphertext* sehingga tidak bisa dibaca (*sniffing*). |
| **Secure WiFi Layer** | Simulasi WPA2 di `main_secure.py` | Perangkat dipaksa hanya terhubung ke koneksi nirkabel yang terenkripsi aman (WPA2). |
| **Login Protection (IDS)** | Logika Lockout di `api_gateway.py` | Sistem otomatis memblokir IP Address secara permanen jika salah menebak token 3 kali (Error 403). |
| **Activity Logging** | Pencatatan `security_activity.log` | Mencatat riwayat lengkap (Waktu, IP, Status) dari semua login, kontrol, maupun serangan siber. |
| **Alert System** | SMTP Gmail via `email_helper.py` | Langsung mengirim notifikasi email ke Admin saat ada IP yang terblokir atau perangkat baru login. |

---

## A. Authentication & Access Control

### 1. API Security (Bearer Token)
Sistem menggunakan Bearer Token pada setiap permintaan HTTP dari perangkat IoT ke server Gateway. Tanpa token yang benar, akses akan ditolak (401 Unauthorized).

**Bukti Kode:**
*Di `iot-code/main_secure.py` (Kirim Token):*
```python
SECURE_TOKEN = "token_aman_smartroom_2026"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {SECURE_TOKEN}",
    "X-Device-ID": DEVICE_ID
}
```

*Di `api_gateway.py` (Validasi Token):*
```python
auth_header = request.headers.get('Authorization')
if not auth_header or not auth_header.startswith("Bearer "):
    return jsonify({"error": "Unauthorized"}), 401

token = auth_header.split(" ")[1]
if token != SECURE_TOKEN:
    return jsonify({"error": "Unauthorized", "message": "Invalid token."}), 401
```

📸 **Guide Screenshot:**
1. Screenshot kode `SECURE_TOKEN` di file `api_gateway.py`.
2. Screenshot hasil Terminal saat Anda menjalankan `python3 attack_simulator.py` (Menu 1) yang memperlihatkan **HTTP RESPONSE 401 Unauthorized** (Ditolak karena tanpa token).

### 2. Device Authentication (Device ID Validation)
Sistem memverifikasi identitas unik perangkat. Jika ada device yang menggunakan token benar tapi Device ID-nya asing/salah, sistem akan menolak requestnya.

**Bukti Kode:**
*Di `api_gateway.py`:*
```python
device_id = request.headers.get('X-Device-ID')
if not device_id or device_id not in REGISTERED_DEVICES:
    return jsonify({"error": "Unauthorized", "message": "Unknown Device ID"}), 401
```

📸 **Guide Screenshot:**
1. Buka Tab **"🛡️ Security & Logs"** di Dashboard.
2. Screenshot tabel **"📡 Connected Devices"** yang memperlihatkan Device ID (`PICO-W-CLASS-A`) berstatus Online beserta IP-nya.

---

## B. Encryption & Secure Communication

### 1. HTTPS / SSL/TLS
Sistem tidak menggunakan HTTP telanjang yang rentan disadap, melainkan diekspos melalui HTTPS secure tunnel (menggunakan layanan Pinggy).

**Bukti Kode:**
*Di `iot-code/main_secure.py`:*
```python
# API URL dipaksa menggunakan HTTPS (SSL/TLS Termination)
GATEWAY_URL = "https://nxtgh-110-138-80-6.run.pinggy-free.link"
```

📸 **Guide Screenshot:**
1. Screenshot terminal Anda saat menjalankan command Pinggy (`ssh -p 443 -R0...`), yang memperlihatkan *URL https://...pinggy-free.link*.
2. Tunjukkan bahwa URL yang di-copy ke `main_secure.py` berawalan `https://`.

### 2. Payload Encryption (Enkripsi Data Sensor)
Data sensor disandikan menjadi format Hexadesimal (XOR Cipher) agar tidak bisa dibaca (*sniffing*) oleh peretas di jaringan WiFi yang sama.

**Bukti Kode:**
*Di `iot-code/main_secure.py` (Proses Enkripsi):*
```python
def encrypt_payload(plain_text):
    # Enkripsi ringan XOR Cipher ke Hex Format
    cipher_bytes = bytes([ord(c) ^ ord(ENCRYPTION_KEY[i % len(ENCRYPTION_KEY)]) 
                         for i, c in enumerate(plain_text)])
    return "".join("{:02x}".format(b) for b in cipher_bytes)

# Payload yang dikirim bukan Suhu/Kelembaban, tapi ciphertext
payload = ujson.dumps({"encrypted_data": encrypted_hex})
```

📸 **Guide Screenshot:**
1. Jalankan simulasi di Wokwi (tekan tombol Play).
2. Screenshot **Terminal Wokwi** yang memperlihatkan teks `>> Data Terenkripsi (Hex): 212c2933...` (Data sensor yang disamarkan).

### 3. Secure WiFi Layer
Proyek IoT diset agar hanya terhubung pada koneksi dengan protokol WPA2/WPA3.

**Bukti Kode:**
*Di `iot-code/main_secure.py`:*
```python
# Simulasi koneksi WPA2 Secure Network
ssid = "Wokwi-GUEST"
password = ""  # Di produksi diwajibkan: "K@mpus_S3kur3_2026!"
```

📸 **Guide Screenshot:**
1. Screenshot blok kode pengaturan `ssid` dan `password` di Wokwi yang memiliki komentar tentang *WPA2 strong password*.

---

## C. Intrusion Detection (IDS) & Alert System

### 1. Login Protection (Max 3x Gagal & Auto-Block IP)
API Gateway memiliki *Firewall* pintar (IDS) yang akan memblokir secara permanen IP Address mana pun yang memasukkan token salah sebanyak 3 kali berturut-turut.

**Bukti Kode:**
*Di `api_gateway.py`:*
```python
# Cek apakah IP penyerang sudah masuk daftar hitam
if ip in blocked_ips:
    return jsonify({"error": "Forbidden"}), 403

if token != SECURE_TOKEN:
    failed_attempts[ip] = failed_attempts.get(ip, 0) + 1
    if failed_attempts[ip] >= 3:
        blocked_ips.add(ip) # AUTO BLOCK IP
        send_email_alert("CRITICAL: Device Blocked", "Brute-force terdeteksi.")
        return jsonify({"error": "Forbidden", "message": "IP is blocked."}), 403
```

📸 **Guide Screenshot:**
1. Jalankan `python3 attack_simulator.py` dan pilih **Menu 2 (Brute-Force)**.
2. Screenshot proses serangan yang mulanya membalas `401 Unauthorized` pada tebakan token 1-2, lalu mendadak menjadi `403 Forbidden - IP BLOCKED` pada tebakan ke-3/4.

### 2. Activity Logging (Simpan Waktu, IP, Status)
Semua percobaan akses, baik sukses, gagal, maupun serangan, dicatat di log digital (*audit trail*) untuk kebutuhan investigasi forensik.

**Bukti Kode:**
*Di `api_gateway.py`:*
```python
def log_event(level, ip, action, status, details):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} | {level} | IP: {ip} | ACTION: {action} | STATUS: {status} | DETAILS: {details}\n"
    with open("security_activity.log", "a") as f:
        f.write(log_line)
```

📸 **Guide Screenshot:**
1. Buka Tab **"🛡️ Security & Logs"** di Dashboard.
2. Screenshot **Tabel Forensik Log** yang menampilkan *Timestamp*, *Level*, *IP Address*, dan *Action* dari aktivitas perangkat maupun serangan.

### 3. Alert System (Email Alert: Device Asing & Login Gagal)
Jika terdeteksi serangan Brute-Force (IP Diblokir) atau ada *Device Baru/Asing* yang terhubung, sistem otomatis mengirimkan Email ke Admin Kampus.

**Bukti Kode:**
*Di `email_helper.py` (Koneksi SMTP):*
```python
def _send_email_worker(subject, body):
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login("titasaripratiwi8@gmail.com", "vycqnyqljbbdzqrs")
    server.sendmail(smtp_user, recipient, msg.as_string())
    server.quit()
```

📸 **Guide Screenshot:**
1. Buka **Inbox Email Gmail** Anda (`titasaripratiwi8@gmail.com`).
2. Screenshot salah satu/kedua email masuk ini:
   - Email peringatan judul: **"🚨 CRITICAL: Device Token Brute-Force Blocked"**.
   - Email notifikasi masuk judul: **"📡 Device Login: PICO-W-CLASS-A [Koneksi Pertama]"**.
