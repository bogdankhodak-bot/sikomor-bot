"""Simple in-memory conversation storage with per-user history."""
from collections import defaultdict
import time

MAX_HISTORY = 20
SESSION_TIMEOUT = 30 * 60  # 30 minutes in seconds

_history: dict[int, list[dict]] = defaultdict(list)
_last_active: dict[int, float] = {}
_known_users: set[int] = set()


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
