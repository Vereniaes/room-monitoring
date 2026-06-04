import time
import requests

BASE_URL = "http://localhost:5000"

def print_header(title):
    print("\n" + "=" * 60)
    print(f"🔥 SIMULASI SERANGAN SIBER: {title}")
    print("=" * 60)

def simulate_unauthorized_access():
    print_header("Akses Kontrol Lampu Kampus Tanpa Autentikasi")
    
    print("\n[INFO] Skenario: Hacker dari IP luar mencoba menyalakan lampu seluruh gedung kampus pada pukul 02.00 pagi.")
    print("[LANGKAH 1] Mengirim request perubahan lampu ke '/set_light?state=on' TANPA TOKEN...")
    
    try:
        # Kirim request tanpa header Authorization
        res = requests.post(f"{BASE_URL}/set_light?state=on")
        print(f"[HTTP RESPONSE] Status Code: {res.status_code}")
        print(f"[RESPONSE BODY] {res.json()}")
        
        if res.status_code == 200:
            print("\n🚨 [HASIL SERANGAN] SUKSES! Lampu gedung menyala tanpa izin. Sistem rentan (Sebelum Keamanan)!")
        else:
            print("\n🛡️  [HASIL PERTAHANAN] DITOLAK! API Gateway memblokir perubahan lampu karena tidak terotentikasi.")
    except Exception as e:
        print(f"❌ Gagal menyambung ke server API Gateway: {e}")

def simulate_brute_force():
    print_header("Percobaan Serangan Brute-Force Token API")
    print("\n[INFO] Skenario: Penyusup mencoba menembak data sensor palsu menggunakan token tebakan secara berturut-turut.")
    print("[LANGKAH] Mengirim 4 data sensor palsu berturut-turut dengan token acak...")
    
    fake_tokens = ["admin123", "password_dosen", "token_palsu_999", "hacker_pro_2026"]
    
    for i, token in enumerate(fake_tokens, 1):
        print(f"\n⚡ Percobaan #{i}: Menggunakan token '{token}'")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {"encrypted_data": "4f0b121e03"}  # Hex dummy
        
        try:
            res = requests.post(f"{BASE_URL}/write", headers=headers, json=payload)
            print(f"   [HTTP RESPONSE] Status Code: {res.status_code}")
            print(f"   [RESPONSE BODY] {res.json()}")
            
            if res.status_code == 403:
                print("   🛡️  [IDS ACTION] Sistem mendeteksi Brute-Force! IP Anda sekarang resmi DIBLOKIR permanen!")
                break
        except Exception as e:
            print(f"   ❌ Gagal menyambung ke server: {e}")
            break
        time.sleep(1)

def toggle_security_mode():
    print_header("Ubah Mode Keamanan (Toggle Security Mode)")
    try:
        res = requests.post(f"{BASE_URL}/toggle_security")
        print(f"[HTTP RESPONSE] Status Code: {res.status_code}")
        print(f"[STATUS SEKARANG] {res.json()['status']}")
    except Exception as e:
        print(f"❌ Gagal menyambung ke server: {e}")

def reset_blocked_ips():
    print_header("Reset Daftar Blokir IP (Unblock All)")
    try:
        res = requests.post(f"{BASE_URL}/unblock_ips")
        print(f"[HTTP RESPONSE] Status Code: {res.status_code}")
        print(f"[STATUS] {res.json()['message']}")
    except Exception as e:
        print(f"❌ Gagal menyambung ke server: {e}")

def main():
    while True:
        print("\n" + "=" * 50)
        print("🛡️  MENU SIMULASI SERANGAN IOT (LK 5)")
        print("=" * 50)
        print("1. [SERANGAN A] Nyalakan Lampu Gedung Tanpa Token (Akses Ilegal)")
        print("2. [SERANGAN B] Brute-Force Token API (Intrusion Detection)")
        print("3. [KONTROL] Aktifkan / Matikan Mode Keamanan Gateway")
        print("4. [KONTROL] Reset Seluruh Blokir IP / Unblock")
        print("5. Keluar")
        print("-" * 50)
        choice = input("Pilih menu (1-5): ")
        
        if choice == "1":
            simulate_unauthorized_access()
        elif choice == "2":
            simulate_brute_force()
        elif choice == "3":
            toggle_security_mode()
        elif choice == "4":
            reset_blocked_ips()
        elif choice == "5":
            print("\nTerima kasih! Tetap amankan sistem IoT Anda.")
            break
        else:
            print("Pilihan tidak valid.")

if __name__ == "__main__":
    main()
