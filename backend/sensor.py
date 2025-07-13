import serial
import time
import logging
import os
import sys
import json
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


def read_sensor():
    try:
        port = config.get("port", "/dev/ttyS0")
        logging.info(f"📡 Membuka port {port}...")

        ser = serial.Serial(
            port=port,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )

        if not ser.is_open:
            ser.open()
            logging.debug("✅ Port serial dibuka.")

        # Kirim request data ke sensor
        request = bytearray([0xFF, 0x03, 0x00, 0x09, 0x00, 0x07])
        request += bytearray([0xC1, 0xD4])  # CRC (disesuaikan sesuai sensor)

        ser.write(request)
        time.sleep(1)
        response = ser.read(256)
        ser.close()

        if not response or len(response) < 17:
            logging.warning(f"❌ Response kosong atau terlalu pendek: {response}")
            return None

        logging.info(f"✅ Raw response: {response.hex()}")

        try:
            temp = round(int.from_bytes(response[3:5], byteorder='big') / 100 - 40, 2)
            hum = round(int.from_bytes(response[5:7], byteorder='big') / 100, 2)
            press = round(int.from_bytes(response[7:9], byteorder='big') / 10, 2)
            wspeed = round(int.from_bytes(response[9:11], byteorder='big') / 100, 2)
            wdir = round(int.from_bytes(response[11:13], byteorder='big') / 10, 2)
            rain = round(int.from_bytes(response[13:15], byteorder='big') / 10, 2)
            srad = int.from_bytes(response[15:17], byteorder='big')

            logging.info(f"✅ Parsed: Temp={temp}, Hum={hum}, Press={press}, WSpeed={wspeed}, WDir={wdir}, Rain={rain}, Srad={srad}")
            return (temp, hum, press, wspeed, wdir, rain, srad)

        except Exception as parse_err:
            logging.error(f"❌ Gagal parsing data sensor: {parse_err}")
            traceback.print_exc()
            return None

    except Exception as e:
        logging.error(f"❌ Exception saat membaca sensor: {e}")
        traceback.print_exc()
        return None


# === Untuk pengujian langsung ===
if __name__ == "__main__":
    result = read_sensor()
    if result:
        print("✅ Sensor data:", result)
    else:
        print("❌ Gagal membaca data sensor.")
