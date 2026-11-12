import boto3
import pytest
from moto import mock_aws

from app.dynamo_store import DynamoStore

REGION = "eu-west-1"


@pytest.fixture
def store():
    """moto fakes AWS in memory, so these tests never touch your real account."""
    with mock_aws():
        boto3.client("dynamodb", region_name=REGION).create_table(
            TableName="SensorReadings",
            AttributeDefinitions=[
                {"AttributeName": "device_id", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "device_id", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield DynamoStore("SensorReadings", region=REGION)


def reading(device="sensor-1", ts="2026-11-13T10:00:00+00:00", temp=22.5):
    return {"device_id": device, "timestamp": ts, "temperature": temp,
            "humidity": 50.0, "anomaly": temp > 28}


def test_round_trip_returns_floats(store):
    store.add(reading(temp=22.5))
    got = store.get("sensor-1")
    assert len(got) == 1
    assert got[0]["temperature"] == 22.5
    assert isinstance(got[0]["temperature"], float)


def test_readings_come_back_in_time_order(store):
    store.add(reading(ts="2026-11-13T10:00:02+00:00", temp=3))
    store.add(reading(ts="2026-11-13T10:00:01+00:00", temp=1))
    store.add(reading(ts="2026-11-13T10:00:03+00:00", temp=2))
    assert [r["temperature"] for r in store.get("sensor-1")] == [1, 3, 2]


def test_unknown_device_returns_empty_list(store):
    assert store.get("nope") == []


def test_devices_are_unique_and_sorted(store):
    store.add(reading(device="b", ts="t1"))
    store.add(reading(device="a", ts="t2"))
    store.add(reading(device="a", ts="t3"))
    assert store.devices() == ["a", "b"]
