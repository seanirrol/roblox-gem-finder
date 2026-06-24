#!/usr/bin/env python3
"""
SQLite database operations for Roblox Gem Finder.
Replaces the text file master list with a proper database.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = "roblox_gems.db"

def init_db():
    """Create database schema if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Games table - unique games found
    c.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY,
            universe_id INTEGER UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            url TEXT UNIQUE,
            is_archived BOOLEAN DEFAULT 0,
            archived_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(universe_id)
        )
    ''')

    # Game stats - track stats over time
    c.execute('''
        CREATE TABLE IF NOT EXISTS game_stats (
            id INTEGER PRIMARY KEY,
            game_id INTEGER NOT NULL,
            visits INTEGER,
            active_players INTEGER,
            approval_rate INTEGER,
            content_maturity TEXT,
            is_sponsored BOOLEAN,
            scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE
        )
    ''')

    # Tier matches - which tiers each game matched
    c.execute('''
        CREATE TABLE IF NOT EXISTS tier_matches (
            id INTEGER PRIMARY KEY,
            game_id INTEGER NOT NULL,
            tier_level INTEGER,
            scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE
        )
    ''')

    # Blacklist - manually removed games
    c.execute('''
        CREATE TABLE IF NOT EXISTS blacklist (
            id INTEGER PRIMARY KEY,
            url TEXT UNIQUE,
            normalized_name TEXT,
            reason TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Scans - track each scan
    c.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY,
            scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            games_collected INTEGER,
            games_with_data INTEGER,
            games_found INTEGER,
            duration_seconds REAL
        )
    ''')

    # Scanner logs - track console output
    c.execute('''
        CREATE TABLE IF NOT EXISTS scanner_logs (
            id INTEGER PRIMARY KEY,
            message TEXT NOT NULL,
            log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create indexes for performance
    c.execute('CREATE INDEX IF NOT EXISTS idx_game_universe ON games(universe_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_stats_game ON game_stats(game_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_stats_scan ON game_stats(scan_time)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_tier_game ON tier_matches(game_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_blacklist_name ON blacklist(normalized_name)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_logs_time ON scanner_logs(log_time)')

    conn.commit()
    conn.close()

def add_game(universe_id, name, description, url):
    """Add or get a game. Returns game_id."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        c.execute(
            'INSERT INTO games (universe_id, name, description, url) VALUES (?, ?, ?, ?)',
            (universe_id, name, description, url)
        )
        conn.commit()
        game_id = c.lastrowid
    except sqlite3.IntegrityError:
        # Game already exists
        c.execute('SELECT id FROM games WHERE universe_id = ?', (universe_id,))
        game_id = c.fetchone()[0]

    conn.close()
    return game_id

def add_game_stats(game_id, visits, active_players, approval_rate, content_maturity, is_sponsored):
    """Add stats for a game at current scan time."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        INSERT INTO game_stats (game_id, visits, active_players, approval_rate, content_maturity, is_sponsored)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (game_id, visits, active_players, approval_rate, content_maturity, is_sponsored))

    conn.commit()
    conn.close()

def add_tier_match(game_id, tier_level):
    """Record that a game matched a tier."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        'INSERT INTO tier_matches (game_id, tier_level) VALUES (?, ?)',
        (game_id, tier_level)
    )

    conn.commit()
    conn.close()

def is_blacklisted(url=None, normalized_name=None):
    """Check if a game is blacklisted by URL or name."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if url:
        c.execute('SELECT 1 FROM blacklist WHERE url = ?', (url,))
        if c.fetchone():
            conn.close()
            return True

    if normalized_name:
        c.execute('SELECT 1 FROM blacklist WHERE normalized_name = ?', (normalized_name,))
        if c.fetchone():
            conn.close()
            return True

    conn.close()
    return False

def add_to_blacklist(url=None, normalized_name=None, reason=""):
    """Add a game to blacklist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if url:
        c.execute(
            'INSERT OR IGNORE INTO blacklist (url, reason) VALUES (?, ?)',
            (url, reason)
        )

    if normalized_name:
        c.execute(
            'INSERT OR IGNORE INTO blacklist (normalized_name, reason) VALUES (?, ?)',
            (normalized_name, reason)
        )

    conn.commit()
    conn.close()

def get_all_games():
    """Get all games with their latest stats."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT
            g.id, g.universe_id, g.name, g.url,
            gs.visits, gs.active_players, gs.approval_rate, gs.content_maturity,
            MAX(gs.scan_time) as last_scan
        FROM games g
        LEFT JOIN game_stats gs ON g.id = gs.game_id
        GROUP BY g.id
        ORDER BY g.name
    ''')

    games = [dict(row) for row in c.fetchall()]
    conn.close()
    return games

def get_games_by_tier(tier_level):
    """Get games that matched a specific tier."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT
            g.id, g.universe_id, g.name, g.url,
            gs.visits, gs.active_players, gs.approval_rate,
            MAX(gs.scan_time) as last_scan
        FROM games g
        JOIN tier_matches tm ON g.id = tm.game_id
        LEFT JOIN game_stats gs ON g.id = gs.game_id
        WHERE tm.tier_level = ?
        GROUP BY g.id
        ORDER BY g.name
    ''', (tier_level,))

    games = [dict(row) for row in c.fetchall()]
    conn.close()
    return games

def get_trending_games(days=7):
    """Get games with rising player counts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT
            g.name, g.url,
            MAX(gs.active_players) as current_players,
            MIN(gs.active_players) as previous_players,
            MAX(gs.active_players) - MIN(gs.active_players) as growth
        FROM games g
        JOIN game_stats gs ON g.id = gs.game_id
        WHERE gs.scan_time >= datetime('now', '-' || ? || ' days')
        GROUP BY g.id
        HAVING growth > 0
        ORDER BY growth DESC
    ''', (days,))

    games = [dict(row) for row in c.fetchall()]
    conn.close()
    return games

def record_scan(games_collected, games_with_data, games_found, duration):
    """Record metadata about a scan."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        INSERT INTO scans (games_collected, games_with_data, games_found, duration_seconds)
        VALUES (?, ?, ?, ?)
    ''', (games_collected, games_with_data, games_found, duration))

    conn.commit()
    conn.close()

def archive_game(game_id):
    """Archive a single game."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        'UPDATE games SET is_archived = 1, archived_at = CURRENT_TIMESTAMP WHERE id = ?',
        (game_id,)
    )
    conn.commit()
    conn.close()

def archive_games_bulk(game_ids):
    """Archive multiple games."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    placeholders = ','.join('?' * len(game_ids))
    c.execute(
        f'UPDATE games SET is_archived = 1, archived_at = CURRENT_TIMESTAMP WHERE id IN ({placeholders})',
        game_ids
    )
    conn.commit()
    conn.close()

def unarchive_game(game_id):
    """Unarchive a single game."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        'UPDATE games SET is_archived = 0, archived_at = NULL WHERE id = ?',
        (game_id,)
    )
    conn.commit()
    conn.close()

def delete_games_bulk(game_ids):
    """Permanently delete archived games."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    placeholders = ','.join('?' * len(game_ids))
    c.execute(f'DELETE FROM games WHERE id IN ({placeholders})', game_ids)
    c.execute(f'DELETE FROM game_stats WHERE game_id IN ({placeholders})', game_ids)
    c.execute(f'DELETE FROM tier_matches WHERE game_id IN ({placeholders})', game_ids)
    conn.commit()
    conn.close()

def get_archived_games():
    """Get all archived games."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT
            g.id, g.universe_id, g.name, g.url,
            gs.visits, gs.active_players, gs.approval_rate,
            MAX(gs.scan_time) as last_scan
        FROM games g
        LEFT JOIN game_stats gs ON g.id = gs.game_id
        WHERE g.is_archived = 1
        GROUP BY g.id
        ORDER BY g.archived_at DESC
    ''')

    games = [dict(row) for row in c.fetchall()]
    conn.close()
    return games

def get_stats():
    """Get overall statistics."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    stats = {}

    # Total games (excluding archived)
    c.execute('SELECT COUNT(*) FROM games WHERE is_archived = 0')
    stats['total_games'] = c.fetchone()[0]

    # Archived games
    c.execute('SELECT COUNT(*) FROM games WHERE is_archived = 1')
    stats['archived_games'] = c.fetchone()[0]

    # Recent scans
    c.execute('''
        SELECT COUNT(*) FROM scans
        WHERE scan_time >= datetime('now', '-1 day')
    ''')
    stats['scans_today'] = c.fetchone()[0]

    # Last scan
    c.execute('SELECT MAX(scan_time) FROM scans')
    result = c.fetchone()[0]
    stats['last_scan'] = result if result else None

    # Games found this week
    c.execute('''
        SELECT COUNT(DISTINCT game_id) FROM tier_matches
        WHERE scan_time >= datetime('now', '-7 days')
    ''')
    stats['new_games_week'] = c.fetchone()[0]

    conn.close()
    return stats

def add_log(message):
    """Add a message to scanner logs."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO scanner_logs (message) VALUES (?)', (message,))
    conn.commit()
    conn.close()

def get_logs(limit=50):
    """Get recent scanner logs."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT message, log_time FROM scanner_logs ORDER BY log_time DESC LIMIT ?', (limit,))
    logs = [dict(row) for row in c.fetchall()]
    conn.close()
    return list(reversed(logs))

def get_scanner_status():
    """Get scanner status (last scan time)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT MAX(scan_time) FROM scans')
    last_scan = c.fetchone()[0]
    conn.close()
    return {"last_scan": last_scan}
