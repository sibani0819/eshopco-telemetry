from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import pandas as pd
import numpy as np
import json

app = FastAPI()

# CORS configuration
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

def load_telemetry_data():
    """Load telemetry data from covered-latency.json"""
    try:
        # Try different possible paths for Vercel
        possible_paths = [
            'covered-latency.json',
            'api/covered-latency.json',
            './covered-latency.json',
            './api/covered-latency.json'
        ]
        
        data = None
        used_path = None
        
        for path in possible_paths:
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    used_path = path
                    print(f"✅ Successfully loaded data from: {path}")
                    break
            except FileNotFoundError:
                continue
        
        if data is None:
            raise FileNotFoundError("Could not find covered-latency.json")
        
        # Convert to DataFrame - using YOUR actual field names
        df_data = []
        for item in data:
            df_data.append({
                'region': item.get('region', ''),
                'latency_ms': item.get('latency_ms', 0),
                'uptime': item.get('uptime_pct', 0.0) / 100.0  # Convert percentage to decimal
            })
        
        print(f"✅ Loaded {len(df_data)} records from {used_path}")
        return pd.DataFrame(df_data)
    
    except Exception as e:
        raise Exception(f"Error loading telemetry data: {e}")

# Load data at startup
try:
    df = load_telemetry_data()
    print(f"✅ Successfully loaded {len(df)} telemetry records")
    print(f"✅ Available regions: {df['region'].unique().tolist()}")
    data_loaded = True
except Exception as e:
    print(f"❌ CRITICAL: Failed to load telemetry data: {e}")
    # Create empty DataFrame to prevent crashes
    df = pd.DataFrame(columns=['region', 'latency_ms', 'uptime'])
    data_loaded = False

@app.post("/", response_model=MetricsResponse)
async def calculate_metrics(request: MetricsRequest):
    """Main endpoint to calculate metrics"""
    try:
        if not data_loaded:
            raise HTTPException(status_code=500, detail="Telemetry data not loaded")
        
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
        raise HTTPException(status_code=500, detail=f"Error calculating metrics: {str(e)}")

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
