import json
from pathlib import Path
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# CORS: allow any website to call this endpoint
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the telemetry data once
with open(Path(__file__).parent / "q-vercel-latency.json") as f:
    DATA = json.load(f)


class Query(BaseModel):
    regions: List[str]
    threshold_ms: float


def percentile(values, p):
    v = sorted(values)
    k = (len(v) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


@app.get("/")
def home():
    return {"status": "ok", "usage": "POST {regions: [...], threshold_ms: 180}"}


@app.post("/")
@app.post("/{path:path}")
def analyze(q: Query, path: str = ""):
    result = {}
    for region in q.regions:
        rows = [r for r in DATA if r["region"] == region]
        if not rows:
            continue
        lat = [r["latency_ms"] for r in rows]
        up = [r["uptime_pct"] for r in rows]
        result[region] = {
            "avg_latency": sum(lat) / len(lat),
            "p95_latency": percentile(lat, 95),
            "avg_uptime": sum(up) / len(up),
            "breaches": sum(1 for x in lat if x > q.threshold_ms),
        }
    return result
