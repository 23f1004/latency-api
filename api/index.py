import json
from pathlib import Path
from typing import List

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "*",
}


@app.middleware("http")
async def add_cors(request: Request, call_next):
    # Answer browser "preflight" checks immediately
    if request.method == "OPTIONS":
        return Response(status_code=204, headers=CORS_HEADERS)
    try:
        response = await call_next(request)
    except Exception as e:
        response = JSONResponse({"error": str(e)}, status_code=500)
    # Add the CORS headers to EVERY response, even errors
    for k, v in CORS_HEADERS.items():
        response.headers[k] = v
    return response


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
