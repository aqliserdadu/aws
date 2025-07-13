import time
from datetime import datetime
from sensor import read_sensor
from database import insert_data
import logging
import os
import traceback

# === Konfigurasi Log ===
log_path = "/opt/aws/logs/sensor.log"
os.makedirs(os.path.dirname(log_path), exist_ok=True)

logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# === Fungsi untuk menentukan apakah saat ini waktu eksekusi ===
def should_run():
    now = datetime.now()
    return now.minute % 5 == 0 and now.second == 0

# === Fungsi utama ===
def main():
    print("⏱️ Menunggu waktu yang tepat (tiap 5 menit di detik ke-0)...")
    logging.info("⏱️ Service dimulai. Menunggu waktu eksekusi sensor setiap 5 menit.")

    last_run = None

    try:
        while True:
            now = datetime.now()

            if should_run():
                # Hindari pengulangan dalam detik yang sama
                if last_run != now.replace(second=0, microsecond=0):
                    log_time = now.strftime('%Y-%m-%d %H:%M:%S')
                    print(f"\n📡 [{log_time}] Membaca sensor...")
                    logging.info("📡 Membaca sensor...")

                    try:
                        sensor_data = read_sensor()

                        if sensor_data:
                            logging.info(f"✅ Data sensor terbaca: {sensor_data}")
                            print("✅ Data sensor terbaca:", sensor_data)
                            temp, hum, press, wspeed, wdir, rain, srad = sensor_data

                            insert_data(
                                temp=temp,
                                hum=hum,
                                press=press,
                                wspeed=wspeed,
                                wdir=wdir,
                                rain=rain,
                                srad=srad
                            )
                            logging.info("💾 Data berhasil disimpan ke database.")
                        else:
                            logging.warning("⚠️ Pembacaan sensor gagal. Tidak menyimpan.")
                            print("⚠️ Pembacaan sensor gagal. Tidak menyimpan.")

                    except Exception as e:
                        logging.error(f"❌ Terjadi error saat membaca atau menyimpan data: {e}")
                        logging.error(traceback.format_exc())
                        print(f"❌ Error: {e}")

                    last_run = now.replace(second=0, microsecond=0)

            time.sleep(0.5)

    except KeyboardInterrupt:
        logging.info("🛑 Service dihentikan secara manual.")
        print("\n🛑 Dihentikan oleh pengguna.")

# === Eksekusi ===
if __name__ == "__main__":
    main()
