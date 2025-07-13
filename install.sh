#!/bin/bash

# ============================================
#  Automatic Weather Station (AWS) - Installer
# ============================================
# Nama Aplikasi : Automatic Weather Station (AWS)
# Deskripsi     : Sistem pemantauan cuaca otomatis yang terdiri dari backend (pengumpulan data sensor),
#                 API (penyediaan data secara fleksibel), serta antarmuka web pengguna.
# Fungsi        : Merekam data lingkungan seperti suhu, kelembaban, tekanan, curah hujan, radiasi surya, dll.
# Lokasi Data   : Disimpan lokal menggunakan SQLite dan disediakan melalui REST API.
#
# Dibuat oleh   : Abu Bakar <abubakar.it.dev@gmail.com>
# Versi         : 1.0
# Lisensi       : Private/Internal Project
# ============================================

echo "============================================"
echo " Automatic Weather Station (AWS) - Installer"
echo "============================================"
echo "📌 Dibuat oleh        : Abu Bakar <abubakar.it.dev@gmail.com>"
echo "📌 Deskripsi          : Sistem pemantauan cuaca otomatis berbasis Python & API"
echo "📌 Lokasi Instalasi   : /opt/aws"
echo "📌 Service            : aws-sensor, aws-api, aws-web, aws-backup"
echo "📌 Web Port           : 0.0.0.0:5010"
echo "📌 API Port           : 0.0.0.0:5011"
echo "📌 Dokumentasi API    : http://0.0.0.0:5011/docs"
echo "============================================"
echo ""

set -e  # Stop jika terjadi error

# === Pemeriksaan awal: hentikan jika service sudah terpasang ===
CHECK_SERVICES=("aws-sensor.service" "aws-web.service" "aws-api.service")
echo "🔍 Pemeriksaan keberadaan systemd service..."
found_existing=false

for service in "${CHECK_SERVICES[@]}"; do
    if [[ -f "/etc/systemd/system/$service" ]]; then
        echo "⚠️  Ditemukan service yang sudah ada: $service"
        found_existing=true
    fi
done

if [ "$found_existing" = true ]; then
    echo ""
    echo "🚫 Instalasi dibatalkan. Beberapa service AWS sudah terpasang."
    echo "🔁 Hapus service lama terlebih dahulu jika ingin instal ulang:"
    echo "    sudo systemctl stop <service>"
    echo "    sudo rm /etc/systemd/system/<service>"
    echo "    sudo systemctl daemon-reload"
    echo ""
    exit 1
else
    echo "✅ Tidak ada service yang bentrok. Melanjutkan instalasi..."
fi

# === Konfigurasi Default ===
LOG_DIR="/opt/aws/logs"
APP_BASE="/opt/aws"
SERVICES=("aws-sensor.service" "aws-web.service" "aws-api.service" "aws-backup.service")

echo ""
echo "🚀 Mulai proses instalasi AWS Project..."

# === Buat direktori instalasi ===
echo "📁 Membuat direktori instalasi di $APP_BASE..."
mkdir -p "$APP_BASE"
cp -r . "$APP_BASE"

# === Virtual Environment ===
echo "🧪 Membuat virtual environment..."
python3 -m venv "$APP_BASE/venv"
source "$APP_BASE/venv/bin/activate"

# === Install dependencies jika ada ===
REQ_FILE="$APP_BASE/requirements.txt"
if [[ -f "$REQ_FILE" ]]; then
    echo "📦 Menginstall dependencies dari $REQ_FILE..."
    pip install -r "$REQ_FILE"
else
    echo "⚠️  File requirements.txt tidak ditemukan, melewati install dependencies"
fi

# === Install CLI command ===
echo "🔗 Menautkan perintah aws ke /usr/bin/aws..."
if [[ -f "$APP_BASE/aws" ]]; then
    install -m 755 "$APP_BASE/aws" /usr/bin/aws
else
    echo "❌ File CLI 'aws' tidak ditemukan di $APP_BASE/aws"
fi

# === Buat direktori log ===
echo "📁 Membuat direktori log di $LOG_DIR..."
mkdir -p "$LOG_DIR"
chown root:root "$LOG_DIR"

# === Membuat systemd services ===
echo "🔧 Membuat systemd service..."

# 1. aws-sensor.service
echo "  • aws-sensor.service"
cat <<EOF | tee /etc/systemd/system/aws-sensor.service > /dev/null
[Unit]
Description=Sensor Reader Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_BASE/backend
ExecStart=$APP_BASE/venv/bin/python -u main.py
StandardOutput=append:$LOG_DIR/sensor.log
StandardError=append:$LOG_DIR/sensor.log
Restart=always
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOF

# 2. aws-web.service
echo "  • aws-web.service"
cat <<EOF | tee /etc/systemd/system/aws-web.service > /dev/null
[Unit]
Description=Web App Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_BASE/backend
ExecStart=$APP_BASE/venv/bin/python -u app.py
StandardOutput=append:$LOG_DIR/web.log
StandardError=append:$LOG_DIR/web.log
Restart=always
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOF

# 3. aws-api.service
echo "  • aws-api.service"
cat <<EOF | tee /etc/systemd/system/aws-api.service > /dev/null
[Unit]
Description=FastAPI Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_BASE/api
ExecStart=$APP_BASE/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 5011
StandardOutput=append:$LOG_DIR/api.log
StandardError=append:$LOG_DIR/api.log
Restart=always
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOF

# 4. aws-backup.service
echo "  • aws-backup.service"
cat <<EOF | tee /etc/systemd/system/aws-backup.service > /dev/null
[Unit]
Description=AWS Backup Mingguan (dijalankan malam hari)
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_BASE/backend
ExecStart=$APP_BASE/venv/bin/python -u backup.py
StandardOutput=append:$LOG_DIR/backup.log
StandardError=append:$LOG_DIR/backup.log
Restart=always
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOF

# === Reload systemd & aktifkan semua service ===
echo ""
echo "🔄 Reload systemd dan aktifkan semua service..."
systemctl daemon-reexec
systemctl daemon-reload

for service in "${SERVICES[@]}"; do
    systemctl enable "$service"
    systemctl restart "$service"
    echo "✅ $service diaktifkan & dijalankan."
done

echo ""
echo "🎉 Instalasi selesai!"
echo "Gunakan perintah 'aws' untuk menjalankan CLI."
