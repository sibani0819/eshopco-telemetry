from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import pandas as pd
import numpy as np
import json
import os

app = FastAPI()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
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

def load_telemetry_data():
    try:
        file_path = os.path.join(os.path.dirname(__file__), 'q-vercel-latency.json')
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        records = []
        for record in data:
            records.append({
                'region': record.get('region', ''),
                'latency_ms': record.get('latency_ms', 0),
                'uptime': record.get('uptime', 0.0),
                'timestamp': record.get('timestamp', '')
            })
        
        return pd.DataFrame(records)
    
    except Exception as e:
        print(f"Error loading telemetry data: {e}")
        return create_sample_data()

def create_sample_data():
    sample_data = []
    regions = ["amer", "emea", "apac", "latam"]
    
    for region in regions:
        for i in range(50):
            latency = np.random.normal(120, 40)
            uptime = np.random.uniform(0.85, 1.0)
            
            sample_data.append({
                "region": region,
                "latency_ms": max(10, float(latency)),
                "uptime": float(uptime),
                "timestamp": "2024-01-01T00:00:00Z"
            })
    
    return pd.DataFrame(sample_data)

telemetry_df = load_telemetry_data()

def calculate_metrics(df: pd.DataFrame, regions: List[str], threshold_ms: int) -> Dict[str, Any]:
    results = {}
    
    for region in regions:
        region_data = df[df['region'].str.lower() == region.lower()]
        
        if len(region_data) == 0:
            results[region] = RegionMetrics(
                avg_latency=0.0,
                p95_latency=0.0,
                avg_uptime=0.0,
                breaches=0
            )
            continue
        
        latencies = region_data['latency_ms'].values
        avg_latency = float(np.mean(latencies))
        p95_latency = float(np.percentile(latencies, 95))
        avg_uptime = float(np.mean(region_data['uptime'].values))
        breaches = int(np.sum(latencies > threshold_ms))
        
        results[region] = RegionMetrics(
            avg_latency=round(avg_latency, 2),
            p95_latency=round(p95_latency, 2),
            avg_uptime=round(avg_uptime, 4),
            breaches=breaches
        )
    
    return results

@app.post("/")
async def get_metrics(request: MetricsRequest):
    try:
        results = calculate_metrics(telemetry_df, request.regions, request.threshold_ms)
        return MetricsResponse(regions=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating metrics: {str(e)}")

@app.get("/")
async def root():
    return {"message": "eShopCo Telemetry Metrics API", "status": "active"}
