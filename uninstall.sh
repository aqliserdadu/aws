#!/bin/bash

echo "🚨 Memulai proses uninstall AWS (Automatic Weather Station)..."

# Konfigurasi path
INSTALL_DIR="/opt/aws"
LOG_DIR="$INSTALL_DIR/logs"
BIN_PATH="/usr/bin/aws"
DB_DIR="$INSTALL_DIR/database"
SERVICES=("aws-sensor.service" "aws-web.service" "aws-api.service")

# Tanya apakah ingin menghapus database
read -p "❓ Apakah Anda ingin menghapus database ? [y/N]: " DELETE_DB
DELETE_DB=${DELETE_DB,,}  # lowercase

# 1. Stop dan nonaktifkan service
echo "🛑 Menghentikan dan menonaktifkan service..."
for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$service"; then
        sudo systemctl stop "$service"
        echo "✅ $service dihentikan"
    fi
    if systemctl is-enabled --quiet "$service"; then
        sudo systemctl disable "$service"
        echo "✅ $service dinonaktifkan"
    fi
    sudo rm -f "/etc/systemd/system/$service"
    echo "🗑️ $service dihapus"
done

# 2. Reload systemd
echo "🔄 Reload systemd daemon..."
sudo systemctl daemon-reload
sudo systemctl reset-failed

# 3. Proses penghapusan folder
if [[ "$DELETE_DB" == "y" || "$DELETE_DB" == "yes" ]]; then
    echo "🗑️ Menghapus seluruh direktori $INSTALL_DIR termasuk database..."
    sudo rm -rf "$INSTALL_DIR"
else
    echo "⚠️ Menyisakan database. Menghapus semua kecuali folder $DB_DIR..."
    sudo find "$INSTALL_DIR" -mindepth 1 -not -path "$DB_DIR" -not -path "$DB_DIR/*" -exec rm -rf {} +
    echo "✅ Folder database tetap disimpan di $DB_DIR"
fi

# 4. Hapus file CLI jika ada
if [[ -f "$BIN_PATH" ]]; then
    echo "🗑️ Menghapus CLI aws dari $BIN_PATH..."
    sudo rm -f "$BIN_PATH"
else
    echo "⚠️ CLI aws tidak ditemukan di $BIN_PATH, dilewati."
fi

echo "✅ Uninstall selesai. Sistem telah dibersihkan."
