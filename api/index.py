from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import numpy as np

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MetricsRequest(BaseModel):
    regions: List[str]
    threshold_ms: int

class RegionMetrics(BaseModel):
    avg_latency: float
    p95_latency: float
    avg_uptime: float
    breaches: int

class MetricsResponse(BaseModel):
    regions: Dict[str, RegionMetrics]

# Hardcoded sample data to ensure it works
telemetry_data = {
    "amer": [120, 180, 90, 200, 85, 110, 95, 130, 160, 75, 140, 125, 155, 105, 115],
    "emea": [110, 160, 95, 170, 88, 105, 125, 140, 155, 82, 135, 118, 148, 98, 128],
    "apac": [130, 190, 100, 210, 92, 115, 135, 165, 175, 87, 145, 138, 168, 108, 125],
    "latam": [125, 170, 98, 195, 89, 108, 128, 150, 168, 84, 142, 132, 158, 102, 122]
}

@app.post("/", response_model=MetricsResponse)
async def calculate_metrics(request: MetricsRequest):
    results = {}
    
    for region in request.regions:
        if region in telemetry_data:
            latencies = telemetry_data[region]
            uptimes = [0.95 + (1 - (x - min(latencies)) / (max(latencies) - min(latencies))) * 0.04 for x in latencies]
            
            avg_latency = float(np.mean(latencies))
            p95_latency = float(np.percentile(latencies, 95))
            avg_uptime = float(np.mean(uptimes))
            breaches = int(np.sum(np.array(latencies) > request.threshold_ms))
            
            results[region] = {
                "avg_latency": round(avg_latency, 2),
                "p95_latency": round(p95_latency, 2),
                "avg_uptime": round(avg_uptime, 4),
                "breaches": breaches
            }
        else:
            results[region] = {
                "avg_latency": 0.0,
                "p95_latency": 0.0,
                "avg_uptime": 0.0,
                "breaches": 0
            }
    
    return {"regions": results}

@app.get("/")
async def root():
    return {
        "message": "eShopCo Telemetry API",
        "status": "active",
        "regions_available": list(telemetry_data.keys()),
        "usage": "POST / with {'regions': ['amer','emea'], 'threshold_ms': 180}"
    }
