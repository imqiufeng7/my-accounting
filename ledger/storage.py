from __future__ import annotations
import csv
import os
import uuid
from pathlib import Path


def ensure_csv(path: Path, fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        _atomic_write(path, fields, [])


def read_rows(path: Path, fields: list[str]) -> list[dict]:
    ensure_csv(path, fields)
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _atomic_write(path: Path, fields: list[str], rows: list[dict]) -> None:
    tmp_path = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    with open(tmp_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})
    os.replace(tmp_path, path)


def append_row(path: Path, fields: list[str], row: dict) -> dict:
    rows = read_rows(path, fields)
    if "id" not in fields:
        raise ValueError("append_row requires an 'id' field for editable records")
    row = dict(row)
    row["id"] = uuid.uuid4().hex[:8]
    rows.append(row)
    _atomic_write(path, fields, rows)
    return row


def update_row(path: Path, fields: list[str], row_id: str, updates: dict) -> bool:
    rows = read_rows(path, fields)
    found = False
    for row in rows:
        if row.get("id") == row_id:
            row.update(updates)
            found = True
            break
    if found:
        _atomic_write(path, fields, rows)
    return found


def delete_row(path: Path, fields: list[str], row_id: str) -> bool:
    rows = read_rows(path, fields)
    new_rows = [r for r in rows if r.get("id") != row_id]
    if len(new_rows) == len(rows):
        return False
    _atomic_write(path, fields, new_rows)
    return True


def upsert_keyed_row(path: Path, fields: list[str], key_field: str, key_value: str, updates: dict) -> None:
    """Insert or update a row identified by a non-id key column (e.g. 股票代號, 帳戶名稱)."""
    rows = read_rows(path, fields)
    for row in rows:
        if row.get(key_field) == key_value:
            row.update(updates)
            _atomic_write(path, fields, rows)
            return
    new_row = {k: "" for k in fields}
    new_row[key_field] = key_value
    new_row.update(updates)
    rows.append(new_row)
    _atomic_write(path, fields, rows)


def delete_keyed_row(path: Path, fields: list[str], key_field: str, key_value: str) -> bool:
    rows = read_rows(path, fields)
    new_rows = [r for r in rows if r.get(key_field) != key_value]
    if len(new_rows) == len(rows):
        return False
    _atomic_write(path, fields, new_rows)
    return True
