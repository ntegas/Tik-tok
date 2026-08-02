"""Простое JSON-хранилище очереди контента, разделяющее этапы пайплайна.

Статусы элемента очереди:
    researched -> drafted -> approved -> published -> analyzed
    (или rejected на этапе модерации)
"""
import json
import os
import uuid
from datetime import datetime, timezone

from config import DATA_DIR, STATE_FILE


def _ensure_state_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"items": []}, f, ensure_ascii=False, indent=2)


def _load():
    _ensure_state_file()
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def add_item(platform, trend, status="researched", **fields):
    state = _load()
    item = {
        "id": str(uuid.uuid4()),
        "platform": platform,
        "trend": trend,
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    state["items"].append(item)
    _save(state)
    return item


def update_item(item_id, **fields):
    state = _load()
    for item in state["items"]:
        if item["id"] == item_id:
            item.update(fields)
            item["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save(state)
            return item
    raise KeyError(f"item {item_id} not found")


def list_items(status=None, platform=None):
    state = _load()
    items = state["items"]
    if status is not None:
        items = [i for i in items if i["status"] == status]
    if platform is not None:
        items = [i for i in items if i["platform"] == platform]
    return items
