import sqlite3
import random
from datetime import datetime, timedelta
import json

# Load konfigurasi device
with open("config.json") as f:
    config = json.load(f)

DB_FILE = "../database/aws_db.sqlite"

def create_table_if_not_exists(conn):
    """Buat tabel dan index jika belum ada"""
    cur = conn.cursor()
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
            created_at TEXT,
            latitude REAL,
            longitude REAL,
            altitude REAL,
            location TEXT
        );
    """)
    # Index timestamp agar query cepat
    cur.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_datas (timestamp);")
    conn.commit()

def insert_dummy_data(conn):
    """Generate data dummy 2 tahun ke belakang (5 menit interval) dengan missing timestamp 10-15%"""
    cur = conn.cursor()
    geo = config["geo"]
    device = config["device"]
    location = config["location"]

    # Mulai dari 2 tahun lalu
    start_time = datetime.now() - timedelta(days=2*365)
    total_intervals = 2 * 365 * 24 * (60 // 5)  # 2 tahun x 24 jam x (60 menit / 5 menit)

    skipped_timestamps = 0

    print(f"📦 Memasukkan data dummy (2 tahun, interval 5 menit)...")

    current_month = start_time.month
    # Persentase data hilang untuk bulan pertama
    missing_rate = random.uniform(0.10, 0.15)

    for i in range(total_intervals):
        dt = start_time + timedelta(minutes=i*5)
        timestamp = int(dt.timestamp())
        created_at = dt.isoformat()

        # Update persentase data hilang jika ganti bulan
        if dt.month != current_month:
            current_month = dt.month
            missing_rate = random.uniform(0.10, 0.15)
            print(f"📆 Bulan {current_month}: Kehilangan data {missing_rate*100:.1f}%")

        # Simulasikan alat mati sesuai persentase bulan ini
        if random.random() < missing_rate:
            skipped_timestamps += 1
            continue

        # Data sensor random normal
        temp = round(random.uniform(20.0, 35.0), 1)
        hum = round(random.uniform(40.0, 90.0), 1)
        press = round(random.uniform(1000.0, 1025.0), 2)
        wspeed = round(random.uniform(0.0, 10.0), 2)
        wdir = random.randint(0, 360)
        rain = round(random.uniform(0.0, 5.0), 2)
        srad = round(random.uniform(100.0, 1200.0), 1)

        cur.execute("""
            INSERT INTO sensor_datas (
                temp, hum, press, wspeed, wdir, rain, srad,
                device, timestamp, created_at,
                latitude, longitude, altitude, location
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            temp, hum, press, wspeed, wdir, rain, srad,
            device, timestamp, created_at,
            geo["latitude"], geo["longitude"], geo["altitude"],
            location
        ))

        # Commit setiap 10.000 data untuk efisiensi
        if (i + 1) % 10000 == 0:
            conn.commit()
            print(f"✅ {i + 1}/{total_intervals} data diproses")

    conn.commit()
    print(f"🎉 Selesai. Total data dimasukkan: {total_intervals - skipped_timestamps}")
    print(f"⚠️ Timestamp hilang (simulasi alat mati): {skipped_timestamps} interval.")

def main():
    conn = sqlite3.connect(DB_FILE)
    try:
        create_table_if_not_exists(conn)
        insert_dummy_data(conn)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
