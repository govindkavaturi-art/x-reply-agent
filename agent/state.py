import json
import os
from datetime import datetime, timezone

from agent.config import COOLDOWN_FILE, SURFACED_FILE, PAUSE_FLAG


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        return json.load(f)


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# --- Cooldown ---

def load_cooldown() -> dict[str, str]:
    return _load_json(COOLDOWN_FILE, {})


def save_cooldown(cooldown: dict[str, str]):
    _save_json(COOLDOWN_FILE, cooldown)


def prune_expired_cooldown(cooldown: dict[str, str]) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    return {
        username: expiry
        for username, expiry in cooldown.items()
        if datetime.fromisoformat(expiry) > now
    }


def add_cooldown(cooldown: dict[str, str], username: str, hours: int) -> dict[str, str]:
    from datetime import timedelta
    expiry = datetime.now(timezone.utc) + timedelta(hours=hours)
    cooldown[username] = expiry.isoformat()
    return cooldown


# --- Surfaced posts ---

def load_surfaced() -> list[str]:
    return _load_json(SURFACED_FILE, [])


def save_surfaced(surfaced: list[str]):
    _save_json(SURFACED_FILE, surfaced)


def add_surfaced(surfaced: list[str], post_ids: list[str]) -> list[str]:
    existing = set(surfaced)
    for pid in post_ids:
        if pid not in existing:
            surfaced.append(pid)
    return surfaced


# --- Pause flag ---

def pause_flag_exists() -> bool:
    return os.path.exists(PAUSE_FLAG)
