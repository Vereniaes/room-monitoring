import network
import urequests as requests
from machine import ADC, Pin, I2C
from time import sleep
import dht
from i2c_lcd import I2cLcd

# ======
# CHECKLIST A: MQTT Authentication (TIDAK DITERAPKAN - VULNERABLE BASELINE)
# - Username & password broker MQTT: TIDAK ADA
# - Role-based topic access: TIDAK ADA
# - ACL (Access Control List): TIDAK ADA
# KONDISI: Konfigurasi WiFi polos tanpa proteksi jaringan tambahan
# ======
# --- KONFIGURASI WIFI (TANPA KEAMANAN) ---
ssid = "Wokwi-GUEST"
password = ""  # Open network - tidak ada password WiFi (WPA2/WPA3 tidak aktif)
# =======
# DONE CHECKLIST A (MQTT Auth - NOT IMPLEMENTED - VULNERABLE)
# =======

# ======
# CHECKLIST A: API Security (TIDAK DITERAPKAN - VULNERABLE BASELINE)
# - API Key validation: TIDAK ADA - menggunakan plain password di header
# - Bearer Token / JWT: TIDAK ADA
# - Expired session token: TIDAK ADA
# KONDISI: Data dikirim via HTTP biasa (rentan disadap / man-in-the-middle attack)
# ======
# 1. Menggunakan HTTP biasa (Bukan HTTPS - rentan disadap)
INFLUX_URL = "http://xxxjg-203-17-85-134.run.pinggy-free.link/api/v2/write?org=IOT&bucket=data_sensor&precision=s"

# 2. Password Default yang sangat lemah (admin123) / Tanpa Token Valid
PASSWORD_DEFAULT = "admin123"
# =======
# DONE CHECKLIST A (API Security - NOT IMPLEMENTED - VULNERABLE)
# =======

# ======
# CHECKLIST A: Device Authentication (TIDAK DITERAPKAN - VULNERABLE BASELINE)
# - Device ID validation: TIDAK ADA - siapapun bisa mengirim data ke server
# - MAC address verification: TIDAK ADA
# - Token pairing antar device: TIDAK ADA
# ======
# Tidak ada mekanisme identifikasi device - server tidak tahu data berasal dari device mana
# =======
# DONE CHECKLIST A (Device Auth - NOT IMPLEMENTED - VULNERABLE)
# =======

# ======
# CHECKLIST B: HTTPS / SSL/TLS (TIDAK DITERAPKAN - VULNERABLE BASELINE)
# - HTTPS pada web dashboard: TIDAK ADA - menggunakan HTTP plain text
# - TLS pada MQTT broker: TIDAK ADA
# KONDISI: Semua data terbang di udara tanpa enkripsi (mudah di-sniffing)
# ======
# Lihat INFLUX_URL di atas - menggunakan HTTP bukan HTTPS
# =======
# DONE CHECKLIST B (HTTPS/TLS - NOT IMPLEMENTED - VULNERABLE)
# =======

# ======
# CHECKLIST B: Payload Encryption (TIDAK DITERAPKAN - VULNERABLE BASELINE)
# - AES encryption: TIDAK ADA
# - Enkripsi data sensor sebelum dikirim: TIDAK ADA
# KONDISI: Data sensor dikirim dalam format plain text yang bisa dibaca siapapun
# ======
# Tidak ada fungsi enkripsi - data langsung dikirim apa adanya
# =======
# DONE CHECKLIST B (Payload Encryption - NOT IMPLEMENTED - VULNERABLE)
# =======

# --- INISIALISASI SENSOR & OUTPUT ---
ldr = ADC(Pin(28))               # LDR sensor di GP28
dht_sensor = dht.DHT22(Pin(5))   # DHT22 sensor di GP5
pir = Pin(4, Pin.IN)             # PIR sensor di GP4
led = Pin(3, Pin.OUT)            # LED di GP3 (Mensimulasikan Lampu Gedung)
buzzer = Pin(6, Pin.OUT)         # Buzzer di GP6

i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=400000)
lcd = I2cLcd(i2c, 0x27, 2, 16)   

# ======
# CHECKLIST B: Secure WiFi Layer (TIDAK DITERAPKAN - VULNERABLE BASELINE)
# - WPA2/WPA3: TIDAK ADA - menggunakan Wokwi-GUEST open network
# - Hidden SSID + strong password: TIDAK ADA
# ======
def connect_wifi():
    """Koneksi WiFi tanpa keamanan - VULNERABLE STATE untuk demonstrasi."""
    lcd.clear()
    lcd.putstr("Connecting WiFi.")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while not wlan.isconnected():
        sleep(1)
        print(".", end="")
    print("\n[OK] WiFi Connected!")
    lcd.clear()
    lcd.putstr("WiFi Connected!")
    sleep(2)
# =======
# DONE CHECKLIST B (Secure WiFi - NOT IMPLEMENTED - VULNERABLE)
# =======

def check_sensors():
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        hum = dht_sensor.humidity()
    except Exception:
        temp = hum = None  
    ldr_val = ldr.read_u16()
    pir_event = pir.value()
    return temp, hum, ldr_val, pir_event

connect_wifi()

while True:
    temp, hum, ldr_val, pir_event = check_sensors()
    is_dark = ldr_val < 20000     
    motion = pir_event == 1
    daya_listrik = 3500.0 if motion else 250.0

    led.value(is_dark)           
    buzzer.value(motion)  

    lcd.clear()
    if temp is not None:
        lcd.putstr("T:{:.1f}C H:{:.0f}%".format(temp, hum))
    else:
        lcd.putstr("DHT ERROR")
    lcd.move_to(0, 1)
    lcd.putstr(("L" if not is_dark else "D") + (" M" if motion else "  "))

    print("-" * 50)
    print("📍 Lokasi: Ruang_Kelas_A (NO SECURITY MODE - VULNERABLE)")
    
    if temp is not None:
        # ======
        # CHECKLIST A: API Security (DEMONSTRASI KERENTANAN)
        # - Menggunakan plain password di custom header (bukan Bearer Token)
        # - Server yang aman akan menolak ini dengan HTTP 401 Unauthorized
        # - Ini adalah BUKTI bahwa sistem tanpa keamanan akan ditolak / mudah disadap
        # ======
        headers = {
            "Password-Login": PASSWORD_DEFAULT,  # ❌ Kirim password plain - sangat berbahaya!
            "Content-Type": "text/plain; charset=utf-8",
            "Accept": "application/json"
        }
        # =======
        # DONE CHECKLIST A (API Security demo vulnerability)
        # =======
        
        # ======
        # CHECKLIST B: Payload Encryption (DEMONSTRASI KERENTANAN)
        # - Data sensor dikirim dalam format plain text Line Protocol
        # - Siapapun yang men-sniffing paket HTTP bisa membaca semua nilai sensor
        # ======
        data_influx = "smart_room,lokasi=Ruang_Kelas_A suhu={},kelembaban={},cahaya={},gerakan={},daya_listrik={}".format(
            temp, hum, ldr_val, pir_event, daya_listrik
        )
        # =======
        # DONE CHECKLIST B (Payload Encryption demo vulnerability)
        # =======
        
        print("\n>> ❌ Mengirim Data Tanpa Enkripsi (HTTP Plain Text) - VULNERABLE...")
        print("   Data terkirim:", data_influx)
        try:
            res_in = requests.post(INFLUX_URL, headers=headers, data=data_influx)
            print(">> Status HTTP:", res_in.status_code)
            
            # ======
            # CHECKLIST C: Activity Logging (TIDAK ADA DI SISI DEVICE - VULNERABLE)
            # - Tidak ada pencatatan log waktu, IP, status
            # - Tidak ada alert jika koneksi gagal berulang kali
            # ======
            # Jika dijalankan, InfluxDB pasti akan menolak (Status 401 Unauthorized)
            # Ini adalah BUKTI BAGUS untuk laporan bahwa sistem yang rentan akan gagal!
            if res_in.status_code == 401:
                print("   ❌ [DITOLAK] Server menolak karena tidak ada autentikasi valid!")
                print("   ⚠️  Screenshot log ini sebagai BUKTI celah keamanan 'Login Tanpa Autentikasi'")
            # =======
            # DONE CHECKLIST C (Activity Logging - NOT IMPLEMENTED)
            # =======
                
            res_in.close()
        except Exception as e:
            print("   ❌ [ERROR]:", e)

    print("-" * 50)
    print("⚠️  PERINGATAN: Kode ini adalah BASELINE RENTAN untuk perbandingan!")
    print("   Gunakan main_secure.py untuk firmware yang aman.")
    sleep(15)