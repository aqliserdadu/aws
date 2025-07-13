from sqlalchemy import select, desc, func, and_
from models import sensor_datas
from database import SessionLocal

def get_latest(device=None):
    with SessionLocal() as db:
        query = select(sensor_datas).order_by(desc(sensor_datas.c.timestamp))
        if device:
            query = query.where(sensor_datas.c.device == device)
        return db.execute(query).fetchone()

def insert_data(data: dict):
    with SessionLocal() as db:
        db.execute(sensor_datas.insert().values(**data))
        db.commit()

def query_by_params(params, from_ts, to_ts, device=None, limit=None):
    with SessionLocal() as db:
        cols = [sensor_datas.c.timestamp] + [sensor_datas.c.get(p) for p in params]
        query = select(*cols).where(sensor_datas.c.timestamp.between(from_ts, to_ts))
        if device:
            query = query.where(sensor_datas.c.device == device)
        if limit:
            query = query.limit(limit)
        return db.execute(query).fetchall()

def get_all(filters):
    with SessionLocal() as db:
        query = select(sensor_datas)
        if filters.get("device"):
            query = query.where(sensor_datas.c.device == filters["device"])
        if filters.get("from_ts") and filters.get("to_ts"):
            query = query.where(sensor_datas.c.timestamp.between(filters["from_ts"], filters["to_ts"]))
        if filters.get("limit"):
            query = query.limit(filters["limit"])
        return db.execute(query).fetchall()

def list_devices():
    with SessionLocal() as db:
        result = db.execute(select(sensor_datas.c.device).distinct()).fetchall()
        return [r[0] for r in result]

def stats_for_param(param, from_ts, to_ts):
    with SessionLocal() as db:
        col = sensor_datas.c.get(param)
        query = select(func.avg(col), func.min(col), func.max(col)).where(sensor_datas.c.timestamp.between(from_ts, to_ts))
        result = db.execute(query).fetchone()
        return {"parameter": param, "avg": result[0], "min": result[1], "max": result[2]}

def query_geo(min_lat, max_lat, min_lon, max_lon):
    with SessionLocal() as db:
        query = select(sensor_datas).where(
            and_(
                sensor_datas.c.latitude >= min_lat,
                sensor_datas.c.latitude <= max_lat,
                sensor_datas.c.longitude >= min_lon,
                sensor_datas.c.longitude <= max_lon
            )
        )
        return db.execute(query).fetchall()
