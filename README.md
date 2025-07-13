# 🌤 Automatic Weather Station (AWS)

Automatic Weather Station (AWS) adalah Sistem pemantauan cuaca otomatis yang terdiri dari backend (pengumpulan data sensor), API (penyediaan data secara fleksibel), serta antarmuka web pengguna. Merekam data lingkungan seperti suhu, kelembaban, tekanan, curah hujan, radiasi surya, dll. Disimpan lokal menggunakan SQLite dan disediakan melalui REST API

---

## ⚙️ Fitur Utama

### ✅ 1. Backend Sensor (`aws-sensor.service`)
Mengambil data dari sensor cuaca dan menyimpannya ke dalam database SQLite.

### ✅ 2. API Service (`aws-api.service`)
Menyediakan REST API untuk:
- Mengambil data terakhir
- Query data berdasarkan waktu, lokasi, dan parameter

### ✅ 3. Web Dashboard (`aws-web.service`)
Antarmuka pengguna berbasis web untuk menampilkan data dan visualisasi cuaca.

### ✅ 4. Backup Otomatis (`aws-backup.service`)
Backup database dilakukan secara otomatis seminggu sekali pada malam hari, dan memastikan service backend dimatikan sementara selama backup berlangsung.

---



### 📁 Struktur Proyek
```bash
aws/
├── api/            # REST API untuk penyediaan data
├── backup/         # Script untuk backup data mingguan
├── backend/        # Backend sensor cuaca
├── database/       # Database SQLite
├── logs/           # File log untuk masing-masing service
├── install.sh      # Script instalasi otomatis
├── uninstall.sh    # Script uninstall
└── README.md       # Dokumentasi ini
```

### 🛠️ Instalasi Otomatis

Jalankan script berikut:
```bash
chmod +x install.sh
./install.sh
```


### 🖥️ Manajemen Service
Script aws digunakan untuk mengelola semua service dengan mudah:

### ▶️ Menyalakan service
```bash
aws start all         # Menyalakan semua service
aws start sensor      # Menyalakan hanya sensor
aws start api         # Menyalakan hanya API
aws start web         # Menyalakan hanya Web
aws start backup      # Menyalakan hanya Backup
```
### ⏹️ Menghentikan service
```bash
aws stop all
aws stop sensor
aws stop api
aws stop web
aws stop backup
```

### 🛠️ Uninstall Otomatis

Jalankan script berikut:
```bash
chmod +x uninstall.sh
./uninstall.sh
```

