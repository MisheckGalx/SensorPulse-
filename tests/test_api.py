import pytest
from fastapi.testclient import TestClient

from app.main import app, store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_store():
    store.clear()


def post(device="sensor-1", temp=22.0, hum=50.0):
    return client.post("/readings", json={
        "device_id": device, "temperature": temp, "humidity": hum})


def test_add_reading_returns_201():
    r = post()
    assert r.status_code == 201
    assert r.json()["anomaly"] is False


def test_high_temperature_is_flagged():
    assert post(temp=35.0).json()["anomaly"] is True


def test_invalid_humidity_rejected():
    assert post(hum=150).status_code == 422


def test_summary_calculates_averages():
    post(temp=20.0)
    post(temp=30.0)
    s = client.get("/devices/sensor-1/summary").json()
    assert s["count"] == 2
    assert s["avg_temperature"] == 25.0
    assert s["anomaly_count"] == 1
    assert s["status"] == "ALERT"


def test_unknown_device_404():
    assert client.get("/devices/nope/summary").status_code == 404
