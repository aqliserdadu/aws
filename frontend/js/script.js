let map, marker, config;

// Ambil konfigurasi
async function loadConfig() {
    const res = await fetch('/api/config');
    config = await res.json();

    // Tampilkan/hide card berdasarkan config.parameters
    const allCards = document.querySelectorAll('.card');
    allCards.forEach(card => {
        const id = card.id.replace('-card', '');
        card.style.display = config.parameters.includes(id) ? '' : 'none';
    });

    // Dropdown parameter
    const paramSelect = document.getElementById('param-select');
    paramSelect.innerHTML = '';
    config.parameters.forEach(param => {
        const opt = document.createElement('option');
        opt.value = param;
        opt.textContent = param.toUpperCase();
        paramSelect.appendChild(opt);
    });

    // Inisialisasi map
    const { latitude, longitude } = config.geo;
    map = L.map('map').setView([latitude, longitude], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    marker = L.marker([latitude, longitude]).addTo(map).bindPopup("Lokasi Sensor").openPopup();

    // Tampilkan device dan lokasi
    //document.getElementById("device-name").textContent = config.device;
    document.getElementById("map-location").textContent = config.location;

    // Fetch pertama kali
    fetchData();
    const param = paramSelect.value;
    const range = document.getElementById('time-range').value;
    //fetchHistory(param, range);
    renderHistoryChart(param, range);
    renderWindRose(range);

    // Tampilkan footer device dan software version
    if (config.device) {
        document.getElementById('footer-device').textContent = `${config.device}`;
    }
    if (config.software) {
        document.getElementById('footer-version').textContent = `V:${config.software}`;
    }
}

async function fetchData() {
    try {
        const res = await fetch('/api/latest');
        const data = await res.json();

        Object.keys(data).forEach(key => {
            const el = document.getElementById(`${key}-value`);
            if (el && typeof data[key] === 'number') {
                el.textContent = data[key].toFixed(2);
            }
        });

        if (data.timestamp) {
            const formatted = data.timestamp.replace(' ', ' |');
            const timestampEls = document.querySelectorAll('.timestamp');
            timestampEls.forEach(el => el.textContent = formatted);
        }

    } catch (e) {
        console.error("Gagal fetch data terbaru:", e);
    }
}



async function renderWindRose(range = "realtime") {
    try {
        const res = await fetch(`/api/windrose?range=${range}`);
        const data = await res.json();

        // Buat array dari arah dan kecepatan
        const rawData = [];
        for (let i = 0; i < data.wdir.length; i++) {
            const dir = data.wdir[i];
            const spd = data.wspeed[i];
            if (dir !== null && spd !== null) {
                rawData.push({
                    dir: degToCompass16(dir),
                    speed: spd
                });
            }
        }

        // Kelompokkan data berdasarkan arah
        const grouped = {};
        rawData.forEach(d => {
            if (!grouped[d.dir]) grouped[d.dir] = [];
            grouped[d.dir].push(d.speed);
        });

        const directions = [
            'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
            'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'
        ];

        const meanSpeeds = directions.map(dir => {
            const speeds = grouped[dir] || [];
            const mean = speeds.length ? speeds.reduce((a, b) => a + b, 0) / speeds.length : 0;
            return +mean.toFixed(2);
        });

        const trace = {
            type: 'barpolar',
            r: meanSpeeds,
            theta: directions,
            name: 'Wind Speed',
            marker: {
                color: meanSpeeds,
                colorscale: 'Bluered',
                colorbar: {
                    title: 'm/s',
                    thickness: 10
                }
            }
        };

        const layout = {
            title: 'Wind Rose (Average Speed)',
            polar: {
                angularaxis: {
                    direction: 'clockwise',
                    rotation: 90
                },
                radialaxis: {
                    ticksuffix: ' m/s',
                    angle: 45
                }
            },
            margin: { t: 50, b: 30, l: 30, r: 30 },
            showlegend: false
        };

        Plotly.newPlot("windRoseChart", [trace], layout);

    } catch (e) {
        console.error("❌ Gagal render wind rose:", e);
    }
}


function degToCompass16(deg) {
    const directions = [
        'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
        'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'
    ];
    const index = Math.round(deg / 22.5) % 16;
    return directions[index];
}


async function renderHistoryChart(param = "temp", range = "realtime") {
    try {
        console.log("🟢 renderHistoryChart() dipanggil:", param, range);
        const res = await fetch(`/api/history?param=${param}&range=${range}`);
        const data = await res.json();

        console.log("📈 Data timestamps:", data.timestamps);
        console.log("📉 Data values:", data.values);

        if (!data.timestamps.length) {
            console.warn("⚠️ Tidak ada data untuk range:", range);
            Plotly.react("dataChart", [], { title: "Tidak ada data" });
            return;
        }

        // ✅ Konversi timestamps ke milidetik
        const timestamps = data.timestamps.map(ts => new Date(ts).getTime());

        // ✅ Threshold gap 6 menit (ms)
        const GAP_THRESHOLD = 6 * 60 * 1000; // 6 menit dalam ms

        const filledTimestamps = [];
        const filledValues = [];

        filledTimestamps.push(data.timestamps[0]);
        filledValues.push(data.values[0]);

        for (let i = 1; i < timestamps.length; i++) {
            const prev = timestamps[i - 1];
            const curr = timestamps[i];

            // ⏳ Jika ada gap lebih dari 6 menit, masukkan null
            if (curr - prev > GAP_THRESHOLD) {
                console.log(`⛔ Gap terdeteksi antara ${new Date(prev).toISOString()} dan ${new Date(curr).toISOString()}`);
                filledTimestamps.push(new Date(prev + 1).toISOString()); // timestamp dummy
                filledValues.push(null); // ⬅️ Isi null biar garis putus
            }

            filledTimestamps.push(data.timestamps[i]);
            filledValues.push(data.values[i]);
        }

        // ✅ Buat trace Plotly dengan gap
        const trace = {
            x: filledTimestamps,
            y: filledValues,
            type: 'scatter',
            mode: 'lines+markers',
            name: param.toUpperCase(),
            line: {
                shape: 'spline',
                color: '#0074D9',
                width: 2
            },
            marker: {
                size: 4
            },
            connectgaps: false // ⬅️ Biarkan gap jadi putus-putus
        };

        const layout = {
            margin: { t: 30, b: 70, l: 50, r: 20 },
            title: `History of ${param.toUpperCase()}`,
            xaxis: {
                title: 'Waktu',
                tickangle: -45,
                tickformat: "%Y-%m-%d<br>%H:%M",
            },
            yaxis: {
                title: 'Nilai'
            },
            plot_bgcolor: '#fafafa',
            paper_bgcolor: '#fff',
            font: {
                size: 12
            }
        };

        Plotly.react("dataChart", [trace], layout, { responsive: true });
    } catch (err) {
        console.error("❌ Gagal render grafik:", err);
    }
}



document.getElementById('export-btn').addEventListener('click', async () => {
    const start = document.getElementById('start-datetime').value;
    const end = document.getElementById('end-datetime').value;
    const destination = document.getElementById('export-destination').value;
    const status = document.getElementById('export-status');
    
    status.style.display = 'block';

    if (!start || !end) {
        status.textContent = "❌ Start dan end date harus diisi.";
        return;
    }

    status.textContent = "⏳ Memproses export...";

    try {
        const res = await fetch('/api/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ start, end, destination })
        });

        if (destination === 'download') {
            if (!res.ok) {
                const result = await res.json();
                status.textContent = `❌ Gagal: ${result.error || 'Unknown error'}`;
                return;
            }
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `export_${start}_${end}.csv`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            status.textContent = "✅ Berhasil diunduh.";
        } else {
            const result = await res.json();
            if (res.ok) {
                status.textContent = `✅ Tersimpan di USB: ${result.path}`;
            } else {
                status.textContent = `❌ Gagal: ${result.error}`;
            }
        }
    } catch (err) {
        status.textContent = "❌ Terjadi error saat export.";
        console.error(err);
    }
});


// Event listener
document.getElementById('param-select').addEventListener('change', () => {
    const param = document.getElementById('param-select').value;
    const range = document.getElementById('time-range').value;
    renderHistoryChart(param, range);
});

document.getElementById('time-range').addEventListener('change', () => {
    const param = document.getElementById('param-select').value;
    const range = document.getElementById('time-range').value;
    renderHistoryChart(param, range);
    renderWindRose(range);
});

async function loadUsbOptions() {
    try {
        const res = await fetch('/api/usb-list');
        const devices = await res.json();
        const status = document.getElementById('export-status');
    
        status.style.display = 'none';

        const select = document.getElementById('export-destination');
        const currentOptions = Array.from(select.options).map(opt => opt.value);

        // Cek apakah array devices dan currentOptions sama persis
        const isSame = devices.length === currentOptions.length &&
            devices.every((d, i) => d === currentOptions[i]);

        if (!isSame) {
            // Kalau ada perbedaan, update <select>
            select.innerHTML = ''; // kosongkan dulu

            devices.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d;
                opt.textContent = d === 'download' ? 'Download' : `USB: ${d}`;
                select.appendChild(opt);
            });
        } else {
            console.log('USB list tidak berubah, tidak perlu update.');
        }
    } catch (e) {
        console.warn("Gagal memuat USB list:", e);
    }
}


loadUsbOptions(); // Panggil saat halaman dimuat


setInterval(() => {
   loadUsbOptions();
}, 10000);

// Auto refresh tiap 1 menit
setInterval(() => {
    fetchData();
    const param = document.getElementById('param-select').value;
    const range = document.getElementById('time-range').value;
    //fetchHistory(param, range);
    renderHistoryChart(param, range);
    renderWindRose(range);
}, 60000);

// Jalankan pertama kali
loadConfig();


//wifi deteksi

function updateWifiStatusUI() {
  fetch('/api/wifi-status')
    .then(res => res.json())
    .then(data => {
      const dot = document.getElementById("wifi-status-dot");
      const statusText = document.getElementById("wifi-current-status");

      if (data.connected) {
        dot.style.backgroundColor = "green";
        statusText.innerText = `Terhubung ke WiFi: ${data.ssid}`;
      } else {
        dot.style.backgroundColor = "red";
        statusText.innerText = `Tidak terhubung ke jaringan manapun.`;
      }
    })
    .catch(err => {
      document.getElementById("wifi-status-dot").style.backgroundColor = "red";
      document.getElementById("wifi-current-status").innerText = "Gagal mendapatkan status koneksi.";
    });
}

// Jalankan saat halaman dimuat dan setiap 30 detik
updateWifiStatusUI();
setInterval(updateWifiStatusUI, 30000);


// Fungsi untuk load SSID saat modal dibuka
const ssidSelect = document.getElementById("ssid");

document.getElementById("wifiModal").addEventListener("show.bs.modal", () => {
  ssidSelect.innerHTML = '<option value="">Memuat jaringan...</option>';

  fetch('/api/wifi-scan')
    .then(res => res.json())
    .then(data => {
      ssidSelect.innerHTML = ''; // Kosongkan isi
      if (data.ssids && data.ssids.length > 0) {
        data.ssids.forEach(ssid => {
          const opt = document.createElement("option");
          opt.value = ssid;
          opt.textContent = ssid;
          ssidSelect.appendChild(opt);
        });
      } else {
        ssidSelect.innerHTML = '<option value="">Tidak ada jaringan ditemukan</option>';
      }
    })
    .catch(err => {
      ssidSelect.innerHTML = '<option value="">Gagal memuat SSID</option>';
    });
});



document.getElementById("wifi-form").addEventListener("submit", function(e) {
  e.preventDefault();
  const ssid = document.getElementById("ssid").value;
  const password = document.getElementById("wifi-password").value;
  document.getElementById("wifi-status").innerText = `Menghubungkan ke ${ssid}...`;

  // Kirim ke server (ganti dengan AJAX fetch ke backend Python atau Flask)
  fetch('/api/connect-wifi', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ssid, password})
  }).then(res => res.json()).then(data => {
    document.getElementById("wifi-status").innerText = data.message || "Terhubung!";
  }).catch(err => {
    document.getElementById("wifi-status").innerText = "Gagal terhubung.";
  });
});

// Restart & Shutdown (pastikan backend endpoint tersedia)
document.getElementById("restart-btn").addEventListener("click", () => {
  if (confirm("Yakin ingin merestart Raspberry Pi?")) {
    fetch('/api/system/restart', { method: 'POST' });
  }
});
document.getElementById("shutdown-btn").addEventListener("click", () => {
  if (confirm("Yakin ingin mematikan Raspberry Pi?")) {
    fetch('/api/system/shutdown', { method: 'POST' });
  }
});
