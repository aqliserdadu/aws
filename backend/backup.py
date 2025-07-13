import os
import shutil
import sqlite3
import subprocess
from datetime import datetime, timedelta
import logging
import time
import json

# === Path Konfigurasi ===
BASE_DB = "/opt/aws/database/aws_db.sqlite"
BACKUP_DIR = "/opt/aws/database/backup"
STATE_FILE = "/opt/aws/database/backup_state.json"
LOG_PATH = "/opt/aws/logs/backup.log"
SERVICES = ["aws-sensor.service", "aws-api.service"]  # 🆕

# === Setup Logging ===
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# === Load/Save State ===
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        logging.error(f"❌ Gagal menyimpan state: {e}")

# === Stop & Start Service ===
def control_services(action):
    for service in SERVICES:
        try:
            subprocess.run(["systemctl", action, service], check=True)
            logging.info(f"✅ Service '{service}' berhasil: {action}")
        except subprocess.CalledProcessError as e:
            logging.error(f"❌ Gagal {action} service {service}: {e}")

# === Backup Database ===
def backup_database():
    today_str = datetime.today().strftime('%Y-%m-%d')
    backup_name = f"aws_db_{today_str}.sqlite"
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    if os.path.exists(backup_path):
        logging.info("✅ Backup hari ini sudah ada.")
        return False

    try:
        shutil.copy2(BASE_DB, backup_path)
        logging.info(f"✅ Backup berhasil dibuat: {backup_path}")
        return True
    except Exception as e:
        logging.error(f"❌ Gagal backup database: {e}")
        return False

# === Hapus Backup Lama (> 30 hari) ===
def cleanup_old_backups():
    cutoff = datetime.today() - timedelta(days=30)
    for fname in os.listdir(BACKUP_DIR):
        if fname.startswith("aws_db_") and fname.endswith(".sqlite"):
            try:
                date_str = fname.replace("aws_db_", "").replace(".sqlite", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if file_date < cutoff:
                    os.remove(os.path.join(BACKUP_DIR, fname))
                    logging.info(f"🗑️ Backup lama dihapus: {fname}")
            except Exception as e:
                logging.warning(f"⚠️ Tidak bisa memproses backup: {fname} => {e}")

# === Optimasi Database (hapus >13 bulan) ===
def optimize_database():
    try:
        conn = sqlite3.connect(BASE_DB)
        cur = conn.cursor()

        cutoff = int((datetime.now() - timedelta(days=396)).timestamp())
        cur.execute("DELETE FROM sensor_datas WHERE created_at < ?", (cutoff,))
        deleted = cur.rowcount
        logging.info(f"🧹 Menghapus {deleted} baris data lebih dari 13 bulan.")

        cur.execute("VACUUM;")
        conn.commit()
        conn.close()
        logging.info("✅ Database dioptimasi.")
    except Exception as e:
        logging.error(f"❌ Gagal optimasi database: {e}")

# === Main Loop ===
def main_loop():
    logging.info("🚀 Memulai background backup mingguan (malam hari)...")
    state = load_state()

    while True:
        now = datetime.now()
        hour = now.hour
        today_str = now.strftime('%Y-%m-%d')

        # Cek apakah sudah seminggu sejak backup terakhir
        last_backup_str = state.get("last_backup", None)
        do_backup = False

        if last_backup_str:
            try:
                last_backup_date = datetime.strptime(last_backup_str, "%Y-%m-%d")
                if now - last_backup_date >= timedelta(days=7):
                    do_backup = True
            except Exception as e:
                logging.warning(f"⚠️ Format last_backup salah: {e}")
                do_backup = True
        else:
            do_backup = True

        # Jalankan hanya malam hari (00:00–01:00)
        if 0 <= hour < 1 and do_backup:
            logging.info("🌙 Malam hari & waktunya backup mingguan. Menjalankan proses...")
            try:
                control_services("stop")  # Stop semua service

                if backup_database():
                    state["last_backup"] = today_str
                    save_state(state)

                cleanup_old_backups()
                optimize_database()

            finally:
                control_services("start")  # Start kembali service

        else:
            if not do_backup:
                logging.info("📅 Belum waktunya backup mingguan.")
            elif not (0 <= hour < 1):
                logging.info("🕓 Bukan malam hari. Menunggu waktu 00:00–01:00.")

        time.sleep(3600)  # cek tiap 1 jam

# === Entry Point ===
if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        logging.info("🛑 Dihentikan oleh pengguna.")
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}")
