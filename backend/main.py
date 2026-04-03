import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import pandas as pd
import resend
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
METRICS_DIR = BASE_DIR / "metrics"

MAP_CSV = DATA_DIR / "map_data.csv"
FORECAST_CSV = METRICS_DIR / "forecast_data.csv"

app = FastAPI(title="5G Network Quality API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:8080",
        "http://localhost:4173",
        "https://d33m3uevv39v9p.cloudfront.net",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


resend.api_key = os.environ.get("RESEND_API_KEY", "")
CONTACT_TO_EMAIL = os.environ.get("CONTACT_TO_EMAIL", "lhtthong.forwork@outlook.com")


class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    message: str


# ── Map data ────────────────────────────────────────────────────

def _read_map_data() -> list[dict[str, Any]]:
    """Read map_data.csv and return list of {lat, lng, cluster} dicts."""
    if not MAP_CSV.is_file():
        raise HTTPException(status_code=404, detail=f"{MAP_CSV.name} not found.")

    try:
        df = pd.read_csv(MAP_CSV)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read {MAP_CSV.name}: {exc}")

    required = {"lat", "lng", "cluster"}
    if not required.issubset(df.columns):
        raise HTTPException(
            status_code=500,
            detail=f"{MAP_CSV.name} missing columns: {required - set(df.columns)}",
        )

    df = df[["lat", "lng", "cluster"]].dropna()
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lng"] = pd.to_numeric(df["lng"], errors="coerce")
    df["cluster"] = pd.to_numeric(df["cluster"], errors="coerce").astype(int)
    df = df.dropna()

    return df.to_dict(orient="records")


# ── Forecast data ───────────────────────────────────────────────

def _read_forecast_data() -> list[dict[str, Any]]:
    """Read forecast_data.csv and return list of {timestamp, predicted_throughput, predicted_latency} dicts."""
    if not FORECAST_CSV.is_file():
        raise HTTPException(status_code=404, detail=f"{FORECAST_CSV.name} not found.")

    try:
        df = pd.read_csv(FORECAST_CSV)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read {FORECAST_CSV.name}: {exc}")

    required = {"timestamp", "predicted_throughput", "predicted_latency"}
    if not required.issubset(df.columns):
        raise HTTPException(
            status_code=500,
            detail=f"{FORECAST_CSV.name} missing columns: {required - set(df.columns)}",
        )

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["predicted_throughput"] = pd.to_numeric(df["predicted_throughput"], errors="coerce")
    df["predicted_latency"] = pd.to_numeric(df["predicted_latency"], errors="coerce")
    df = df.dropna(subset=["timestamp", "predicted_throughput", "predicted_latency"])
    df = df.sort_values("timestamp")

    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    df["predicted_throughput"] = df["predicted_throughput"].round(2)
    df["predicted_latency"] = df["predicted_latency"].round(2)

    return df[["timestamp", "predicted_throughput", "predicted_latency"]].to_dict(orient="records")


# ── Routes ──────────────────────────────────────────────────────

@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "5G Network Quality API is running."}


@app.get("/api/map-data")
def get_map_data() -> list[dict[str, Any]]:
    return _read_map_data()


@app.get("/api/forecast-data")
def get_forecast_data() -> list[dict[str, Any]]:
    return _read_forecast_data()


@app.post("/api/contact")
def send_contact_email(body: ContactRequest) -> dict[str, str]:
    if not resend.api_key:
        raise HTTPException(status_code=500, detail="Email service is not configured.")

    params: resend.Emails.SendParams = {
        "from": "5G Dashboard <onboarding@resend.dev>",
        "to": [CONTACT_TO_EMAIL],
        "reply_to": body.email,
        "subject": f"[5G Dashboard] Feedback from {body.name}",
        "html": (
            f"<h2>New feedback from {body.name}</h2>"
            f"<p><strong>Email:</strong> {body.email}</p>"
            f"<p><strong>Message:</strong></p>"
            f"<p>{body.message}</p>"
        ),
    }

    try:
        email = resend.Emails.send(params)
    except resend.exceptions.ResendError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if not email or "id" not in email:
        raise HTTPException(status_code=502, detail="Failed to send email.")

    return {"status": "sent"}


# ── AWS Lambda entry point (Mangum) ─────────────────────────────
from mangum import Mangum

handler = Mangum(app)
