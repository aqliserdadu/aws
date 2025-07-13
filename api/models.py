from sqlalchemy import Table, Column, Integer, Float, Text
from database import metadata

sensor_datas = Table(
    "sensor_datas",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("temp", Float),
    Column("hum", Float),
    Column("press", Float),
    Column("wspeed", Float),
    Column("wdir", Float),
    Column("rain", Float),
    Column("srad", Float),
    Column("device", Text),
    Column("timestamp", Integer),
    Column("created_at", Integer),
    Column("latitude", Float),
    Column("longitude", Float),
    Column("altitude", Float),
    Column("location", Text)
)
