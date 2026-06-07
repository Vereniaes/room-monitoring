"""
generate_minggu_pagi.py

-> generate + upload data sensor untuk hari Minggu pagi ke InfluxDB Cloud
-> skenario: gedung kosong, tidak ada aktivitas (libur Minggu)
-> pola data:
     - gerakan     = 0        (tidak ada orang)
     - daya_listrik = 180-260W (standby mode, bukan full load)
     - cahaya      = naik bertahap (matahari pagi)
     - suhu        = 26-30°C  (pagi, bertahap naik)
     - kelembaban  = 70-85%   (pagi hari lebih lembab)
-> interval: tiap 5 menit
-> waktu: dari 2 jam lalu sampai sekarang (atau bisa di-set manual)

cara pakai:
    python3 generate_minggu_pagi.py
    python3 generate_minggu_pagi.py --hours 4   <- generate 4 jam ke belakang
    python3 generate_minggu_pagi.py --start "06:00" --end "12:00"  <- range spesifik hari ini
"""

import os
import sys
import math
import random
import argparse
import datetime
from pathlib import Path

# ======
# Load .env
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

INFLUXDB_URL    = os.environ.get("INFLUXDB_URL", "")
INFLUXDB_TOKEN  = os.environ.get("INFLUXDB_TOKEN", "")
INFLUXDB_ORG    = os.environ.get("INFLUXDB_ORG", "")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET", "")
DUMMY_FILE      = Path(__file__).parent / "dashboard" / "data_sensor_1_minggu_lineprotocol.txt"

LOKASI = "Ruang_Kelas_A"

# ======
# helper: generate nilai sensor realistis untuk Minggu pagi
# ======

def _suhu(hour: float) -> float:
    # Pagi awal 26°C, naik sekitar 0.5°C per jam sampai siang
    base = 26.0 + (hour - 6) * 0.55
    return round(base + random.uniform(-0.3, 0.3), 1)

def _kelembaban(hour: float) -> float:
    # Pagi lembab ~80%, turun pelan ke ~68% saat siang
    base = 82 - (hour - 6) * 1.8
    return round(max(60, min(90, base + random.uniform(-2, 2))))

def _cahaya(hour: float) -> float:
    # Gelap dini hari, naik saat matahari terbit
    # sunrise sekitar jam 06:00, full bright jam 10:00
    if hour < 6.0:
        val = 500 + random.uniform(-100, 200)
    elif hour < 10.0:
        # naik dari 2000 ke 45000
        progress = (hour - 6.0) / 4.0
        val = 2000 + progress * 43000 + random.uniform(-500, 500)
    else:
        val = 45000 + random.uniform(-1000, 1000)
    return round(max(0, val))

def _daya_listrik() -> float:
    # Hari Minggu pagi, gedung kosong — hanya standby (CCTV, router, lampu darurat)
    # Tidak ada AC, tidak ada PC menyala, tidak ada orang
    base = random.choice([185.0, 190.0, 195.0, 200.0, 215.0, 220.0, 250.0])
    return round(base + random.uniform(-10, 10), 1)

def generate_data_points(start_dt: datetime.datetime, end_dt: datetime.datetime, interval_minutes: int = 5):
    """Generate list data points dari start_dt ke end_dt tiap interval menit."""
    points = []
    current = start_dt
    while current <= end_dt:
        hour = current.hour + current.minute / 60.0
        ts = int(current.timestamp())
        suhu = _suhu(hour)
        kelembaban = _kelembaban(hour)
        cahaya = _cahaya(hour)
        gerakan = 0          # tidak ada orang
        daya = _daya_listrik()

        # format Line Protocol
        line = (
            f"smart_room,lokasi={LOKASI} "
            f"suhu={suhu},kelembaban={kelembaban},"
            f"cahaya={cahaya},gerakan={gerakan},"
            f"daya_listrik={daya} "
            f"{ts}"
        )
        points.append((current, line))
        current += datetime.timedelta(minutes=interval_minutes)
    return points

# ======
# upload ke InfluxDB Cloud
# ======

def upload_to_influxdb(lines: list[str]):
    try:
        from influxdb_client import InfluxDBClient
        from influxdb_client.client.write_api import SYNCHRONOUS
    except ImportError:
        print("❌ influxdb-client belum terinstall: pip install influxdb-client")
        sys.exit(1)

    if not all([INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET]):
        print("❌ Kredensial InfluxDB tidak lengkap di .env")
        sys.exit(1)

    print(f"\n🔌 Konek ke InfluxDB Cloud...")
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG, timeout=15_000)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    BATCH = 50
    uploaded = 0
    for i in range(0, len(lines), BATCH):
        batch = lines[i : i + BATCH]
        write_api.write(
            bucket=INFLUXDB_BUCKET,
            org=INFLUXDB_ORG,
            record="\n".join(batch),
            write_precision="s"
        )
        uploaded += len(batch)
        pct = uploaded / len(lines) * 100
        print(f"   [{pct:5.1f}%] {uploaded}/{len(lines)} records...", end="\r")

    client.close()
    print(f"\n✅ Upload ke InfluxDB Cloud selesai: {uploaded} records")

# ======
# append ke file dummy lokal
# ======

def append_to_dummy_file(lines: list[str]):
    with open(DUMMY_FILE, "a") as f:
        for line in lines:
            f.write(line + "\n")
    print(f"✅ Append ke dummy file: {len(lines)} records → {DUMMY_FILE}")

# ======
# main
# ======

def main():
    parser = argparse.ArgumentParser(description="Generate data sensor Minggu pagi (gedung kosong)")
    parser.add_argument("--hours", type=float, default=2.0,
                        help="Jumlah jam ke belakang dari sekarang (default: 2)")
    parser.add_argument("--start", type=str, default=None,
                        help="Waktu mulai format HH:MM hari ini, misal 06:00")
    parser.add_argument("--end", type=str, default=None,
                        help="Waktu selesai format HH:MM hari ini, misal 12:00")
    parser.add_argument("--interval", type=int, default=5,
                        help="Interval antar data dalam menit (default: 5)")
    parser.add_argument("--dummy-only", action="store_true",
                        help="Hanya append ke file dummy lokal, tidak upload ke InfluxDB")
    args = parser.parse_args()

    now = datetime.datetime.now()
    today = now.date()

    if args.start and args.end:
        start_h, start_m = map(int, args.start.split(":"))
        end_h, end_m = map(int, args.end.split(":"))
        start_dt = datetime.datetime(today.year, today.month, today.day, start_h, start_m)
        end_dt   = datetime.datetime(today.year, today.month, today.day, end_h, end_m)
    else:
        end_dt   = now.replace(second=0, microsecond=0)
        start_dt = end_dt - datetime.timedelta(hours=args.hours)

    print("=" * 55)
    print("  Generate Data Sensor — Minggu Pagi (Gedung Kosong)")
    print("=" * 55)
    print(f"  Dari    : {start_dt.strftime('%d %b %Y %H:%M')}")
    print(f"  Sampai  : {end_dt.strftime('%d %b %Y %H:%M')}")
    print(f"  Interval: setiap {args.interval} menit")
    print(f"  Pola    : gerakan=0, daya standby ~180-260W, cahaya pagi")

    points = generate_data_points(start_dt, end_dt, interval_minutes=args.interval)
    if not points:
        print("❌ Tidak ada data yang bisa di-generate (cek range waktu)")
        sys.exit(1)

    lines = [lp for _, lp in points]
    total = len(lines)
    print(f"\n📊 Total data yang akan di-generate: {total} records")

    # Preview 3 baris pertama
    print("\nPreview 3 data pertama:")
    for i, (dt, lp) in enumerate(points[:3]):
        print(f"  [{dt.strftime('%H:%M')}] {lp[:80]}...")

    print()
    if args.dummy_only:
        append_to_dummy_file(lines)
    else:
        # Upload ke InfluxDB Cloud DAN append ke dummy file
        upload_to_influxdb(lines)
        append_to_dummy_file(lines)

    print(f"\n{'='*55}")
    print("  Selesai! Refresh dashboard untuk lihat data baru.")
    print(f"{'='*55}")

if __name__ == "__main__":
    main()
