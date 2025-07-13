from fastapi import FastAPI, Query, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta

import crud, schemas
from database import metadata, engine
from auth import verify_token

# 🔧 Inisialisasi FastAPI App
app = FastAPI(
    title="Sensor API",
    description="API untuk mengakses dan mengelola data sensor cuaca secara fleksibel",
    version="1.0.0",
    docs_url=None  # Nonaktifkan Swagger bawaan
)

# 🔧 Jalankan otomatis pembuatan tabel (jika belum ada)
metadata.create_all(bind=engine)

# 🔧 Path direktori template & icon
BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "template"
ICON_DIR = TEMPLATE_DIR / "icon"

# 🔧 Mount folder static & templates
app.mount("/static", StaticFiles(directory=ICON_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# ✅ Custom Swagger UI
@app.get("/docs", include_in_schema=False)
async def custom_docs(request: Request):
    return templates.TemplateResponse("docs.html", {
        "request": request,
        "swagger_js_url": "https://cdn.jsdelivr.net/npm/swagger-ui-dist/swagger-ui-bundle.js",
        "swagger_css_url": "https://cdn.jsdelivr.net/npm/swagger-ui-dist/swagger-ui.css",
        "openapi_url": app.openapi_url
    })

# ✅ Endpoint untuk pengecekan server (opsional)
@app.get("/health", tags=["utility"])
def health():
    return {
        "status": "ok",
        "server_time": datetime.now().isoformat()
    }

# ================================================================
# ==========        SENSOR DATA ENDPOINTS (UTAMA)        =========
# ================================================================

@app.get("/api/sensors/latest")
def latest(device: Optional[str] = None):
    row = crud.get_latest(device)
    return dict(row._mapping) if row else {}

@app.get("/api/sensors/query", response_model=List[schemas.SensorQueryResponse])
def query_params(
    params: List[str] = Query(...),
    from_: datetime = Query(..., alias="from"),
    to: datetime = Query(..., alias="to"),
    device: Optional[str] = None,
    limit: Optional[int] = None
):
    from_ts = int(from_.timestamp())
    to_ts = int((to + timedelta(days=1)).timestamp()) - 1
    rows = crud.query_by_params(params, from_ts, to_ts, device, limit)
    return [{"timestamp": r[0], "data": dict(zip(params, r[1:]))} for r in rows]

@app.get("/api/sensors/all")
def get_all_data(
    device: Optional[str] = None,
    from_: Optional[datetime] = Query(None, alias="from"),
    to: Optional[datetime] = Query(None, alias="to"),
    limit: Optional[int] = None
):
    filters = {
        "device": device,
        "from_ts": int(from_.timestamp()) if from_ else None,
        "to_ts": int((to + timedelta(days=1)).timestamp()) - 1 if to else None,
        "limit": limit
    }
    rows = crud.get_all(filters)
    return [dict(r._mapping) for r in rows]

@app.post("/api/sensors/", dependencies=[Depends(verify_token)])
def post_sensor(data: schemas.SensorCreate):
    crud.insert_data(data.dict())
    return {"status": "success"}

@app.get("/api/sensors/devices")
def list_devices():
    return crud.list_devices()

@app.get("/api/sensors/stats", response_model=List[schemas.SensorStatResponse], dependencies=[Depends(verify_token)])
def sensor_stats(
    params: List[str] = Query(...),
    from_: datetime = Query(..., alias="from"),
    to: datetime = Query(..., alias="to")
):
    from_ts = int(from_.timestamp())
    to_ts = int((to + timedelta(days=1)).timestamp()) - 1
    return [crud.stats_for_param(p, from_ts, to_ts) for p in params]

@app.get("/api/sensors/geo")
def geo_query(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float
):
    rows = crud.query_geo(min_lat, max_lat, min_lon, max_lon)
    return [dict(r._mapping) for r in rows]
