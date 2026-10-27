"""Authenticated, single-owner paper-order inbox. No broker connection in the web process."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hmac
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from dotenv import load_dotenv

# Dedicated private runtime configuration; existing service credentials are untouched.
load_dotenv(Path(__file__).with_name('paper-secrets.conf'), override=False)

router = APIRouter(prefix='/paper-signals', tags=['Paper trading'])


class Signal(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    signal_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,48}$')
    direction: Literal['LONG', 'SHORT'] = 'LONG'
    ticker: str = Field(pattern=r'^[A-Z0-9][A-Z0-9 .-]{0,19}$')
    price: float = Field(gt=0, allow_inf_nan=False)
    timestamp: int = Field(gt=0)
    limit_price: float = Field(gt=0, le=1000, allow_inf_nan=False)


class Result(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    status: Literal['submitted', 'filled', 'cancelled', 'rejected', 'unknown']
    order_id: int | None = Field(default=None, ge=0)
    perm_id: int | None = Field(default=None, ge=0)
    conid: int | None = Field(default=None, gt=0)
    filled: float = Field(default=0, ge=0, le=1, allow_inf_nan=False)
    average_fill_price: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    reason: Literal['broker_status', 'broker_unavailable', 'contract_rejected', 'expired', 'uncertain']


def authorize(authorization: str | None = Header(default=None)):
    token = os.getenv('PAPER_API_TOKEN', '')
    if len(token) < 32:
        raise HTTPException(503, 'Paper execution is not configured')
    if not authorization or not hmac.compare_digest(authorization.encode(), ('Bearer ' + token).encode()):
        raise HTTPException(401, 'Invalid paper API credential')


@contextmanager
def locked_store():
    root = Path(os.getenv('PAPER_QUEUE_DIR', 'data/paper-signals'))
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (root / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield root


def save(path, record):
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False) as file:
        temp = Path(file.name)
        json.dump(record, file, allow_nan=False)
        file.flush()
        os.fsync(file.fileno())
    try:
        temp.replace(path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        temp.unlink(missing_ok=True)


@router.post('', dependencies=[Depends(authorize)], status_code=202)
def receive(signal: Signal):
    payload = signal.model_dump()
    with locked_store() as root:
        path = root / (signal.signal_id + '.json')
        if path.exists():
            existing = json.loads(path.read_text())
            if {'direction': 'LONG', **existing['signal']} != payload:
                raise HTTPException(409, 'Signal ID already has different content')
            return existing
        if signal.timestamp <= time.time():
            raise HTTPException(422, 'Forecast target time must be in the future')
        if round(signal.limit_price, 2) != signal.limit_price:
            raise HTTPException(422, 'Limit must have at most two decimal places')
        if (signal.direction == 'LONG' and signal.price <= signal.limit_price or
                signal.direction == 'SHORT' and signal.price >= signal.limit_price):
            raise HTTPException(422, 'Forecast must be above a LONG limit or below a SHORT limit')
        today = datetime.now(timezone.utc).date().isoformat()
        # One credential represents one owner; changing names cannot bypass this quota.
        count = sum(json.loads(p.read_text())['received_at'][:10] == today for p in root.glob('*.json'))
        if count >= 5:
            raise HTTPException(429, 'Daily paper signal limit reached (5 per UTC day)')
        record = {'signal': payload, 'received_at': datetime.now(timezone.utc).isoformat(),
                  'status': 'queued', 'action': 'SELL' if signal.direction == 'SHORT' else 'BUY', 'quantity': 1}
        save(path, record)
        return record


@router.post('/claim', dependencies=[Depends(authorize)])
def claim():
    with locked_store() as root:
        records = [(p, json.loads(p.read_text())) for p in root.glob('*.json')]
        for path, record in sorted(records, key=lambda item: item[1]['received_at']):
            if record['status'] != 'queued':
                continue
            if record['signal']['timestamp'] <= time.time():
                record.update(status='rejected', reason='expired')
                save(path, record)
                continue
            # A lost response or crashed worker must not cause an automatic second claim/order.
            record.update(status='claimed', claimed_at=datetime.now(timezone.utc).isoformat())
            save(path, record)
            return record
    return None


def signal_path(root, signal_id):
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', signal_id):
        raise HTTPException(404, 'Signal not found')
    path = root / (signal_id + '.json')
    if not path.exists():
        raise HTTPException(404, 'Signal not found')
    return path


@router.get('/{signal_id}', dependencies=[Depends(authorize)])
def status(signal_id: str):
    with locked_store() as root:
        return json.loads(signal_path(root, signal_id).read_text())


@router.post('/{signal_id}/result', dependencies=[Depends(authorize)])
def report(signal_id: str, result: Result):
    with locked_store() as root:
        path = signal_path(root, signal_id)
        record = json.loads(path.read_text())
        payload = result.model_dump()
        if record.get('result') == payload:
            return record
        if record['status'] != 'claimed':
            raise HTTPException(409, 'Signal already completed or was not claimed')
        record.update(status=result.status, result=payload,
                      updated_at=datetime.now(timezone.utc).isoformat())
        save(path, record)
        return record
