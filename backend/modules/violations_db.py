"""
Violations Database Module

Manages persistent storage of vehicle overspeed violations using SQLite.
The database file (violations.db) is created at the project root on first run.
"""

import sqlite3
import os
from datetime import datetime, timezone
from pathlib import Path

# Database file location — project root
DB_PATH = Path(__file__).resolve().parents[2] / "violations.db"


def get_connection():
    """Get a thread-safe SQLite connection with row_factory for dict-like access."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Create the violations table if it does not already exist, then run
    migrations to add any columns that are present in the current schema
    but missing from the on-disk table (handles databases created with
    older versions of the code).

    Called once on application startup.
    """
    # Full desired schema: (column_name, column_def)
    DESIRED_COLUMNS = [
        ("id",                 "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("video_name",         "TEXT    NOT NULL DEFAULT ''"),
        ("tracker_vehicle_id", "INTEGER NOT NULL DEFAULT 0"),
        ("vehicle_unique_id",  "TEXT    NOT NULL DEFAULT ''"),
        ("vehicle_type",       "TEXT    NOT NULL DEFAULT 'Unknown'"),
        ("detected_speed",     "REAL    NOT NULL DEFAULT 0"),
        ("speed_limit",        "REAL    NOT NULL DEFAULT 0"),
        ("violation_type",     "TEXT    NOT NULL DEFAULT 'Overspeed'"),
        ("timestamp",          "TEXT    NOT NULL DEFAULT ''"),
        ("area",               "TEXT    NOT NULL DEFAULT 'Unknown'"),
        ("frame_image",        "TEXT"),
        ("status",             "TEXT    NOT NULL DEFAULT 'reported'"),
    ]

    conn = get_connection()
    try:
        # 1. Create table with full schema if it doesn't exist yet
        col_defs = ",\n                ".join(f"{name} {defn}" for name, defn in DESIRED_COLUMNS)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS violations (
                {col_defs}
            )
        """)
        conn.commit()

        # 2. Migrate: add any columns that exist in desired schema but not on disk
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(violations)").fetchall()}
        for col_name, col_def in DESIRED_COLUMNS:
            if col_name not in existing_cols:
                # PRIMARY KEY / AUTOINCREMENT columns cannot be added via ALTER TABLE
                if "PRIMARY KEY" in col_def.upper():
                    continue
                try:
                    conn.execute(f"ALTER TABLE violations ADD COLUMN {col_name} {col_def}")
                    conn.commit()
                    print(f"[DB] Migration: added missing column '{col_name}'")
                except Exception as migrate_err:
                    print(f"[DB] Migration warning for column '{col_name}': {migrate_err}")

        print(f"[DB] Violations database ready at: {DB_PATH}")
    finally:
        conn.close()
    # Also initialise the accidents table
    _init_accidents_table()


def _init_accidents_table():
    """
    Create the accidents table and run migrations if columns are missing.
    Called from init_db() on startup.
    """
    ACCIDENTS_COLUMNS = [
        ("id",          "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("vehicle_ids", "TEXT    NOT NULL DEFAULT ''"),
        ("frame_number","INTEGER NOT NULL DEFAULT 0"),
        ("area",        "TEXT    NOT NULL DEFAULT 'Unknown'"),
        ("timestamp",   "TEXT    NOT NULL DEFAULT ''"),
        ("snapshot",    "TEXT"),
        ("signals",     "TEXT    NOT NULL DEFAULT ''"),
        ("details",     "TEXT    NOT NULL DEFAULT ''"),
        ("status",      "TEXT    NOT NULL DEFAULT 'reported'"),
    ]
    conn = get_connection()
    try:
        col_defs = ",\n                ".join(f"{name} {defn}" for name, defn in ACCIDENTS_COLUMNS)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS accidents (
                {col_defs}
            )
        """)
        conn.commit()

        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(accidents)").fetchall()}
        for col_name, col_def in ACCIDENTS_COLUMNS:
            if col_name not in existing_cols:
                if "PRIMARY KEY" in col_def.upper():
                    continue
                try:
                    conn.execute(f"ALTER TABLE accidents ADD COLUMN {col_name} {col_def}")
                    conn.commit()
                    print(f"[DB] Migration: added missing column 'accidents.{col_name}'")
                except Exception as e:
                    print(f"[DB] Migration warning for accidents.{col_name}: {e}")
        print("[DB] Accidents table ready.")
    finally:
        conn.close()


def add_violation(
    video_name: str,
    tracker_vehicle_id: int,
    vehicle_unique_id: str,
    vehicle_type: str,
    detected_speed: float,
    speed_limit: float,
    area: str = "Unknown",
    frame_image: str = None,
    violation_type: str = "Overspeed",
    status: str = "reported",
) -> dict:
    """
    Insert a new violation record.

    Returns:
        dict: The newly created violation record (including auto-generated id and timestamp).
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO violations
                (video_name, tracker_vehicle_id, vehicle_unique_id, vehicle_type,
                 detected_speed, speed_limit, violation_type, timestamp, area, frame_image, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                video_name,
                tracker_vehicle_id,
                vehicle_unique_id,
                vehicle_type,
                round(detected_speed, 1),
                round(speed_limit, 1),
                violation_type,
                timestamp,
                area,
                frame_image,
                status,
            ),
        )
        conn.commit()
        new_id = cursor.lastrowid
        return {
            "id": new_id,
            "video_name": video_name,
            "tracker_vehicle_id": tracker_vehicle_id,
            "vehicle_unique_id": vehicle_unique_id,
            "vehicle_type": vehicle_type,
            "detected_speed": round(detected_speed, 1),
            "speed_limit": round(speed_limit, 1),
            "violation_type": violation_type,
            "timestamp": timestamp,
            "area": area,
            "frame_image": frame_image,
            "status": status,
        }
    finally:
        conn.close()


def upsert_violation(
    video_name: str,
    tracker_vehicle_id: int,
    vehicle_unique_id: str,
    vehicle_type: str,
    detected_speed: float,
    speed_limit: float,
    area: str = "Unknown",
    frame_image: str = None,
    violation_type: str = "Overspeed",
    status: str = "reported",
) -> dict:
    """
    Insert a new violation or update an existing one, strictly keeping one record per vehicle ID.
    Always maintains the maximum detected speed for that vehicle.

    Returns:
        dict: containing 'action' ('inserted' or 'updated') and 'record' (the violation dict).
    """
    conn = get_connection()
    try:
        # Check if violation already exists for this EXACT globally unique ID and area
        existing = conn.execute(
            "SELECT * FROM violations WHERE vehicle_unique_id = ? AND area = ?",
            (vehicle_unique_id, area)
        ).fetchone()

        if existing:
            existing_dict = dict(existing)
            # Keep the maximum speed ever recorded for this vehicle
            new_speed = max(detected_speed, existing_dict["detected_speed"])
            timestamp = datetime.now(timezone.utc).isoformat()

            # Update the existing row with new timestamp, snapshot, and potentially higher speed
            conn.execute(
                """
                UPDATE violations
                SET detected_speed = ?, timestamp = ?, frame_image = ?, vehicle_type = ?
                WHERE id = ?
                """,
                (
                    round(new_speed, 1), timestamp, frame_image,
                    vehicle_type, existing_dict["id"]
                )
            )
            conn.commit()

            existing_dict["detected_speed"] = round(new_speed, 1)
            existing_dict["timestamp"] = timestamp
            existing_dict["frame_image"] = frame_image
            existing_dict["vehicle_type"] = vehicle_type

            return {"action": "updated", "record": existing_dict}
        else:
            # Does not exist, insert new
            record = add_violation(
                video_name, tracker_vehicle_id, vehicle_unique_id,
                vehicle_type, detected_speed, speed_limit, area,
                frame_image, violation_type, status
            )
            return {"action": "inserted", "record": record}
    finally:
        conn.close()


def get_all_violations() -> list[dict]:
    """
    Fetch all violations ordered by newest first.

    Returns:
        list[dict]: All violation records.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM violations ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_violations_by_vehicle(vehicle_unique_id: str) -> list[dict]:
    """
    Fetch all violations for a globally unique vehicle ID.

    Returns:
        list[dict]: Violation records for the given vehicle.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM violations WHERE vehicle_unique_id = ? ORDER BY id DESC",
            (vehicle_unique_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_violation(violation_id: int) -> bool:
    """
    Delete a violation record by its primary key.

    Returns:
        bool: True if the record was found and deleted, False otherwise.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM violations WHERE id = ?", (violation_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_all_violations() -> int:
    """
    Delete all violation records from the database.
    
    Returns:
        int: Number of records deleted.
    """
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM violations")
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Accidents CRUD
# ─────────────────────────────────────────────────────────────────────────────

def add_accident(
    vehicle_ids: str,
    frame_number: int,
    area: str = "Unknown",
    signals: str = "",
    details: str = "",
    snapshot: str = None,
    status: str = "reported",
) -> dict:
    """
    Insert a new accident record.

    Args:
        vehicle_ids: Comma-separated string of involved vehicle IDs, e.g. "3,7"
        frame_number: Frame index when accident was detected.
        area: Human-readable area label.
        signals: Comma-separated list of signals, e.g. "Collision,Sudden Stop"
        details: Human-readable description.
        snapshot: Base64-encoded JPEG of the frame (or None).
        status: Record status ('reported', 'reviewed', etc.).

    Returns:
        dict: The newly created accident record.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO accidents
                (vehicle_ids, frame_number, area, timestamp, snapshot, signals, details, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (vehicle_ids, frame_number, area, timestamp, snapshot, signals, details, status),
        )
        conn.commit()
        return {
            "id":           cursor.lastrowid,
            "vehicle_ids":  vehicle_ids,
            "frame_number": frame_number,
            "area":         area,
            "timestamp":    timestamp,
            "snapshot":     snapshot,
            "signals":      signals,
            "details":      details,
            "status":       status,
        }
    finally:
        conn.close()


def get_all_accidents() -> list:
    """Fetch all accident records, newest first."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM accidents ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def delete_accident(accident_id: int) -> bool:
    """Delete an accident record by its primary key."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM accidents WHERE id = ?", (accident_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_all_accidents() -> int:
    """Delete all accident records. Returns number deleted."""
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM accidents")
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
