"""Conversation storage, persistent subscriber store, and persistent user tracking."""
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

# ── Persistent user store ─────────────────────────────────────────────────────
_USERS_FILE = "users.json"
_known_users: set[int] = set()
_today_new_count: int = 0


def _load_users() -> None:
    global _known_users
    if os.path.exists(_USERS_FILE):
        try:
            with open(_USERS_FILE, "r") as f:
                data = json.load(f)
            _known_users = set(data.get("users", []))
            logger.info(f"Loaded {len(_known_users)} known users from disk")
        except Exception as e:
            logger.error(f"Failed to load users: {e}")
            _known_users = set()


def _save_users() -> None:
    try:
        with open(_USERS_FILE, "w") as f:
            json.dump({"users": list(_known_users)}, f)
    except Exception as e:
        logger.error(f"Failed to save users: {e}")


def register_user(user_id: int) -> bool:
    """Record a user interaction. Returns True if this is a brand-new user."""
    global _today_new_count
    if user_id in _known_users:
        return False
    _known_users.add(user_id)
    _today_new_count += 1
    _save_users()
    return True


def get_user_count() -> int:
    return len(_known_users)


def get_today_new_count() -> int:
    return _today_new_count


def reset_today_count() -> None:
    global _today_new_count
    _today_new_count = 0


# Load users at module import time
_load_users()

# ── Persistent subscriber store ───────────────────────────────────────────────
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

# ── Conversation history ──────────────────────────────────────────────────────


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
