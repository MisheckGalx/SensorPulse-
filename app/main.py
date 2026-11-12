import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from pydantic import BaseModel, Field

# Readings above this temperature are flagged as anomalies.
TEMP_THRESHOLD = float(os.getenv("TEMP_THRESHOLD", "28"))
# If TABLE_NAME is set we use DynamoDB, otherwise we keep data in memory.
TABLE_NAME = os.getenv("TABLE_NAME")

app = FastAPI(title="SensorPulse")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


class ReadingIn(BaseModel):
    """What a device sends us. Pydantic validates it automatically."""
    device_id: str = Field(min_length=1)
    temperature: float = Field(ge=-50, le=100)
    humidity: float = Field(ge=0, le=100)


class InMemoryStore:
    """Used for local development and tests."""

    def __init__(self):
        self.data: dict[str, list[dict]] = {}

    def add(self, reading: dict):
        self.data.setdefault(reading["device_id"], []).append(reading)

    def get(self, device_id: str) -> list[dict]:
        return self.data.get(device_id, [])

    def devices(self) -> list[str]:
        return sorted(self.data.keys())

    def clear(self):
        self.data.clear()


def make_store():
    if TABLE_NAME:
        from app.dynamo_store import DynamoStore
        return DynamoStore(TABLE_NAME)
    return InMemoryStore()


store = make_store()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/devices")
def list_devices():
    return store.devices()


@app.post("/readings", status_code=201)
def add_reading(r: ReadingIn):
    reading = r.model_dump()
    reading["timestamp"] = datetime.now(timezone.utc).isoformat()
    reading["anomaly"] = r.temperature > TEMP_THRESHOLD
    store.add(reading)
    return reading


@app.get("/devices/{device_id}/readings")
def list_readings(device_id: str, limit: int = 50):
    readings = store.get(device_id)
    if not readings:
        raise HTTPException(status_code=404, detail="Device not found")
    return readings[-limit:]


@app.get("/devices/{device_id}/summary")
def summary(device_id: str):
    readings = store.get(device_id)
    if not readings:
        raise HTTPException(status_code=404, detail="Device not found")
    n = len(readings)
    anomalies = sum(1 for r in readings if r["anomaly"])
    return {
        "device_id": device_id,
        "count": n,
        "avg_temperature": round(sum(r["temperature"] for r in readings) / n, 2),
        "avg_humidity": round(sum(r["humidity"] for r in readings) / n, 2),
        "max_temperature": max(r["temperature"] for r in readings),
        "anomaly_count": anomalies,
        "status": "ALERT" if anomalies else "OK",
    }


# AWS Lambda entry point: Mangum translates API Gateway events into
# requests that FastAPI understands.
handler = Mangum(app, lifespan="off")
