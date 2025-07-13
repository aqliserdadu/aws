from flask import Flask, send_from_directory, jsonify, request, send_file
import sqlite3
import pandas as pd
from datetime import datetime
import json
import os
import io
import sys
import logging
import traceback
import re
import subprocess

# === Logging Setup ===
log_path = "/opt/aws/logs/web.log"
os.makedirs(os.path.dirname(log_path), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler(sys.stdout)
    ]
)

# === Path Setup ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
DB_FILE = os.path.join(BASE_DIR, "../database/aws_db.sqlite")

# === Load konfigurasi JSON ===
try:
    with open(CONFIG_PATH) as f:
        CONFIG = json.load(f)
except Exception as e:
    logging.error(f"❌ Gagal membaca file konfigurasi config.json: {e}")
    CONFIG = {}

# === Flask App ===
app = Flask(__name__, static_folder=None)

# === USB Mount Management ===
BASE_MOUNT_DIR = "/mnt"
MOUNTED_USB = []
    
# Path ke file SQLite
DB_FILE = os.path.join(BASE_DIR, "../database/aws_db.sqlite")


def get_usb_devices():
    """
    Deteksi USB flashdisk, mount jika perlu,
    dan kembalikan list dict: [{"label": "<vendor>", "mount": "<mount_point>"}]
    """
    devices = []
    try:
        result = subprocess.run(['lsblk', '-S', '-o', 'NAME,TRAN,VENDOR'], capture_output=True, text=True)
        lines = result.stdout.strip().splitlines()[1:]
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 3:
                name, tran, vendor = parts[:3]
                if tran.lower() == 'usb':
                    # Cek partisi
                    part_result = subprocess.run(
                        ['lsblk', '-nrpo', 'NAME,TYPE,MOUNTPOINT', f'/dev/{name}'],
                        capture_output=True, text=True
                    )
                    part_lines = part_result.stdout.strip().splitlines()
                    for part_line in part_lines:
                        part_info = part_line.strip().split()
                        if len(part_info) >= 3 and part_info[1] == "part":
                            part_name = part_info[0]
                            mount_point = part_info[2] if part_info[2] != "-" else None
                            # Mount jika belum termount
                            if not mount_point:
                                safe_vendor = vendor.replace(" ", "_")
                                mount_point = os.path.join(BASE_MOUNT_DIR, safe_vendor)
                                os.makedirs(mount_point, exist_ok=True)
                                try:
                                    subprocess.run(['mount', part_name, mount_point], check=True)
                                    logging.info(f"✅ Mounted {part_name} ke {mount_point}")
                                    MOUNTED_USB.append(mount_point)  # Track untuk cleanup nanti
                                except subprocess.CalledProcessError as e:
                                    logging.error(f"❌ Gagal mount {part_name}: {e}")
                                    continue
                            devices.append({
                                "label": vendor.strip(),
                                "mount": mount_point
                            })
        return devices
    except Exception as e:
        logging.error(f"❌ USB detection error: {e}")
        return []


def cleanup_usb_mounts():
    """
    Unmount semua USB yang dimount oleh aplikasi ini
    """
    global MOUNTED_USB
    for mount_point in MOUNTED_USB:
        try:
            subprocess.run(['umount', mount_point], check=True)
            logging.info(f"🛑 Unmounted {mount_point}")
        except subprocess.CalledProcessError as e:
            logging.error(f"⚠ Gagal unmount {mount_point}: {e}")
    MOUNTED_USB = []  # Clear list


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # supaya hasil bisa diakses dengan nama kolom
    return conn


def sanitize_filename(filename):
    """Hapus karakter ilegal untuk FAT32/NTFS"""
    filename = filename.replace(":", "-").replace("/", "-")
    filename = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", filename)
    return filename


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def serve_frontend_assets(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@app.route('/api/config')
def get_config():
    return jsonify(CONFIG)


@app.route('/api/latest')
def latest_data():
    try:
        logging.info("📥 MEMASUKI /api/latest")
        params = CONFIG.get("parameters", [])
        if not params:
            logging.warning("⚠️ Parameter kosong")
            return jsonify({"error": "No parameters defined in config"}), 400

        param_fields = ', '.join(params + ["timestamp"])
        logging.info("🔍 SQL kolom: %s", param_fields)

        query = f"""
        SELECT {param_fields}
        FROM sensor_datas
        ORDER BY timestamp DESC
        LIMIT 1;
        """
        conn = get_db_connection()
        df = pd.read_sql(query, conn)
        conn.close()

        if df.empty:
            logging.info("📭 Data kosong")
            return jsonify({param: None for param in params})
        else:
            row = df.iloc[0].to_dict()
            if 'timestamp' in row and row['timestamp']:
                ts = datetime.fromtimestamp(row['timestamp'])
                row['timestamp'] = ts.strftime("%Y-%m-%d %H:%M")
            logging.info("✅ Data ditemukan: %s", row)
            return jsonify(row)

    except Exception as e:
        logging.error("❌ Exception di /api/latest: %s", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/history')
def history_data():
    param = request.args.get('param', 'temp')
    range_time = request.args.get('range', 'realtime')
    now = int(datetime.now().timestamp())

    start_time = {
        "realtime": now - 15 * 60,
        "1h": now - 3600,
        "12h": now - 12 * 3600,
        "1d": now - 86400,
        "3d": now - 3 * 86400,
        "7d": now - 7 * 86400
    }.get(range_time, now - 15 * 60)

    try:
        query = f"""
        SELECT timestamp, {param}
        FROM sensor_datas
        WHERE timestamp >= ?
        ORDER BY timestamp ASC;
        """
        conn = get_db_connection()
        df = pd.read_sql(query, conn, params=(start_time,))
        conn.close()

        # Ganti NaN dengan None agar JSON valid
        df.fillna(value=pd.NA, inplace=True)
        df = df.astype(object).where(pd.notnull(df), None)

        if param not in df.columns:
            return jsonify({"timestamps": [], "values": []})

        return jsonify({
            "timestamps": [datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") for ts in df["timestamp"]],
            "values": df[param].tolist()
        })

    except Exception as e:
        logging.error("❌ /api/history error: %s", e)
        traceback.print_exc()
        return jsonify({"timestamps": [], "values": [], "error": str(e)}), 500


@app.route('/api/windrose')
def windrose_data():
    range_time = request.args.get('range', 'realtime')
    now = int(datetime.now().timestamp())

    start_time = {
        "realtime": now - 15 * 60,
        "1h": now - 3600,
        "12h": now - 12 * 3600,
        "1d": now - 86400,
        "3d": now - 3 * 86400,
        "7d": now - 7 * 86400
    }.get(range_time, now - 15 * 60)

    try:
        query = """
        SELECT timestamp, wspeed, wdir
        FROM sensor_datas
        WHERE timestamp >= ?
        ORDER BY timestamp ASC;
        """
        conn = get_db_connection()
        df = pd.read_sql(query, conn, params=(start_time,))
        conn.close()

        # Ganti NaN dengan None agar JSON valid
        df.fillna(value=pd.NA, inplace=True)
        df = df.astype(object).where(pd.notnull(df), None)

        if "wspeed" not in df.columns or "wdir" not in df.columns:
            return jsonify({"timestamps": [], "wspeed": [], "wdir": []})

        return jsonify({
            "timestamps": [datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") for ts in df["timestamp"]],
            "wspeed": df["wspeed"].tolist(),
            "wdir": df["wdir"].tolist()
        })

    except Exception as e:
        logging.error("❌ /api/windrose error: %s", e)
        traceback.print_exc()
        return jsonify({"timestamps": [], "wspeed": [], "wdir": [], "error": str(e)}), 500


@app.route('/api/usb-list', methods=['GET'])
def list_usb_devices():
    try:
        usb_devices = get_usb_devices()
        devices = ["download"] + [usb["label"] for usb in usb_devices]
        response = jsonify(devices)
        cleanup_usb_mounts()  # Unmount setelah selesai
        return response
    except Exception as e:
        logging.error(f"❌ USB list error: {e}")
        cleanup_usb_mounts()  # Tetap unmount jika error
        return jsonify(["download"]), 500


@app.route('/api/export', methods=['POST'])
def export_data():
    """
    Export data ke USB atau download
    """
    try:
        data = request.get_json()
        start = data.get("start")
        end = data.get("end")
        destination = data.get("destination", "download")

        if not start or not end:
            return jsonify({"error": "Parameter 'start' dan 'end' wajib diisi."}), 400

        logging.info(f"📦 Export request: {start} → {end} to {destination}")

        start_dt = int(datetime.fromisoformat(start).timestamp())
        end_dt = int(datetime.fromisoformat(end).timestamp())

        # Query data
        query = """
            SELECT *
            FROM sensor_datas
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC;
        """
        conn = get_db_connection()
        df = pd.read_sql(query, conn, params=(start_dt, end_dt))
        conn.close()

        if df.empty:
            return jsonify({"error": "Tidak ada data dalam rentang waktu tersebut."}), 400

        filename = f"export_{start}_{end}.csv"
        filename = sanitize_filename(filename)

        if destination == "download":
            # Export untuk di-download langsung
            csv_io = io.StringIO()
            df.to_csv(csv_io, index=False)
            mem = io.BytesIO()
            mem.write(csv_io.getvalue().encode('utf-8'))
            mem.seek(0)
            response = send_file(
                mem,
                download_name=filename,
                as_attachment=True,
                mimetype='text/csv'
            )
        else:
            # Export ke USB
            usb_devices = get_usb_devices()
            mount_point = next((usb["mount"] for usb in usb_devices if usb["label"] == destination), None)
            if not mount_point or not os.access(mount_point, os.W_OK):
                logging.error(f"❌ Tidak bisa tulis ke USB {destination}")
                return jsonify({"error": f"Folder USB '{destination}' tidak ditemukan atau tidak bisa ditulis."}), 500

            export_path = os.path.join(mount_point, filename)
            try:
                df.to_csv(export_path, index=False)
                logging.info(f"✅ Data berhasil diekspor ke: {export_path}")
                response = jsonify({"status": "success", "path": export_path})
            except Exception as e:
                logging.error(f"❌ Gagal menulis ke USB: {e}")
                response = jsonify({"error": f"Gagal menulis ke USB: {e}"}), 500

        return response
    except Exception as e:
        logging.error("❌ Export error: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        # Unmount semua USB setelah selesai
        cleanup_usb_mounts()


@app.route('/api/wifi-status', methods=['GET'])
def wifi_status():
    try:
        logging.info("Memeriksa status koneksi WiFi...")
        result = subprocess.run(['nmcli', '-t', '-f', 'active,ssid', 'dev', 'wifi'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        ssid_connected = next((line.split(":")[1] for line in lines if line.startswith("yes:")), None)

        ping_check = subprocess.run(['ping', '-c', '1', '8.8.8.8'], stdout=subprocess.DEVNULL)
        connected = ping_check.returncode == 0

        logging.info(f"Status koneksi: {'terhubung' if connected else 'tidak terhubung'}, SSID: {ssid_connected or '-'}")

        return jsonify({
            'connected': connected,
            'ssid': ssid_connected if ssid_connected else "-"
        })
    except Exception as e:
        logging.error(f"Kesalahan saat memeriksa status WiFi: {e}")
        return jsonify({'connected': False, 'ssid': '-'})


@app.route('/api/wifi-scan', methods=['GET'])
def wifi_scan():
    try:
        logging.info("Memindai jaringan WiFi...")
        result = subprocess.run(['nmcli', '-t', '-f', 'ssid', 'dev', 'wifi'], capture_output=True, text=True)
        raw_ssids = result.stdout.strip().split('\n')
        ssids = list({ssid for ssid in raw_ssids if ssid.strip()})
        logging.info(f"Ditemukan {len(ssids)} SSID: {ssids}")
        return jsonify({'ssids': ssids})
    except Exception as e:
        logging.error(f"Kesalahan saat memindai WiFi: {e}")
        return jsonify({'ssids': []})


@app.route('/api/connect-wifi', methods=['POST'])
def connect_wifi():
    try:
        data = request.json
        ssid = data.get('ssid')
        password = data.get('password')

        logging.info(f"Mencoba menghubungkan ke SSID: {ssid} (simulasi)")

        # Simulasi - ganti dengan perintah yang sebenarnya jika ingin menghubungkan
        # subprocess.run(['nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password])

        return jsonify({'message': f'Terhubung ke {ssid} (simulasi).'})
    except Exception as e:
        logging.error(f"Kesalahan saat menghubungkan ke WiFi: {e}")
        return jsonify({'message': 'Gagal menghubungkan ke WiFi.'}), 500


@app.route('/api/system/restart', methods=['POST'])
def restart():
    logging.warning("Perintah restart sistem dikirim!")
    os.system('sudo reboot')
    return '', 204


@app.route('/api/system/shutdown', methods=['POST'])
def shutdown():
    logging.warning("Perintah shutdown sistem dikirim!")
    os.system('sudo shutdown now')
    return '', 204


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5010
    app.run(host="0.0.0.0", port=port)
