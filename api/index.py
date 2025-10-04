from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import pandas as pd
import numpy as np
import json
import os

app = FastAPI()

# CORS configuration - FIXED
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Pydantic models
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

# Load telemetry data
def load_telemetry_data():
    """Load telemetry data from covered-latency.json"""
    try:
        file_path = os.path.join(os.path.dirname(__file__), 'covered-latency.json')
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        records = []
        for record in data:
            records.append({
                'region': record.get('region', ''),
                'latency_ms': record.get('latency_ms', 0),
                'uptime': record.get('uptime', 0.0)
            })
        
        return pd.DataFrame(records)
    
    except Exception as e:
        print(f"Error loading telemetry data: {e}")
        return create_sample_data()

def create_sample_data():
    """Create sample data as fallback"""
    sample_data = []
    regions = ["amer", "emea", "apac", "latam"]
    
    for region in regions:
        for i in range(100):
            latency = np.random.normal(120, 40)
            uptime = np.random.uniform(0.85, 1.0)
            
            sample_data.append({
                "region": region,
                "latency_ms": max(10, float(latency)),
                "uptime": float(uptime)
            })
    
    return pd.DataFrame(sample_data)

# Load data
telemetry_df = load_telemetry_data()
print(f"Loaded data with {len(telemetry_df)} records")

def calculate_metrics(df: pd.DataFrame, regions: List[str], threshold_ms: int) -> Dict[str, Any]:
    """Calculate metrics for specified regions"""
    results = {}
    
    for region in regions:
        # Filter data for the region
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
        
        # Calculate metrics
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
    """Main endpoint for metrics calculation"""
    try:
        print(f"Request: regions={request.regions}, threshold={request.threshold_ms}ms")
        
        results = calculate_metrics(telemetry_df, request.regions, request.threshold_ms)
        response = MetricsResponse(regions=results)
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/")
async def root():
    return {
        "message": "eShopCo Telemetry API",
        "status": "active",
        "usage": "POST / with {'regions': ['amer','emea'], 'threshold_ms': 180}"
    }

# Additional CORS handler for OPTIONS requests
@app.options("/")
async def options_root():
    return JSONResponse(
        content={"message": "CORS allowed"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
    
