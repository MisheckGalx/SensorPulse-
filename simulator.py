"""Pretends to be IoT devices sending readings to the API.
Usage: python simulator.py [api_url] [rounds]
"""
import random
import sys
import time

import httpx

API = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 20
DEVICES = ["sensor-1", "sensor-2", "sensor-3"]

for i in range(ROUNDS):
    for d in DEVICES:
        temp = random.gauss(24, 3)
        if random.random() < 0.1:          # 10% chance of a heat spike
            temp += 8
        payload = {"device_id": d,
                   "temperature": round(temp, 1),
                   "humidity": round(random.uniform(35, 70), 1)}
        r = httpx.post(f"{API}/readings", json=payload)
        print(d, payload["temperature"], "->", r.status_code)
    time.sleep(0.5)
