"""Simple in-memory conversation storage with per-user history, plus persistent subscriber store."""
from collections import defaultdict
import json
import logging
import os
import time

logger = logging.getLogger(__name__)

MAX_HISTORY = 20
SESSION_TIMEOUT = 30 * 60  # 30 minutes in seconds

_history: dict[int, list[dict]] = defaultdict(list)
_last_active: dict[int, float] = {}
_known_users: set[int] = set()

# Persistent subscriber store
_SUBSCRIBERS_FILE = "subscribers.json"
_subscribers: set[int] = set()


def _load_subscribers() -> None:
    global _subscribers
    if os.path.exists(_SUBSCRIBERS_FILE):
        try:
            with open(_SUBSCRIBERS_FILE, "r") as f:
                data = json.load(f)
            _subscribers = set(data.get("subscribers", []))
            logger.info(f"Loaded {len(_subscribers)} subscribers from disk")
        except Exception as e:
            logger.error(f"Failed to load subscribers: {e}")
            _subscribers = set()


def _save_subscribers() -> None:
    try:
        with open(_SUBSCRIBERS_FILE, "w") as f:
            json.dump({"subscribers": list(_subscribers)}, f)
    except Exception as e:
        logger.error(f"Failed to save subscribers: {e}")


def subscribe(user_id: int) -> None:
    _subscribers.add(user_id)
    _save_subscribers()


def unsubscribe(user_id: int) -> None:
    _subscribers.discard(user_id)
    _save_subscribers()


def is_subscribed(user_id: int) -> bool:
    return user_id in _subscribers


def get_all_subscribers() -> list[int]:
    return list(_subscribers)


# Load subscribers at module import time
_load_subscribers()


def _check_timeout(user_id: int) -> None:
    last = _last_active.get(user_id)
    if last is not None and (time.time() - last) > SESSION_TIMEOUT:
        _history[user_id] = []


def add_message(user_id: int, role: str, content: str) -> None:
    _last_active[user_id] = time.time()
    _history[user_id].append({"role": role, "content": content})
    if len(_history[user_id]) > MAX_HISTORY:
        _history[user_id] = _history[user_id][-MAX_HISTORY:]


def get_history(user_id: int) -> list[dict]:
    _check_timeout(user_id)
    return list(_history[user_id])


def clear_history(user_id: int) -> None:
    _history[user_id] = []
    _last_active.pop(user_id, None)


def get_all_user_ids() -> list[int]:
    return list(_history.keys())


def register_user(user_id: int) -> bool:
    """Register a user. Returns True if this is a new user, False if already known."""
    if user_id in _known_users:
        return False
    _known_users.add(user_id)
    return True


def get_user_count() -> int:
    return len(_known_users)
