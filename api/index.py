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
        # Load the JSON data
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
        
        print(f"✅ Successfully loaded {len(df_data)} records from covered-latency.json")
        return pd.DataFrame(df_data)
    
    except FileNotFoundError:
        raise Exception("covered-latency.json file not found. Make sure it exists in the api/ folder.")
    except json.JSONDecodeError:
        raise Exception("Invalid JSON format in covered-latency.json")
    except Exception as e:
        raise Exception(f"Error loading telemetry data: {e}")

# Load data at startup
try:
    df = load_telemetry_data()
    print(f"✅ Loaded {len(df)} telemetry records")
    print(f"✅ Available regions: {df['region'].unique().tolist()}")
except Exception as e:
    print(f"❌ Failed to load telemetry data: {e}")
    # Exit if data cannot be loaded
    raise e

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
        raise HTTPException(status_code=500, detail=f"Error calculating metrics: {str(e)}")

@app.get("/")
async def root():
    return {
        "message": "eShopCo Telemetry API", 
        "status": "active",
        "usage": "POST / with {'regions': ['amer','emea'], 'threshold_ms': 180}"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy", 
        "regions_available": df['region'].unique().tolist(),
        "total_records": len(df)
    }
