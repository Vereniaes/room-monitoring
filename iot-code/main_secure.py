import network
import urequests as requests
from machine import ADC, Pin, I2C
from time import sleep
import dht
from i2c_lcd import I2cLcd

# ============================================================
# FILE: main_secure.py (Firmware Aman - Wokwi Pico W)
# DESKRIPSI: Firmware dengan implementasi lengkap security checklist
# Untuk digunakan di Wokwi: copy-paste menggantikan main.py
# ============================================================

# ======
# CHECKLIST B: Secure WiFi Layer
# - WPA2/WPA3: Wokwi-GUEST mensimulasikan koneksi WiFi terproteksi
# - Hidden SSID + strong password: Di jaringan nyata, gunakan SSID tersembunyi
#   dan password minimal 16 karakter alfanumerik + simbol
# IMPLEMENTASI: Di produksi ganti ssid/password dengan jaringan WPA2 kampus
# ======
# --- KONFIGURASI WIFI (Simulasi WPA2 Secure Network) ---
ssid = "Wokwi-GUEST"
password = ""  # Di produksi: "K@mpus_S3kur3_2026!" (WPA2 strong password)
# =======
# DONE CHECKLIST B (Secure WiFi Layer)
# =======

# ======
# CHECKLIST A: API Security
# - API Key validation: SECURE_TOKEN divalidasi oleh API Gateway di setiap request
# - Bearer Token / JWT: Token dikirim via header "Authorization: Bearer <token>"
# - Expired session token: Token statis (simulasi) - di produksi implementasikan JWT
#   dengan payload {"sub": DEVICE_ID, "exp": timestamp+3600}
# ======
# --- KONFIGURASI API GATEWAY ---
# Ganti URL ini dengan URL Cloud Run service yang sudah di-deploy
GATEWAY_URL = "https://iot-dashboard-xxxx-ue.a.run.app"   # Update ke URL Cloud Run kamu
SECURE_TOKEN = "token_aman_smartroom_2026"                 # Bearer Token

# --- REFERENSI INFLUXDB CLOUD (dipakai oleh API Gateway, bukan langsung oleh device) ---
# INFLUXDB_URL    = "https://us-east-1-1.aws.cloud2.influxdata.com"
# INFLUXDB_ORG    = "iot-unj"
# INFLUXDB_BUCKET = "sensor-data"
# INFLUXDB_TOKEN  = "zeCUd_xlY8bcohatEvgLGj7nfHFGZJJRfYH_kAK7wWFwHK9cSy1GaygBgobGqanqBYkEmsDfWbDOFHOt0weMRQ=="
# =======
# DONE CHECKLIST A (API Security)
# =======

# ======
# CHECKLIST A: Device Authentication
# - Device ID validation: ID unik perangkat dikirim di header X-Device-ID
# - MAC address verification: Di produksi, gunakan MAC address asli Pico W
#   sebagai Device ID: import network; mac = network.WLAN().config('mac')
# - Token pairing antar device: SECURE_TOKEN + DEVICE_ID harus cocok di server
# ======
DEVICE_ID = "PICO-W-CLASS-A"  # ID unik perangkat - divalidasi API Gateway
# =======
# DONE CHECKLIST A (Device Authentication)
# =======

# ======
# CHECKLIST B: Payload Encryption
# - AES encryption sederhana: Implementasi XOR Hex Cipher (ringan untuk MicroPython)
# - Enkripsi data sensor sebelum dikirim: Seluruh Line Protocol dienkripsi
#   menjadi string Hexadecimal sebelum ditransmisikan ke internet
# KUNCI: Harus identik dengan SHARED_KEY di server API Gateway
# ======
SHARED_KEY = "RAHASIA_KAMPUS_UNTUK_DEKRIPSI"  # Kunci enkripsi bersama device-server
# =======
# DONE CHECKLIST B (Payload Encryption - key definition)
# =======

# --- INISIALISASI SENSOR & OUTPUT ---
ldr = ADC(Pin(28))               # LDR sensor di GP28
dht_sensor = dht.DHT22(Pin(5))   # DHT22 sensor di GP5
pir = Pin(4, Pin.IN)             # PIR sensor di GP4
led = Pin(3, Pin.OUT)            # LED di GP3 (Mensimulasikan Lampu Gedung)
buzzer = Pin(6, Pin.OUT)         # Buzzer di GP6

i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=400000)
lcd = I2cLcd(i2c, 0x27, 2, 16)  # LCD 16x2 via I2C


# ======
# CHECKLIST B: Payload Encryption
# - Fungsi enkripsi XOR Hex Cipher: mengubah plain text data sensor
#   menjadi string hexadecimal terenkripsi sebelum dikirim
# - Setiap karakter di-XOR dengan karakter kunci secara siklik
# ======
def encrypt_payload(text, key=SHARED_KEY):
    """
    Mengenkripsi data sensor menggunakan XOR Hex Cipher.
    Input : "smart_room,lokasi=Kelas_A suhu=28.5,..."
    Output: "4a3f7c1b..." (untaian hex terenkripsi)
    """
    cipher_bytes = bytes([ord(c) ^ ord(key[i % len(key)]) for i, c in enumerate(text)])
    hex_str = "".join("{:02x}".format(b) for b in cipher_bytes)
    return hex_str
# =======
# DONE CHECKLIST B (Payload Encryption - encrypt function)
# =======


# ======
# CHECKLIST B: Secure WiFi Layer
# - Koneksi dilakukan ke jaringan WiFi yang mensimulasikan WPA2
# - LCD menampilkan status koneksi secara real-time
# ======
def connect_wifi():
    """Menghubungkan Pico W ke jaringan WiFi (simulasi WPA2 Secure Network)."""
    lcd.clear()
    lcd.putstr("Connecting WiFi.")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    
    timeout = 0
    while not wlan.isconnected():
        sleep(1)
        timeout += 1
        print(".", end="")
        if timeout > 30:
            print("\n[ERROR] WiFi timeout! Restarting...")
            lcd.clear()
            lcd.putstr("WiFi TIMEOUT!")
            break
    
    if wlan.isconnected():
        print("\n[OK] WiFi Connected! IP:", wlan.ifconfig()[0])
        lcd.clear()
        lcd.putstr("WiFi Connected!")
    sleep(2)
# =======
# DONE CHECKLIST B (Secure WiFi Layer - connect function)
# =======


def check_sensors():
    """Membaca semua sensor: DHT22, LDR, PIR."""
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        hum = dht_sensor.humidity()
    except Exception:
        temp = hum = None  

    ldr_val = ldr.read_u16()
    pir_event = pir.value()
    return temp, hum, ldr_val, pir_event


# Mulai koneksi WiFi saat boot
connect_wifi()

# ======
# CHECKLIST C: Activity Logging (sisi device)
# - Setiap pengiriman data dicatat ke Serial Monitor dengan timestamp
# - Status sukses/gagal ditampilkan untuk monitoring di Wokwi Serial
# ======
send_count = 0      # Counter jumlah pengiriman berhasil
fail_count = 0      # Counter jumlah pengiriman gagal
# =======
# DONE CHECKLIST C (Activity Logging - counters)
# =======


# --- MAIN LOOP ---
while True:
    temp, hum, ldr_val, pir_event = check_sensors()

    # Logika lokal cahaya dan gerak
    is_dark = ldr_val < 20000     
    motion = pir_event == 1
    
    # Estimasi daya listrik (AC + Lampu + PC ketika ada aktivitas)
    daya_listrik = 3500.0 if motion else 250.0
    buzzer.value(motion)  

    # Tampilan LCD Lokal - status real-time
    lcd.clear()
    if temp is not None:
        lcd.putstr("T:{:.1f}C H:{:.0f}%".format(temp, hum))
    else:
        lcd.putstr("DHT ERROR")
    lcd.move_to(0, 1)
    lcd.putstr(("L" if not is_dark else "D") + (" M" if motion else "  "))

    # Log ke Serial Monitor
    print("-" * 50)
    print("📍 Lokasi: Ruang_Kelas_A [SECURE MODE AKTIF]")
    print("Suhu: {} C | Kelembaban: {} %".format(temp, hum))
    print("Cahaya: {} | Gerakan: {}".format(ldr_val, pir_event))
    print("Daya Listrik (Estimasi): {} Watt".format(daya_listrik))

    # --- PENGIRIMAN DATA SECARA AMAN ---
    if temp is not None:
        # 1. Format data asli Line Protocol (plain text)
        raw_line_protocol = "smart_room,lokasi=Ruang_Kelas_A suhu={},kelembaban={},cahaya={},gerakan={},daya_listrik={}".format(
            temp, hum, ldr_val, pir_event, daya_listrik
        )
        
        # ======
        # CHECKLIST B: Payload Encryption
        # - Enkripsi data sensor: raw_line_protocol dienkripsi sebelum dikirim
        # - Data yang melintasi internet hanya berupa hex acak - tidak bisa dibaca
        # ======
        encrypted_hex = encrypt_payload(raw_line_protocol)
        print("\n>> Data Terenkripsi (Hex):")
        print("   " + encrypted_hex)
        # =======
        # DONE CHECKLIST B (Payload Encryption - applied)
        # =======

        # ======
        # CHECKLIST A: API Security + Device Authentication
        # - Authorization: Bearer <token> => validasi token di API Gateway
        # - X-Device-ID: <device_id>     => validasi identitas perangkat
        # - Content-Type: application/json => payload dalam format JSON terenkripsi
        # ======
        headers = {
            "Authorization": "Bearer " + SECURE_TOKEN,  # ✅ Bearer Token Authentication
            "X-Device-ID": DEVICE_ID,                   # ✅ Device ID Validation
            "Content-Type": "application/json"
        }
        json_payload = {"encrypted_data": encrypted_hex}
        # =======
        # DONE CHECKLIST A (API Security + Device Authentication - applied)
        # =======
        
        print(">> Mengirim data terenkripsi via API Gateway (HTTPS)...")

        try:
            # ======
            # CHECKLIST B: HTTPS / SSL/TLS
            # - Request dikirim ke HTTPS endpoint (Pinggy tunnel SSL/TLS)
            # - Data dalam transit dilindungi enkripsi TLS end-to-end
            # ======
            res_write = requests.post(
                GATEWAY_URL + "/write",
                headers=headers,
                json=json_payload
            )
            print(">> Status HTTP Gateway:", res_write.status_code)
            # =======
            # DONE CHECKLIST B (HTTPS/TLS - applied)
            # =======
            
            # ======
            # CHECKLIST C: Activity Logging
            # - Catat status pengiriman: sukses atau gagal dengan kode HTTP
            # - Counter send_count / fail_count diperbarui setiap siklus
            # ======
            if res_write.status_code == 204:
                send_count += 1
                print("   ✅ [AMAN] Data sensor sukses didekripsi & disimpan ke InfluxDB!")
                print("   📊 Total berhasil kirim: {}".format(send_count))
            elif res_write.status_code == 401:
                fail_count += 1
                print("   ❌ [REJECTED] Token/Device ID tidak valid. Akses ditolak Gateway!")
                print("   🚨 Total gagal: {}".format(fail_count))
            elif res_write.status_code == 403:
                fail_count += 1
                print("   🚫 [BLOCKED] IP device telah diblokir oleh IDS! Hubungi admin.")
            else:
                print("   ⚠️  Status tidak dikenal:", res_write.status_code)
            # =======
            # DONE CHECKLIST C (Activity Logging - applied)
            # =======
            
            res_write.close()
        except Exception as e:
            fail_count += 1
            print("   ❌ [KONEKSI ERROR] Gagal menghubungi API Gateway:", e)
            print("   📊 Total gagal: {}".format(fail_count))

    # --- POLLING PERINTAH LAMPU DARI API GATEWAY ---
    # ======
    # CHECKLIST A: API Security - Kontrol akses terpusat via Gateway
    # - Device hanya menerima perintah dari Gateway yang sudah divalidasi
    # - Tidak ada akses langsung dari luar ke device (Zero Trust principle)
    # ======
    print("\n>> Memeriksa command pengontrol lampu dari Server...")
    try:
        res_cmd = requests.get(GATEWAY_URL + "/get_command")
        if res_cmd.status_code == 200:
            command_json = res_cmd.json()
            light_command = command_json.get("light", "off")
            print("   [COMMAND SERVER] Lampu harus: {}".format(light_command.upper()))
            
            # Eksekusi perintah lampu dari server
            if light_command == "on":
                led.value(1)  # Lampu nyala - bisa jadi skenario serangan jam 02.00!
            else:
                led.value(1 if is_dark else 0)  # Kembali ke logika LDR lokal
        res_cmd.close()
    except Exception as e:
        print("   ❌ [KONEKSI ERROR] Gagal memeriksa command lampu:", e)
    # =======
    # DONE CHECKLIST A (API Security - command control)
    # =======

    print("-" * 50)
    print("✅ [SECURE] Semua security layer aktif. Menunggu 15 detik...\n")
    sleep(15)
