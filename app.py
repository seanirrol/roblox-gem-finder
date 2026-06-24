#!/usr/bin/env python3
"""
Flask web server for Roblox Gem Finder.
Provides REST API and serves React UI.
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import database
import sqlite3
import json
import os

app = Flask(__name__, static_folder='.')
CORS(app)

# Initialize database on startup
database.init_db()

# ─────────────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────────────

@app.route('/api/games', methods=['GET'])
def get_games():
    """Get all non-archived games."""
    conn = sqlite3.connect(database.DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''
        SELECT
            g.id, g.universe_id, g.name, g.url,
            gs.visits, gs.active_players, gs.approval_rate,
            MAX(gs.scan_time) as last_scan
        FROM games g
        LEFT JOIN game_stats gs ON g.id = gs.game_id
        WHERE g.is_archived = 0
        GROUP BY g.id
        ORDER BY g.name
    ''')
    games = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(games)

@app.route('/api/games/tier/<int:tier>', methods=['GET'])
def get_games_by_tier(tier):
    """Get games for a specific tier."""
    games = database.get_games_by_tier(tier)
    return jsonify(games)

@app.route('/api/games/trending', methods=['GET'])
def get_trending():
    """Get trending games (rising player count)."""
    days = request.args.get('days', 7, type=int)
    games = database.get_trending_games(days)
    return jsonify(games)

@app.route('/api/archived', methods=['GET'])
def get_archived():
    """Get all archived games."""
    games = database.get_archived_games()
    return jsonify(games)

@app.route('/api/games/<int:game_id>/archive', methods=['POST'])
def archive_game(game_id):
    """Archive a game."""
    database.archive_game(game_id)
    return jsonify({"status": "archived"})

@app.route('/api/games/archive/bulk', methods=['POST'])
def archive_bulk():
    """Bulk archive games."""
    data = request.get_json()
    game_ids = data.get('game_ids', [])
    if game_ids:
        database.archive_games_bulk(game_ids)
    return jsonify({"status": "archived", "count": len(game_ids)})

@app.route('/api/games/<int:game_id>/unarchive', methods=['POST'])
def unarchive_game(game_id):
    """Unarchive a game."""
    database.unarchive_game(game_id)
    return jsonify({"status": "unarchived"})

@app.route('/api/games/delete/bulk', methods=['POST'])
def delete_bulk():
    """Bulk delete archived games."""
    data = request.get_json()
    game_ids = data.get('game_ids', [])
    if game_ids:
        database.delete_games_bulk(game_ids)
    return jsonify({"status": "deleted", "count": len(game_ids)})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get overall statistics."""
    stats = database.get_stats()
    return jsonify(stats)

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "version": "2.0"})

# ─────────────────────────────────────────────────────
# SERVE REACT UI
# ─────────────────────────────────────────────────────

@app.route('/')
def serve_ui():
    """Serve the React UI."""
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files."""
    if os.path.exists(path):
        return send_from_directory('.', path)
    return send_from_directory('.', 'index.html')

# ─────────────────────────────────────────────────────
# ERROR HANDLERS
# ─────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Server error"}), 500

if __name__ == '__main__':
    print("🚀 Starting Roblox Gem Finder Web Server...")
    print("📊 Open http://localhost:5000 in your browser")
    app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
