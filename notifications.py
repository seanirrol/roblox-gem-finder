#!/usr/bin/env python3
"""
Notification system for Roblox Gem Finder.
Supports desktop notifications, sound alerts, and webhooks (Discord/Slack).
"""

import subprocess
import platform
import requests
import json

try:
    from windows_toasts import WindowsToasts, Toast
except ImportError:
    WindowsToasts = None

def send_desktop_notification(title, message):
    """Send desktop notification (cross-platform)."""
    system = platform.system()

    if system == "Windows":
        if WindowsToasts is None:
            print(f"[NOTIFICATION] {title}: {message}")
            return

        try:
            toast = Toast([title, message])
            toast.show()
        except Exception as e:
            print(f"[NOTIFICATION] {title}: {message}")

    elif system == "Darwin":  # macOS
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], check=False)

    elif system == "Linux":
        subprocess.run(
            ["notify-send", title, message],
            check=False
        )

def play_sound():
    """Play notification sound (cross-platform)."""
    system = platform.system()

    try:
        if system == "Windows":
            import winsound
            winsound.Beep(1000, 500)
        elif system == "Darwin":  # macOS
            subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
        elif system == "Linux":
            subprocess.run(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"], check=False)
    except Exception as e:
        print(f"[SOUND] Could not play sound: {e}")

def send_webhook(webhook_url, game_name, players, visits, approval, game_url):
    """Send notification to Discord/Slack webhook."""
    try:
        # Discord format
        payload = {
            "embeds": [{
                "title": f"🎮 New Gem Found: {game_name}",
                "color": 6684799,
                "fields": [
                    {"name": "👥 Players", "value": f"{players:,}", "inline": True},
                    {"name": "📊 Visits", "value": f"{visits:,}", "inline": True},
                    {"name": "👍 Approval", "value": f"{approval}%", "inline": True},
                ],
                "url": game_url
            }]
        }

        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()

    except Exception as e:
        print(f"[WEBHOOK] Error sending notification: {e}")

def notify_new_game(game_name, players, visits, approval, game_url, notify=False, sound=False, webhook_url=None):
    """Combined notification handler."""
    if notify:
        send_desktop_notification(
            "🎮 New Gem Found!",
            f"{game_name}\n{players:,} players • {visits:,} visits"
        )

    if sound:
        play_sound()

    if webhook_url:
        send_webhook(webhook_url, game_name, players, visits, approval, game_url)
