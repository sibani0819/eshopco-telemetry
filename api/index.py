from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import pandas as pd
import numpy as np
import json

app = FastAPI()

# ✅ CORS middleware - placed at top
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # allow all origins
    allow_credentials=True,
    allow_methods=["*"],       # allow all HTTP methods
    allow_headers=["*"],       # allow all headers
    expose_headers=["*"],      # explicitly expose all headers
)

# Request model
class MetricsRequest(BaseModel):
    regions: List[str]
    threshold_ms: int

# Response models
class RegionMetrics(BaseModel):
    avg_latency: float
    p95_latency: float
    avg_uptime: float
    breaches: int

class MetricsResponse(BaseModel):
    regions: Dict[str, RegionMetrics]

def load_telemetry_data():
    """Load telemetry data from q-vercel-latency.json"""
    try:
        possible_paths = [
            'q-vercel-latency.json',
            'api/q-vercel-latency.json',
            './q-vercel-latency.json',
            './api/q-vercel-latency.json'
        ]
        data = None
        for path in possible_paths:
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    break
            except FileNotFoundError:
                continue
        if data is None:
            raise FileNotFoundError("Could not find q-vercel-latency.json")
        df_data = []
        for item in data:
            df_data.append({
                'region': item.get('region', ''),
                'latency_ms': item.get('latency_ms', 0),
                'uptime': item.get('uptime_pct', 0.0) / 100.0
            })
        return pd.DataFrame(df_data)
    except Exception as e:
        raise Exception(f"Error loading telemetry data: {e}")

# Load data at startup
try:
    df = load_telemetry_data()
    data_loaded = True
except Exception as e:
    print(f"❌ CRITICAL: Failed to load telemetry data: {e}")
    df = pd.DataFrame(columns=['region', 'latency_ms', 'uptime'])
    data_loaded = False

@app.post("/", response_model=MetricsResponse)
async def calculate_metrics(request: MetricsRequest):
    if not data_loaded:
        raise HTTPException(status_code=500, detail="Telemetry data not loaded")
    results = {}
    for region in request.regions:
        region_data = df[df['region'] == region]
        if len(region_data) == 0:
            results[region] = {
                "avg_latency": 0.0,
                "p95_latency": 0.0,
                "avg_uptime": 0.0,
                "breaches": 0
            }
            continue
        latencies = region_data['latency_ms'].values
        uptimes = region_data['uptime'].values
        avg_latency = float(np.mean(latencies))
        p95_latency = float(np.percentile(latencies, 95))
        avg_uptime = float(np.mean(uptimes))
        breaches = int(np.sum(latencies > request.threshold_ms))
        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 4),
            "breaches": breaches
        }
    return {"regions": results}

@app.get("/")
async def root():
    status = "active" if data_loaded else "data_loading_failed"
    return {
        "message": "eShopCo Telemetry API",
        "status": status,
        "data_loaded": data_loaded,
        "available_regions": df['region'].unique().tolist() if data_loaded else [],
        "usage": "POST / with {'regions': ['amer','emea'], 'threshold_ms': 180}"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy" if data_loaded else "degraded",
        "data_loaded": data_loaded,
        "total_records": len(df) if data_loaded else 0,
        "regions_available": df['region'].unique().tolist() if data_loaded else []
    }
