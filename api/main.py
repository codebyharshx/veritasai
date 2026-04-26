"""Veritas API — FastAPI backend for the healthcare trust layer.

Endpoints per Section 2.5 of PRD/TRD.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import mlflow

from api.routers import facilities, maps, query, trust, health

# Enable MLflow autolog
mlflow.openai.autolog()

app = FastAPI(
    title="Veritas API",
    description="Truth Layer for Indian Healthcare — API Backend",
    version="1.0.0",
)

# CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to Streamlit URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(facilities.router, prefix="/api", tags=["Facilities"])
app.include_router(maps.router, prefix="/api", tags=["Maps"])
app.include_router(query.router, prefix="/api", tags=["Query"])
app.include_router(trust.router, prefix="/api", tags=["Trust"])
app.include_router(health.router, prefix="/api", tags=["Health"])


@app.get("/")
async def root():
    return {
        "name": "Veritas API",
        "description": "Truth Layer for Indian Healthcare",
        "docs": "/docs",
    }
