import sqlite3
import random
from datetime import datetime
import json
import time

# Load config
with open("config.json") as f:
    config = json.load(f)

DB_FILE = "../database/aws_db.sqlite"

def insert_realtime_data():
    """Insert 1 baris data realtime setiap 60 detik"""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    geo = config["geo"]
    device = config["device"]
    location = config["location"]

    try:
        while True:
            now = datetime.now()
            timestamp = int(now.timestamp())
            created_at = now.isoformat()

            # Random data
            temp = round(random.uniform(20.0, 35.0), 1)
            hum = round(random.uniform(40.0, 90.0), 1)
            press = round(random.uniform(1000.0, 1025.0), 2)
            wspeed = round(random.uniform(0.0, 10.0), 2)
            wdir = random.randint(0, 360)
            rain = round(random.uniform(0.0, 1.0), 2)
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
            conn.commit()
            print(f"📡 Inserted realtime data @ {now}")

            # Tunggu 60 detik
            time.sleep(60*5)

    except KeyboardInterrupt:
        print("\n🛑 Realtime data generator dihentikan oleh user.")
    finally:
        conn.close()

if __name__ == "__main__":
    insert_realtime_data()
