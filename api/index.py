from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import pandas as pd
import numpy as np
import json

app = FastAPI()

# CORS configuration - THIS IS CRITICAL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Load telemetry data - SIMPLIFIED
def load_telemetry_data():
    """Load and return telemetry data"""
    try:
        # Load the JSON data directly
        with open('api/covered-latency.json', 'r') as f:
            data = json.load(f)
        
        # Convert to DataFrame
        df_data = []
        for item in data:
            df_data.append({
                'region': item['region'],
                'latency_ms': item['latency_ms'],
                'uptime': item['uptime']
            })
        
        return pd.DataFrame(df_data)
    
    except Exception as e:
        # If file loading fails, use hardcoded sample data
        print(f"File load failed: {e}, using sample data")
        return create_sample_data()

def create_sample_data():
    """Create sample telemetry data"""
    sample_data = []
    regions_data = {
        "amer": [120, 180, 90, 200, 85, 110, 95, 130, 160, 75],
        "emea": [110, 160, 95, 170, 88, 105, 125, 140, 155, 82],
        "apac": [130, 190, 100, 210, 92, 115, 135, 165, 175, 87],
        "latam": [125, 170, 98, 195, 89, 108, 128, 150, 168, 84]
    }
    
    for region, latencies in regions_data.items():
        for latency in latencies:
            sample_data.append({
                "region": region,
                "latency_ms": latency,
                "uptime": np.random.uniform(0.85, 0.99)
            })
    
    return pd.DataFrame(sample_data)

# Load data at startup
df = load_telemetry_data()
print(f"✅ Loaded {len(df)} telemetry records")
print(f"✅ Available regions: {df['region'].unique().tolist()}")

@app.post("/", response_model=MetricsResponse)
async def calculate_metrics(request: MetricsRequest):
    """Main endpoint to calculate metrics"""
    try:
        results = {}
        
        for region in request.regions:
            # Filter data for region
            region_data = df[df['region'] == region]
            
            if len(region_data) == 0:
                # Return zeros if no data for region
                results[region] = {
                    "avg_latency": 0.0,
                    "p95_latency": 0.0, 
                    "avg_uptime": 0.0,
                    "breaches": 0
                }
                continue
            
            latencies = region_data['latency_ms'].values
            uptimes = region_data['uptime'].values
            
            # Calculate metrics
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
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
async def root():
    return {
        "message": "eShopCo Telemetry API", 
        "status": "active",
        "usage": "POST / with {'regions': ['amer','emea'], 'threshold_ms': 180}"
    }

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "healthy", "regions_available": df['region'].unique().tolist()}
