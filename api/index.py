from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import numpy as np

app = FastAPI()

# CORS configuration - PROPERLY ENABLED
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

# YOUR ACTUAL DATA EMBEDDED STATICALLY
telemetry_data = [
    {"region": "apac", "latency_ms": 132.85, "uptime": 0.98216},
    {"region": "apac", "latency_ms": 158.65, "uptime": 0.98449},
    {"region": "apac", "latency_ms": 210.02, "uptime": 0.97439},
    {"region": "apac", "latency_ms": 175.03, "uptime": 0.9888},
    {"region": "apac", "latency_ms": 156.38, "uptime": 0.97809},
    {"region": "apac", "latency_ms": 169.18, "uptime": 0.98332},
    {"region": "apac", "latency_ms": 167.93, "uptime": 0.98236},
    {"region": "apac", "latency_ms": 113.83, "uptime": 0.98592},
    {"region": "apac", "latency_ms": 177.43, "uptime": 0.99437},
    {"region": "apac", "latency_ms": 203.85, "uptime": 0.99137},
    {"region": "apac", "latency_ms": 219.17, "uptime": 0.98774},
    {"region": "apac", "latency_ms": 184.01, "uptime": 0.99043},
    {"region": "emea", "latency_ms": 215.32, "uptime": 0.97201},
    {"region": "emea", "latency_ms": 165.35, "uptime": 0.98221},
    {"region": "emea", "latency_ms": 113.86, "uptime": 0.98619},
    {"region": "emea", "latency_ms": 152.11, "uptime": 0.98282},
    {"region": "emea", "latency_ms": 189.73, "uptime": 0.9713},
    {"region": "emea", "latency_ms": 122.49, "uptime": 0.97366},
    {"region": "emea", "latency_ms": 180.42, "uptime": 0.97796},
    {"region": "emea", "latency_ms": 149.34, "uptime": 0.98406},
    {"region": "emea", "latency_ms": 190.12, "uptime": 0.98774},
    {"region": "emea", "latency_ms": 209.3, "uptime": 0.98798},
    {"region": "emea", "latency_ms": 199.34, "uptime": 0.98362},
    {"region": "emea", "latency_ms": 132.64, "uptime": 0.9851},
    {"region": "amer", "latency_ms": 130.38, "uptime": 0.97866},
    {"region": "amer", "latency_ms": 155.75, "uptime": 0.97379},
    {"region": "amer", "latency_ms": 207.35, "uptime": 0.98876},
    {"region": "amer", "latency_ms": 116.86, "uptime": 0.97658},
    {"region": "amer", "latency_ms": 146.43, "uptime": 0.98099},
    {"region": "amer", "latency_ms": 206.86, "uptime": 0.9869},
    {"region": "amer", "latency_ms": 174.05, "uptime": 0.99031},
    {"region": "amer", "latency_ms": 139.62, "uptime": 0.97104},
    {"region": "amer", "latency_ms": 135.89, "uptime": 0.98546},
    {"region": "amer", "latency_ms": 168.0, "uptime": 0.98838},
    {"region": "amer", "latency_ms": 112.87, "uptime": 0.99292},
    {"region": "amer", "latency_ms": 152.29, "uptime": 0.98653}
]

@app.post("/")
async def calculate_metrics(request: MetricsRequest):
    results = {}
    
    for region in request.regions:
        # Filter data for region
        region_data = [item for item in telemetry_data if item['region'] == region]
        
        if not region_data:
            # Return zeros if no data for region
            results[region] = {
                "avg_latency": 0.0,
                "p95_latency": 0.0,
                "avg_uptime": 0.0,
                "breaches": 0
            }
            continue
        
        latencies = [item['latency_ms'] for item in region_data]
        uptimes = [item['uptime'] for item in region_data]
        
        # Calculate metrics
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
    
    return {"regions": results}

@app.get("/")
async def root():
    return {
        "message": "eShopCo Telemetry API",
        "status": "active",
        "regions_available": ["amer", "emea", "apac"],
        "usage": "POST / with {'regions': ['amer','emea'], 'threshold_ms': 180}"
    }

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "healthy"}

# OPTIONS endpoint for CORS preflight
@app.options("/")
async def options_root():
    return {"message": "CORS enabled"}
