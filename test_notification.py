"""
Standalone test script — sends ONE sample notification to Discord
using the current embed template, so you can preview the look
without waiting for a real new listing.

Run locally:
    DISCORD_WEBHOOK_URL="your_webhook_url_here" python test_notification.py

Or run it as a one-off in GitHub Actions via workflow_dispatch,
same as your main script (it reads the same DISCORD_WEBHOOK_URL secret).
"""

import os
import requests
from datetime import datetime, timezone

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

COLOR_MAP = {
    "SWE": 3447003,       # Blue
    "Data/AI": 10181046,  # Purple
    "Quant": 3066993,     # Green
    "PM": 15105570,       # Orange
    "Hardware": 15158332, # Red
    "General": 9807270    # Gray
}

# Change ROLE_MAP + role_id below if you want to test the @role ping too.
# Leaving it as None sends the message with no ping, which is usually what
# you want for a preview (so it doesn't actually notify your members).
role_id = None

# --- Sample/placeholder job — nothing here is real ---
job = {
    "company": "Sample Company Inc.",
    "role": "Software Engineering Intern - Test Preview",
    "location": "Remote / Multiple Locations",
    "link": "https://example.com",
    "category": "SWE",
}


def send_test_notification(job):
    category = job["category"]

    ping_text = f"<@&{role_id}>" if role_id else ""

    embed = {
        "author": {
            "name": "New Internship Posted",
            "icon_url": "https://raw.githubusercontent.com/SimplifyJobs/Simplify-Jobs/main/assets/icon.png"
        },
        "title": job["role"],
        "url": job["link"],
        "description": f"**{job['company']}**\n[Apply now →]({job['link']})",
        "color": COLOR_MAP.get(category, COLOR_MAP["General"]),
        "thumbnail": {
            "url": "https://raw.githubusercontent.com/SimplifyJobs/Simplify-Jobs/main/assets/icon.png"
        },
        "fields": [
            {"name": "📍 Location", "value": job["location"], "inline": True},
            {"name": "🏷️ Track", "value": category, "inline": True},
        ],
        "footer": {
            "text": "Simplify Jobs Tracker · TEST PREVIEW"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    payload = {
        "username": "Simplify Job Alerts",
        "avatar_url": "https://raw.githubusercontent.com/SimplifyJobs/Simplify-Jobs/main/assets/icon.png",
        "content": ping_text,
        "embeds": [embed]
    }

    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    print(f"Discord responded with status {response.status_code}")
    if response.status_code >= 300:
        print(response.text)


if __name__ == "__main__":
    if not DISCORD_WEBHOOK_URL:
        print("Error: DISCORD_WEBHOOK_URL environment variable is missing.")
    else:
        send_test_notification(job)
        print("Test notification sent — check your Discord channel.")
