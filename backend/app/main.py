from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
METRICS_DIR = BASE_DIR / "metrics"

app = FastAPI(title="5G Network Quality API", version="1.0.0")

# Allow broad CORS access for local dashboard development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


MAP_COLUMNS = ["square_id", "latitude", "longitude", "quality"]
FORECAST_COLUMNS = ["timestamp", "predicted_speed_mbps"]
QUALITY_TO_LABEL = {
    "good": "Tot",
    "medium": "Trung binh",
    "poor": "Yeu",
    "tot": "Tot",
    "trung binh": "Trung binh",
    "yeu": "Yeu",
}


def _first_csv(directory: Path) -> Path | None:
    files = sorted(directory.glob("*.csv"))
    return files[0] if files else None


def _fallback_map_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"square_id": "SQ-001", "latitude": 13.7563, "longitude": 100.5018, "quality": "Tot"},
            {"square_id": "SQ-002", "latitude": 13.7462, "longitude": 100.5347, "quality": "Trung binh"},
            {"square_id": "SQ-003", "latitude": 13.7367, "longitude": 100.5231, "quality": "Yeu"},
            {"square_id": "SQ-004", "latitude": 13.7645, "longitude": 100.5152, "quality": "Tot"},
            {"square_id": "SQ-005", "latitude": 13.7519, "longitude": 100.5414, "quality": "Trung binh"},
        ]
    )


def _fallback_forecast_data() -> pd.DataFrame:
    timestamps = pd.date_range("2026-03-13 08:00:00", periods=12, freq="h")
    predicted = [
        142.0,
        146.5,
        151.2,
        149.8,
        153.4,
        158.1,
        161.6,
        159.2,
        164.4,
        168.7,
        166.9,
        170.2,
    ]
    return pd.DataFrame({"timestamp": timestamps, "predicted_speed_mbps": predicted})


def _read_map_dataframe() -> pd.DataFrame:
    csv_path = _first_csv(DATA_DIR)
    if csv_path is None:
        return _fallback_map_data()

    df = pd.read_csv(csv_path)
    missing = [col for col in ["square_id", "latitude", "longitude"] if col not in df.columns]
    if missing:
        return _fallback_map_data()

    if "quality" not in df.columns:
        if "cluster_label" in df.columns:
            df["quality"] = df["cluster_label"]
        elif "network_quality" in df.columns:
            df["quality"] = df["network_quality"]
        else:
            df["quality"] = "Trung binh"

    out = df[MAP_COLUMNS].copy()
    out["quality"] = (
        out["quality"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(QUALITY_TO_LABEL)
        .fillna("Trung binh")
    )

    return out.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)


def _read_forecast_dataframe() -> pd.DataFrame:
    csv_path = _first_csv(METRICS_DIR)
    if csv_path is None:
        return _fallback_forecast_data()

    df = pd.read_csv(csv_path)

    timestamp_col = None
    for candidate in ["timestamp", "time", "datetime", "date"]:
        if candidate in df.columns:
            timestamp_col = candidate
            break

    value_col = None
    for candidate in ["predicted_speed_mbps", "forecast_speed", "prediction", "y_pred", "speed_mbps"]:
        if candidate in df.columns:
            value_col = candidate
            break

    if timestamp_col is None or value_col is None:
        return _fallback_forecast_data()

    out = df[[timestamp_col, value_col]].copy()
    out.columns = FORECAST_COLUMNS
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    out["predicted_speed_mbps"] = pd.to_numeric(out["predicted_speed_mbps"], errors="coerce")
    out = out.dropna(subset=FORECAST_COLUMNS).sort_values("timestamp")

    if out.empty:
        return _fallback_forecast_data()

    return out.reset_index(drop=True)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "5G Network Quality API is running."}


@app.get("/api/map-data")
def get_map_data() -> dict[str, Any]:
    df = _read_map_dataframe()

    features = []
    for _, row in df.iterrows():
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row["longitude"]), float(row["latitude"])],
                },
                "properties": {
                    "square_id": str(row["square_id"]),
                    "quality": str(row["quality"]),
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
    }


@app.get("/api/forecast-data")
def get_forecast_data() -> dict[str, list[Any]]:
    df = _read_forecast_dataframe()
    return {
        "time": df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S").tolist(),
        "predicted_speed_mbps": df["predicted_speed_mbps"].round(3).tolist(),
    }
