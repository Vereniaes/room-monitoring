"""
Script untuk upload data dummy 1 minggu ke InfluxDB Cloud.
Jalankan sekali saja: python upload_dummy_data.py
"""

import os
import sys
from pathlib import Path

# Load .env manual (tanpa dependency python-dotenv)
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

INFLUXDB_URL    = os.environ.get("INFLUXDB_URL", "")
INFLUXDB_TOKEN  = os.environ.get("INFLUXDB_TOKEN", "")
INFLUXDB_ORG    = os.environ.get("INFLUXDB_ORG", "")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET", "")

DUMMY_FILE = Path(__file__).parent / "dashboard" / "data_sensor_1_minggu_lineprotocol.txt"

def check_config():
    missing = [k for k, v in {
        "INFLUXDB_URL": INFLUXDB_URL,
        "INFLUXDB_TOKEN": INFLUXDB_TOKEN,
        "INFLUXDB_ORG": INFLUXDB_ORG,
        "INFLUXDB_BUCKET": INFLUXDB_BUCKET,
    }.items() if not v]
    if missing:
        print(f"❌ Variabel tidak ditemukan di .env: {missing}")
        sys.exit(1)
    if not DUMMY_FILE.exists():
        print(f"❌ File dummy tidak ditemukan: {DUMMY_FILE}")
        sys.exit(1)
    print("✅ Konfigurasi OK")
    print(f"   URL    : {INFLUXDB_URL}")
    print(f"   Org    : {INFLUXDB_ORG}")
    print(f"   Bucket : {INFLUXDB_BUCKET}")
    print(f"   File   : {DUMMY_FILE}")

def upload():
    try:
        from influxdb_client import InfluxDBClient
        from influxdb_client.client.write_api import SYNCHRONOUS
    except ImportError:
        print("❌ influxdb-client belum terinstall. Jalankan:")
        print("   pip install influxdb-client")
        sys.exit(1)

    print("\n📤 Membaca file dummy...")
    with open(DUMMY_FILE, "r") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]

    total = len(lines)
    print(f"   Total records: {total}")

    print("\n🔌 Menghubungkan ke InfluxDB Cloud...")
    client = InfluxDBClient(
        url=INFLUXDB_URL,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG,
        timeout=30_000
    )

    # Verify connection
    try:
        health = client.health()
        print(f"   Status: {health.status} — {health.message}")
    except Exception as e:
        print(f"❌ Gagal terhubung ke InfluxDB Cloud: {e}")
        client.close()
        sys.exit(1)

    write_api = client.write_api(write_options=SYNCHRONOUS)

    # Upload dalam batch 100 baris
    BATCH = 100
    uploaded = 0
    failed = 0

    print(f"\n🚀 Mulai upload {total} records (batch size: {BATCH})...")
    for i in range(0, total, BATCH):
        batch = lines[i : i + BATCH]
        batch_text = "\n".join(batch)
        try:
            write_api.write(
                bucket=INFLUXDB_BUCKET,
                org=INFLUXDB_ORG,
                record=batch_text,
                write_precision="s"
            )
            uploaded += len(batch)
            pct = (i + len(batch)) / total * 100
            print(f"   [{pct:5.1f}%] {uploaded}/{total} records uploaded...", end="\r")
        except Exception as e:
            failed += len(batch)
            print(f"\n⚠️  Batch {i//BATCH + 1} gagal: {e}")

    client.close()

    print(f"\n\n{'='*50}")
    print(f"✅ Upload selesai!")
    print(f"   Berhasil : {uploaded} records")
    if failed:
        print(f"   Gagal    : {failed} records")
    print(f"{'='*50}")
    print(f"\n💡 Cek data di InfluxDB Cloud:")
    print(f"   {INFLUXDB_URL}/orgs — pilih bucket '{INFLUXDB_BUCKET}'")

if __name__ == "__main__":
    print("=" * 50)
    print("  InfluxDB Cloud — Upload Data Dummy Sensor IoT")
    print("=" * 50)
    check_config()
    upload()
