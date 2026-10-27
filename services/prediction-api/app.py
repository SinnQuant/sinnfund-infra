from fastapi import FastAPI, Response
from pydantic import BaseModel
from dotenv import load_dotenv

import csv
import glob
import logging
import os
import time

import pandas as pd
import requests


# ============================================================
# Configuration
# ============================================================

load_dotenv()

API_KEY = os.getenv("TWELVE_DATA_API_KEY")

PREDICTIONS_DIRECTORY = "submitted_predictions"
LOG_DIRECTORY = "logs"

# 180 days
RECENT_SECONDS = 180 * 24 * 60 * 60

os.makedirs(PREDICTIONS_DIRECTORY, exist_ok=True)
os.makedirs(LOG_DIRECTORY, exist_ok=True)


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    filename=os.path.join(LOG_DIRECTORY, "server.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# Application
# ============================================================

app = FastAPI()


# ============================================================
# Models
# ============================================================

class Prediction(BaseModel):
    researcher: str
    ticker: str
    price: float
    timestamp: int


# ============================================================
# Session / File Management
# ============================================================

def get_current_file():
    pattern = os.path.join(
        PREDICTIONS_DIRECTORY,
        "predictions_*.txt"
    )

    files = glob.glob(pattern)

    if files:
        newest_file = max(
            files,
            key=get_file_timestamp
        )

        timestamp = get_file_timestamp(newest_file)

        if time.time() - timestamp < RECENT_SECONDS:
            return newest_file

    timestamp = int(time.time())

    return os.path.join(
        PREDICTIONS_DIRECTORY,
        f"predictions_{timestamp}.txt"
    )


def get_file_timestamp(filepath):
    filename = os.path.basename(filepath)

    return int(
        filename
        .replace("predictions_", "")
        .replace(".txt", "")
    )


current_file = get_current_file()


# ============================================================
# Market Data
# ============================================================

def get_price(ticker):
    url = "https://api.twelvedata.com/quote"

    params = {
        "symbol": ticker,
        "apikey": API_KEY
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=5
        )
    except requests.RequestException as error:
        logger.error(
            f"Price request failed ticker={ticker} error={error}"
        )
        return -1

    if response.status_code != 200:
        logger.warning(
            f"Price API error ticker={ticker} "
            f"status={response.status_code}"
        )
        return -1

    data = response.json()

    if "previous_close" not in data:
        logger.warning(
            f"No previous close found ticker={ticker}"
        )
        return -1

    return float(data["previous_close"])


# ============================================================
# Portfolio Logic
# ============================================================

def build_portfolio():
    logger.info(
        f"Building portfolio from {current_file}"
    )

    if not os.path.exists(current_file):
        logger.warning("No current prediction file")
        return empty_portfolio()

    df = pd.read_csv(current_file)

    prices = {}

    for ticker in df["ticker"].unique():
        prices[ticker] = get_price(ticker)

    rows = []

    # Keep only positive trades
    for _, prediction in df.iterrows():
        ticker = prediction["ticker"]
        current_price = prices[ticker]

        if current_price == -1:
            logger.warning(
                f"Skipping ticker={ticker} due to missing price"
            )
            continue

        # Positive trade means predicted price is above current price
        if prediction["price"] > current_price:
            rows.append({
                "researcher": prediction["researcher"],
                "symbol": ticker
            })

    if not rows:
        return empty_portfolio()

    result = pd.DataFrame(rows)

    # Split portfolio evenly across all positive trades
    weight = 1 / len(result)

    result["percentage_of_portfolio"] = weight

    logger.info(
        f"Portfolio built with {len(result)} positive trades"
    )

    return result[
        [
            "researcher",
            "symbol",
            "percentage_of_portfolio"
        ]
    ]

def empty_portfolio():
    return pd.DataFrame(columns=[
        "researcher",
        "symbol",
        "percentage_of_portfolio"
    ])


# ============================================================
# API Routes
# ============================================================

@app.post("/prediction")
def submit_prediction(prediction: Prediction):
    logger.info(
        f"Prediction received "
        f"researcher={prediction.researcher} "
        f"ticker={prediction.ticker} "
        f"price={prediction.price} "
        f"timestamp={prediction.timestamp}"
    )

    current_price = get_price(prediction.ticker)

    if current_price == -1:
        logger.warning(
            f"Invalid ticker submitted: {prediction.ticker}"
        )

        return {
            "status": "invalid ticker"
        }

    file_exists = os.path.exists(current_file)

    with open(current_file, "a", newline="") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "researcher",
                "ticker",
                "price",
                "timestamp"
            ])

        writer.writerow([
            prediction.researcher,
            prediction.ticker,
            prediction.price,
            prediction.timestamp
        ])

    logger.info(
        f"Prediction saved to {current_file}"
    )

    return {
        "status": "ok",
        "session": current_file
    }


@app.post("/reset")
def reset():
    global current_file

    old_file = current_file
    timestamp = int(time.time())

    current_file = os.path.join(
        PREDICTIONS_DIRECTORY,
        f"predictions_{timestamp}.txt"
    )

    logger.info(
        f"Session reset "
        f"old={old_file} "
        f"new={current_file}"
    )

    return {
        "status": "reset",
        "session": current_file
    }


@app.get("/portfolio")
def portfolio():
    df = build_portfolio()

    return Response(
        df.to_csv(index=False),
        media_type="text/plain"
    )

# Explicit authenticated paper inbox; legacy research submissions never execute orders.
from paper_signals import router as paper_router
app.include_router(paper_router)
