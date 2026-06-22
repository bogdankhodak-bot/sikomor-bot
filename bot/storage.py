"""Simple in-memory conversation storage with per-user history."""
from collections import defaultdict
from typing import Optional

MAX_HISTORY = 20

_history: dict[int, list[dict]] = defaultdict(list)


def add_message(user_id: int, role: str, content: str) -> None:
    _history[user_id].append({"role": role, "content": content})
    if len(_history[user_id]) > MAX_HISTORY:
        _history[user_id] = _history[user_id][-MAX_HISTORY:]


def get_history(user_id: int) -> list[dict]:
    return list(_history[user_id])


def clear_history(user_id: int) -> None:
    _history[user_id] = []


def get_all_user_ids() -> list[int]:
    return list(_history.keys())
