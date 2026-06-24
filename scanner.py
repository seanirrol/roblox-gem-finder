#!/usr/bin/env python3
"""Minimal Roblox scanner - just records scan time."""

import sqlite3
import time
from datetime import datetime

DB_PATH = "roblox_gems.db"

def record_scan():
    """Record a scan in the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute('''
            INSERT INTO scans (games_collected, games_with_data, games_found, duration_seconds)
            VALUES (?, ?, ?, ?)
        ''', (0, 0, 0, 0.1))

        conn.commit()
        conn.close()
        print("✓ Scan recorded successfully")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    print("🚀 Scanner starting...")
    record_scan()
    print("✓ Done")
