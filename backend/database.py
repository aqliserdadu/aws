import sqlite3
from datetime import datetime
import json
import logging
import os
import sys
import traceback

# === Konfigurasi Log ===
log_path = "/opt/aws/logs/sensor.log"
os.makedirs(os.path.dirname(log_path), exist_ok=True)

logging.basicConfig(
    filename=log_path,
    level=logging.INFO,  # Gunakan DEBUG untuk log detail
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# === Load konfigurasi dari file ===
config_path = "config.json"
if not os.path.exists(config_path):
    logging.error(f"❌ File konfigurasi tidak ditemukan: {config_path}")
    sys.exit(f"❌ File konfigurasi tidak ditemukan: {config_path}")

try:
    with open(config_path) as f:
        config = json.load(f)
    logging.info("✅ Konfigurasi berhasil dimuat.")
except Exception as e:
    logging.error(f"❌ Gagal membaca config.json: {e}")
    traceback.print_exc()
    sys.exit(1)

# === Path ke file database SQLite ===
DB_FILE = "/opt/aws/database/aws_db.sqlite"

def insert_data(temp, hum, press, wspeed, wdir, rain, srad):
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()

        # Buat tabel jika belum ada
        cur.execute("""
        CREATE TABLE IF NOT EXISTS sensor_datas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            temp REAL,
            hum REAL,
            press REAL,
            wspeed REAL,
            wdir REAL,
            rain REAL,
            srad REAL,
            device TEXT,
            timestamp INTEGER,
            created_at INTEGER,
            latitude REAL,
            longitude REAL,
            altitude REAL,
            location TEXT
        )
        """)
        logging.debug("✅ Tabel sensor_datas diperiksa/dibuat.")

        # Buat index jika belum ada
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_sensor_timestamp
        ON sensor_datas (timestamp);
        """)
        logging.debug("✅ Index timestamp diperiksa/dibuat.")

        # Persiapan data
        now = int(datetime.now().timestamp())
        geo = config.get("geo", {})
        values = (
            temp, hum, press, wspeed, wdir, rain, srad,
            config.get("device", "unknown"), now, now,
            geo.get("latitude", 0.0),
            geo.get("longitude", 0.0),
            geo.get("altitude", 0.0),
            config.get("location", "unknown")
        )

        # Eksekusi insert
        cur.execute("""
        INSERT INTO sensor_datas (
            temp, hum, press, wspeed, wdir, rain, srad,
            device, timestamp, created_at,
            latitude, longitude, altitude, location
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, values)

        conn.commit()
        logging.info(f"✅ Data berhasil disimpan. Timestamp: {now}, Device: {config.get('device')}")
        print("✅ Data inserted successfully:", now)

    except Exception as e:
        logging.error(f"❌ Database insert error: {e}")
        traceback.print_exc()
        print("❌ Database insert error:", e)

    finally:
        if conn:
            conn.close()
            logging.debug("🔒 Koneksi database ditutup.")

