# 🛡️ Smart Room IoT Monitoring System
### Sistem Pemantauan Ruang Kelas Berbasis IoT — Universitas Negeri Jakarta

> **Kelompok:** Smart Room IoT  
> **Platform:** Wokwi (Raspberry Pi Pico W) · InfluxDB Cloud · Streamlit · Google Cloud Run  
> **Dashboard:** https://room-monitoring-476404504908.asia-southeast2.run.app

---

## 📋 Daftar Isi

1. [Deskripsi Sistem](#1-deskripsi-sistem)
2. [Diagram Arsitektur](#2-diagram-arsitektur)
3. [Hardware & Software yang Digunakan](#3-hardware--software-yang-digunakan)
4. [Implementasi Sistem](#4-implementasi-sistem)
   - [Akuisisi Data Sensor](#41-akuisisi-data-sensor)
   - [Konektivitas Internet](#42-konektivitas-internet)
   - [Penyimpanan Cloud](#43-penyimpanan-cloud)
   - [Monitoring Dashboard](#44-monitoring-dashboard)
   - [Integrasi Sistem](#45-integrasi-sistem)
5. [Screenshot Dashboard](#5-screenshot-dashboard)
6. [Cara Menjalankan](#6-cara-menjalankan)
7. [Kesimpulan](#7-kesimpulan)

---

## 1. Deskripsi Sistem

**Smart Room IoT Monitoring System** adalah sistem pemantauan kondisi ruang kelas berbasis Internet of Things (IoT) yang dirancang untuk memantau kualitas lingkungan kampus secara real-time. Sistem ini membaca data dari beberapa sensor lingkungan yang terpasang di ruang kelas, mengirimkan data tersebut ke cloud melalui internet, dan menampilkannya pada dashboard web yang dapat diakses dari mana saja.

### Fitur Utama

| Fitur | Keterangan |
|-------|------------|
| 🌡️ **Multi-Sensor** | Membaca suhu, kelembapan, intensitas cahaya, dan deteksi gerak secara bersamaan |
| 📡 **Real-time Streaming** | Data dikirim otomatis setiap 15 detik ke cloud |
| ☁️ **Cloud Storage** | Disimpan di InfluxDB Cloud, diakses dari mana saja |
| 📊 **Dashboard Interaktif** | Grafik historis, status device, forensik log keamanan |
| 🔐 **Keamanan IoT** | Enkripsi payload XOR, Bearer Token auth, Device ID, IDS otomatis |
| 📧 **Email Alert** | Notifikasi otomatis saat device connect, reconnect, atau ada serangan |

---

## 2. Diagram Arsitektur

### Alur Lengkap Sistem

```mermaid
graph TD
    subgraph DEVICE ["🤖 IoT Device — Wokwi Simulator"]
        S1["🌡️ DHT22\nSuhu & Kelembapan"]
        S2["💡 LDR\nIntensitas Cahaya"]
        S3["🚶 PIR\nDeteksi Gerak"]
        PICO["⚙️ Raspberry Pi Pico W\nMicroPython Firmware"]
        LCD["🖥️ LCD I2C 16×2\nDisplay Lokal"]
        S1 & S2 & S3 --> PICO
        PICO --> LCD
    end

    subgraph INTERNET ["🌐 Internet Layer"]
        PINGGY["🔒 Pinggy HTTPS Tunnel\nSSL/TLS Termination"]
        WORKER["☁️ Cloudflare Worker\nProxy Layer"]
    end

    subgraph GATEWAY ["🛡️ API Gateway — Python Flask"]
        AUTH["🔑 Auth Validator\nBearer Token + Device ID"]
        DECRYPT["🔓 XOR Decryptor\nHex → Line Protocol"]
        IDS["🚨 IDS\nBlokir IP Otomatis"]
        EMAIL["📧 Email Alert\nSMTP Notifikasi"]
    end

    subgraph CLOUD ["☁️ Cloud Storage & Dashboard"]
        INFLUX[("🗄️ InfluxDB Cloud\nTime-Series Database")]
        STREAMLIT["📊 Streamlit Dashboard\nGoogle Cloud Run\nport 8080"]
    end

    subgraph USER ["👨‍💼 Pengguna"]
        ADMIN["🖥️ Browser Admin\nMonitoring Real-time"]
    end

    PICO -->|"HTTPS POST\nBearer Token + Device ID\nEncrypted Hex Payload"| PINGGY
    PINGGY -->|Forward| GATEWAY
    AUTH --> DECRYPT --> INFLUX
    IDS --> EMAIL
    INFLUX -->|Query 7 hari| STREAMLIT
    STREAMLIT -->|HTTPS| ADMIN

    style DEVICE fill:#1e3a5f,color:#fff,stroke:#3b82f6
    style INTERNET fill:#14532d,color:#fff,stroke:#22c55e
    style GATEWAY fill:#3b0764,color:#fff,stroke:#a855f7
    style CLOUD fill:#164e63,color:#fff,stroke:#06b6d4
    style USER fill:#1a1a2e,color:#fff,stroke:#6366f1
```

### Alur Data Detail

```
Sensor Fisik → Pico W (baca & enkripsi) → HTTPS POST via Pinggy
    → API Gateway (validasi token, dekripsi, IDS) → InfluxDB Cloud
    → Dashboard Streamlit (Cloud Run) → Browser Pengguna
```

---

## 3. Hardware & Software yang Digunakan

### Hardware (Simulasi via Wokwi)

| Komponen | Spesifikasi | Fungsi |
|----------|------------|--------|
| **Raspberry Pi Pico W** | RP2040 + CYW43439 WiFi | Mikrokontroler utama IoT |
| **DHT22** | Digital, pin GP5 | Sensor suhu & kelembapan udara |
| **LDR + ADC** | Analog, pin GP28 (ADC2) | Sensor intensitas cahaya ruangan |
| **PIR Sensor** | Digital, pin GP4 | Deteksi gerak/kehadiran manusia |
| **LCD I2C 16×2** | I2C addr 0x27, SDA GP0, SCL GP1 | Display status lokal di ruangan |
| **LED** | Digital, pin GP3 | Indikator lampu gedung (aktuator) |
| **Buzzer** | Digital, pin GP6 | Alarm saat terdeteksi gerakan |

### Software & Platform

| Layer | Teknologi | Versi | Fungsi |
|-------|-----------|-------|--------|
| **Firmware IoT** | MicroPython (Wokwi) | 1.24.1 | Logic sensor, enkripsi, HTTP client |
| **Tunnel** | Pinggy SSH HTTPS | Free | Expose local gateway ke internet |
| **API Gateway** | Python Flask + Gunicorn | 3.1.3 | Auth, IDS, dekripsi, forward ke DB |
| **Reverse Proxy** | nginx | 1.18 | Route request gateway vs dashboard |
| **Database Cloud** | InfluxDB Cloud (v2) | Serverless | Penyimpanan time-series sensor |
| **Dashboard** | Streamlit | 1.57.0 | Visualisasi real-time + forensik log |
| **Deployment** | Google Cloud Run | — | Container hosting dashboard + gateway |
| **Email Alert** | SMTP (smtplib) / Mock | — | Notifikasi keamanan otomatis |
| **Containerisasi** | Docker | — | Build & deploy image |

---

## 4. Implementasi Sistem

### 4.1 Akuisisi Data Sensor

Perangkat IoT membaca **4 jenis sensor** secara bersamaan dalam setiap siklus (15 detik):

```python
# iot-code/main_secure.py — Pembacaan sensor DHT22, LDR, PIR
def check_sensors():
    dht_sensor.measure()
    temp     = dht_sensor.temperature()   # Suhu (°C)
    hum      = dht_sensor.humidity()      # Kelembapan (%)
    ldr_val  = ldr.read_u16()             # Cahaya (0–65535 ADC)
    pir_val  = pir.value()               # Gerak (0/1)
    return temp, hum, ldr_val, pir_val
```

**Parameter yang dipantau:**

| Sensor | Parameter | Satuan | Range Nilai |
|--------|-----------|--------|-------------|
| DHT22 | Suhu | °C | 0 – 50 |
| DHT22 | Kelembapan | % | 20 – 90 |
| LDR | Intensitas Cahaya | ADC (0–65535) | Gelap~0 / Terang~65000 |
| PIR | Deteksi Gerak | Boolean | 0 (diam) / 1 (ada gerak) |
| Kalkulasi | Estimasi Daya Listrik | Watt | 250W (idle) / 3500W (aktif) |

Data diformat dalam **InfluxDB Line Protocol** sebelum dikirim:
```
smart_room,lokasi=Ruang_Kelas_A suhu=27.8,kelembaban=35.0,cahaya=16003,gerakan=0,daya_listrik=250.0
```

---

### 4.2 Konektivitas Internet

Data dikirim **secara otomatis** melalui internet dengan lapisan keamanan:

**Langkah pengiriman:**

1. **Enkripsi Payload** — Data di-XOR-encrypt menjadi hex string sebelum meninggalkan device
2. **Koneksi WiFi WPA2** — Pico W terhubung ke jaringan `Wokwi-GUEST`
3. **HTTPS POST** — Request dikirim ke endpoint `/write` melalui tunnel Pinggy
4. **Bearer Token + Device ID** — Header autentikasi wajib di setiap request

```python
# iot-code/main_secure.py — Pengiriman aman
headers = {
    "Authorization": "Bearer token_aman_smartroom_2026",
    "X-Device-ID":   "PICO-W-CLASS-A",
    "Content-Type":  "application/json",
    "Connection":    "close"
}
payload = {"encrypted_data": encrypted_hex}
res = requests.post(GATEWAY_URL + "/write", headers=headers, data=ujson.dumps(payload))
```

**Output Serial Monitor Wokwi:**
```
[OK] WiFi Connected! IP: 10.10.0.1
--------------------------------------------------
📍 Lokasi: Ruang_Kelas_A [SECURE MODE AKTIF]
Suhu: 27.8 C | Kelembaban: 35.0 %
Cahaya: 16003 | Gerakan: 0
Daya Listrik (Estimasi): 250.0 Watt

>> Data Terenkripsi (Hex):
   212c293327163330242c613c3a383e262769...
>> Mengirim data terenkripsi via API Gateway (HTTPS)...
>> Status HTTP Gateway: 200
   ✅ [AMAN] Data sensor sukses didekripsi & disimpan ke InfluxDB!
   📊 Total berhasil kirim: 1
--------------------------------------------------
✅ [SECURE] Semua security layer aktif. Menunggu 15 detik...
```

---

### 4.3 Penyimpanan Cloud

Data tersimpan di **InfluxDB Cloud** (time-series database) yang dapat diakses dari mana saja:

| Parameter | Nilai |
|-----------|-------|
| Platform | InfluxDB Cloud (AWS us-east-1) |
| Organisasi | `iot-unj` |
| Bucket | `sensor-data` |
| Retensi Data | 30 hari |
| Format | Line Protocol (time-series) |
| Akses | REST API dengan Token autentikasi |

**Alur penyimpanan:**
```
Wokwi Device (encrypted hex)
    → Pinggy HTTPS Tunnel
    → API Gateway (dekripsi → Line Protocol)
    → InfluxDB Cloud /api/v2/write
    → Tersimpan di bucket sensor-data ✅
```

**API Gateway meneruskan data ke InfluxDB:**
```python
# api_gateway.py — Forward ke InfluxDB Cloud
headers = {
    "Authorization": "Token " + INFLUX_TOKEN,
    "Content-Type":  "text/plain; charset=utf-8"
}
res = requests.post(INFLUX_URL, headers=headers, data=decrypted_line_protocol, timeout=5)
```

---

### 4.4 Monitoring Dashboard

Dashboard dibangun dengan **Streamlit** dan di-deploy di **Google Cloud Run**, dapat diakses publik di:

> 🌐 **https://room-monitoring-476404504908.asia-southeast2.run.app**

Dashboard memiliki 3 halaman utama:

#### 📈 Halaman Monitoring
- **Nilai sensor real-time** — Suhu, kelembapan, cahaya, daya listrik
- **Kartu status** — Kondisi ruangan (Nyaman / Panas / Gelap dll)
- **Grafik historis** — Time-series 7 hari terakhir dengan selector rentang waktu
- **Waktu pembaruan terakhir** — Ditampilkan di setiap kartu sensor
- **Auto-refresh** — Halaman refresh otomatis setiap 5 menit

#### 🛡️ Halaman Security & Logs
- **Forensik Log** — Semua aktivitas gateway (INFO / WARNING / CRITICAL)
- **Connected Devices** — Status online/offline semua device yang pernah login
- **IP Blocked List** — Daftar IP yang diblokir IDS

#### ⚙️ Halaman Settings
- Konfigurasi email alert (SMTP)
- Toggle mode keamanan (untuk demonstrasi)
- Reset IP block list

---

### 4.5 Integrasi Sistem

Alur end-to-end sistem berjalan sebagai berikut:

```
┌─────────────────────────────────────────────────────────────┐
│                     ALUR LENGKAP SISTEM                     │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│  SENSOR  │  IoT     │ INTERNET │  CLOUD   │   PENGGUNA     │
│          │ DEVICE   │          │          │                │
│ DHT22    │          │          │          │                │
│ LDR      │ Pico W   │ Pinggy   │InfluxDB  │  Dashboard     │
│ PIR      │ Firmware │ HTTPS    │ Cloud    │  Streamlit     │
│          │ MicroPy  │ Tunnel   │ (AWS)    │  Cloud Run     │
│          │          │          │          │                │
│  Read    │ Encrypt  │  POST    │  Store   │  Visualize     │
│ sensor   │ XOR Hex  │ /write   │ Line     │  Real-time     │
│ tiap 15s │ + Auth   │ Bearer   │ Protocol │  + Historis    │
└──────────┴──────────┴──────────┴──────────┴────────────────┘
     1           2          3          4            5
```

**Verifikasi integrasi (curl test):**
```bash
# Test endpoint gateway via Cloud Run
curl -X POST https://room-monitoring-476404504908.asia-southeast2.run.app/write \
  -H "Authorization: Bearer token_aman_smartroom_2026" \
  -H "X-Device-ID: PICO-W-CLASS-A" \
  -H "Content-Type: application/json" \
  -d '{"encrypted_data": "212c2933..."}'

# Response:
# {"status": "ok", "code": 204}  HTTP 200 ✅
```

---

## 5. Screenshot Dashboard

### Halaman Monitoring — Nilai Sensor Real-time

> 📸 *[SCREENSHOT — Halaman monitoring dengan kartu suhu/kelembapan/cahaya/daya + grafik]*

---

### Grafik Historis 7 Hari

> 📸 *[SCREENSHOT — Grafik time-series suhu dan kelembapan 7 hari terakhir]*

---

### Status Perangkat (Connected Devices)

> 📸 *[SCREENSHOT — Panel connected devices menampilkan PICO-W-CLASS-A online]*

---

### Forensik Log Keamanan

> 📸 *[SCREENSHOT — Log INFO/WARNING/CRITICAL dari aktivitas gateway]*

---

### Serial Monitor Wokwi — Data Terkirim

> 📸 *[SCREENSHOT — Output Wokwi menampilkan "✅ Data sukses dikirim ke InfluxDB"]*

---

### Wiring Diagram Wokwi

> 📸 *[SCREENSHOT — Diagram rangkaian Pico W dengan DHT22, LDR, PIR, LCD di Wokwi]*

---

## 6. Cara Menjalankan

### Akses Dashboard Online (Sudah Deploy)

```
Buka browser → https://room-monitoring-476404504908.asia-southeast2.run.app
Login: admin / admin_password_2026
```

### Jalankan Lokal (untuk Pengembangan)

```bash
# Clone repo
git clone https://github.com/Vereniaes/room-monitoring.git
cd room-monitoring

# Buat file .env
cp .env.example .env
# Isi INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET

# Install dependencies
pip install -r requirements.txt

# Terminal 1 — API Gateway
python3 api_gateway.py

# Terminal 2 — Pinggy tunnel (expose gateway ke internet untuk Wokwi)
ssh -p 443 -R0:localhost:5000 a.pinggy.io
# Salin URL HTTPS → update GATEWAY_URL di iot-code/main_secure.py

# Terminal 3 — Dashboard
streamlit run dashboard/dashboard.py
```

### Jalankan Simulasi IoT (Wokwi)

1. Buka https://wokwi.com/projects/[PROJECT_ID]
2. Update `GATEWAY_URL` di `main.py` dengan URL Pinggy terbaru
3. Klik **Run** → lihat output di Serial Monitor

---

## 7. Kesimpulan

Sistem **Smart Room IoT Monitoring** berhasil mengimplementasikan seluruh alur IoT end-to-end:

| Requirement | Implementasi | Status |
|-------------|-------------|--------|
| **Akuisisi Data** | DHT22 (suhu/kelembapan), LDR (cahaya), PIR (gerak) di Pico W | ✅ |
| **Konektivitas Internet** | HTTPS POST otomatis tiap 15 detik via Pinggy + Bearer Token auth | ✅ |
| **Penyimpanan Cloud** | InfluxDB Cloud (AWS) dengan Line Protocol, retensi 30 hari | ✅ |
| **Monitoring Dashboard** | Streamlit di Google Cloud Run — real-time, grafik, status device | ✅ |
| **Integrasi Sistem** | Sensor → Pico W → Pinggy → Gateway → InfluxDB → Dashboard → User | ✅ |

Sistem ini tidak hanya memenuhi kebutuhan monitoring dasar, tetapi juga mengimplementasikan lapisan keamanan IoT meliputi:
- Enkripsi payload XOR Hex sebelum data meninggalkan device
- Autentikasi Bearer Token + Device ID di setiap request
- Intrusion Detection System (IDS) dengan auto-block IP
- Notifikasi email otomatis untuk setiap event keamanan
- Login dashboard dengan hash SHA-256 dan lockout 3 kali percobaan

Dengan arsitektur yang modular dan deployment di cloud, sistem dapat diperluas untuk memantau lebih banyak ruangan kampus hanya dengan menambahkan device IoT baru dan mendaftarkan Device ID-nya ke gateway.

---

## 📁 Struktur File

```
iot-room/
├── iot-code/
│   ├── main.py              ← Firmware baseline (tanpa keamanan, untuk perbandingan)
│   ├── main_secure.py       ← Firmware utama dengan full security layer
│   ├── i2c_lcd.py           ← Driver LCD I2C
│   ├── lcd_api.py           ← LCD API
│   └── diagram.json         ← Wiring diagram Wokwi
├── dashboard/
│   ├── dashboard.py         ← Web Dashboard Streamlit (3 halaman)
│   └── data_sensor_*.txt    ← Data historis untuk upload awal
├── api_gateway.py           ← Flask API Gateway (Auth + IDS + Decrypt + Forward)
├── email_helper.py          ← SMTP email helper dengan Mock fallback
├── attack_simulator.py      ← Simulator serangan siber untuk demonstrasi
├── cloudflare-worker.js     ← Cloudflare Worker proxy (alternatif Pinggy)
├── nginx.conf               ← Reverse proxy config (gateway + dashboard)
├── Dockerfile               ← Container image untuk Cloud Run
├── start.sh                 ← Startup script (nginx + gunicorn + streamlit)
├── settings.json            ← Konfigurasi email dari halaman Settings
├── requirements.txt         ← Python dependencies
└── README.md                ← Dokumentasi ini
```

---

*Smart Room IoT Monitoring System · Universitas Negeri Jakarta · 2026*
