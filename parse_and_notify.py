import os
import re
import json
import hashlib
import requests

# Target URLs (Checks both primary and off-season files)
TARGET_README_URLS = [
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/README.md",
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/README-Off-Season.md"
]

STATE_FILE = "seen_jobs.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# --- DISCORD ROLE CONFIGURATION ---
# Replace numbers with your actual Discord Role IDs (Right-click role -> Copy Role ID)
ROLE_MAP = {
    "SWE": "1545537970856140821",
    "Data/AI": "1545538128666955886",
    "Quant": "1545538199525527693",
    "PM": "1545538164268212224",
    "Hardware": "1545538181095624856",
}

# Distinct embed side-bar accent colors per category (Hex converted to integer)
COLOR_MAP = {
    "SWE": 3447003,       # Vibrant Blue
    "Data/AI": 10181046,   # Purple
    "Quant": 3066993,     # Green / Money
    "PM": 15105570,       # Orange / Product
    "Hardware": 15158332, # Red / Silicon
    "General": 9807270    # Neutral Dark Gray
}

def categorize_job(role_title):
    """Categorizes roles based on keywords in the title."""
    title_lower = role_title.lower()

    if any(k in title_lower for k in ["quant", "trader", "trading", "financial engineer"]):
        return "Quant"
    elif any(k in title_lower for k in ["data", "ai", "machine learning", "ml", "deep learning", "analytics"]):
        return "Data/AI"
    elif any(k in title_lower for k in ["product manager", "product management", "program manager", "pm"]):
        return "PM"
    elif any(k in title_lower for k in ["hardware", "silicon", "fpga", "asic", "firmware", "embedded"]):
        return "Hardware"
    elif any(k in title_lower for k in ["software", "swe", "developer", "backend", "frontend", "full stack", "fullstack", "ios", "android", "web"]):
        return "SWE"
    
    return "General"

def get_job_hash(company, role, location, link):
    """Generate a unique hash for each posting."""
    raw_id = f"{company.strip().lower()}|{role.strip().lower()}|{location.strip().lower()}|{link.strip()}"
    return hashlib.md5(raw_id.encode('utf-8')).hexdigest()

def clean_markdown_link(text):
    """Extract clean text and URL from markdown syntax [Text](URL)."""
    match = re.search(r'\[(.*?)\]\((.*?)\)', text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return text.strip(), ""

def fetch_and_parse_jobs():
    jobs = []
    
    for url in TARGET_README_URLS:
        response = requests.get(url)
        if response.status_code != 200:
            continue  # Skip quietly if file isn't available
        
        lines = response.text.splitlines()
        
        for line in lines:
            if not line.startswith("|") or "Company" in line or "---" in line:
                continue
            
            cols = [c.strip() for c in line.split("|")[1:-1]]
            if len(cols) < 4:
                continue
                
            company_raw = cols[0]
            role_raw = cols[1]
            location = cols[2]
            application_raw = cols[3]
            
            company_name, _ = clean_markdown_link(company_raw)
            role_title, role_url = clean_markdown_link(role_raw)
            _, app_url = clean_markdown_link(application_raw)
            
            target_link = app_url if app_url else role_url
            if not target_link:
                continue
                
            category = categorize_job(role_title)
            job_id = get_job_hash(company_name, role_title, location, target_link)
            
            jobs.append({
                "id": job_id,
                "company": company_name,
                "role": role_title,
                "location": location if location else "Unknown / Remote",
                "link": target_link,
                "category": category
            })
            
    return jobs

from datetime 
import datetime, timezone

def send_discord_notification(job):
    """Builds and posts an Executive Card Discord Embed with targeted role pings."""
    category = job['category']
    role_id = ROLE_MAP.get(category)
    
    # Ping specific role outside embed (Required for push notifications to trigger)
    ping_text = f"🚨 <@&{role_id}> **New {category} Internship Opening!**" if role_id else "🚨 **New Internship Opening!**"
    
    embed = {
        "title": f"🏢 {job['company']}",
        "color": COLOR_MAP.get(category, COLOR_MAP["General"]),
        "thumbnail": {
            "url": "https://raw.githubusercontent.com/SimplifyJobs/Simplify-Jobs/main/assets/icon.png"
        },
        "fields": [
            {"name": "💻 Position", "value": f"**{job['role']}**", "inline": True},
            {"name": "🏷️ Track", "value": f"`{category}`", "inline": True},
            {"name": "📍 Location", "value": job['location'], "inline": False},
            {
                "name": "⚡ Direct Link", 
                "value": f"```\n[ Click Below to Apply ]\n```\n🔗 [**Open Application Portal**]({job['link']})", 
                "inline": False
            }
        ],
        "footer": {
            "text": "SimplifyJobs Summer 2027 • Automated Tracker",
            "icon_url": "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()  # Displays local time per user in Discord
    }
    
    payload = {
        "username": "Simplify Job Alerts",
        "avatar_url": "https://raw.githubusercontent.com/SimplifyJobs/Simplify-Jobs/main/assets/icon.png",
        "content": ping_text,
        "embeds": [embed]
    }
    
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def main():
    if not DISCORD_WEBHOOK_URL:
        print("Error: DISCORD_WEBHOOK_URL environment variable is missing.")
        return

    seen_ids = set()
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                seen_ids = set(json.load(f))
        except Exception as e:
            print(f"Warning: Failed to load state file ({e}).")

    current_jobs = fetch_and_parse_jobs()
    new_jobs = [j for j in current_jobs if j['id'] not in seen_ids]
    
    print(f"Parsed {len(current_jobs)} total jobs. Found {len(new_jobs)} new listings.")

    for job in reversed(new_jobs):
        send_discord_notification(job)
        seen_ids.add(job['id'])

    with open(STATE_FILE, "w") as f:
        json.dump(list(seen_ids), f, indent=2)

if __name__ == "__main__":
    main()
