from pydantic import BaseModel
from typing import Optional, Dict

class SensorBase(BaseModel):
    timestamp: int
    device: Optional[str]
    temp: Optional[float]
    hum: Optional[float]
    press: Optional[float]
    wspeed: Optional[float]
    wdir: Optional[float]
    rain: Optional[float]
    srad: Optional[float]
    latitude: Optional[float]
    longitude: Optional[float]
    altitude: Optional[float]
    location: Optional[str]

class SensorCreate(SensorBase):
    pass

class SensorQueryResponse(BaseModel):
    timestamp: int
    data: Dict[str, Optional[float]]

class SensorStatResponse(BaseModel):
    parameter: str
    avg: Optional[float]
    min: Optional[float]
    max: Optional[float]
