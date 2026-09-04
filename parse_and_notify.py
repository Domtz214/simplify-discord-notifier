import os
import re
import json
import hashlib
import requests
from datetime import datetime, timezone

# Target URLs — Includes both primary READMEs and internal data tables
TARGET_README_URLS = [
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/README.md",
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/README-Off-Season.md",
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md",
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README-Off-Season.md"
]

STATE_FILE = "seen_jobs.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# --- DISCORD ROLE CONFIGURATION ---
ROLE_MAP = {
    "SWE": "123456789012345678",      # Replace with your actual SWE Role ID
    "Data/AI": "234567890123456789",  # Replace with your actual Data/AI Role ID
    "Quant": "345678901234567890",    # Replace with your actual Quant Role ID
    "PM": "456789012345678901",       # Replace with your actual PM Role ID
    "Hardware": "567890123456789012", # Replace with your actual Hardware Role ID
}

COLOR_MAP = {
    "SWE": 3447003,       # Blue
    "Data/AI": 10181046,  # Purple
    "Quant": 3066993,     # Green
    "PM": 15105570,       # Orange
    "Hardware": 15158332, # Red
    "General": 9807270    # Gray
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
    """Generate a unique MD5 hash for deduplication."""
    raw_id = f"{company.strip().lower()}|{role.strip().lower()}|{location.strip().lower()}|{link.strip()}"
    return hashlib.md5(raw_id.encode('utf-8')).hexdigest()

def clean_text(raw_html):
    """Strip HTML comments, sub-tags, and extra whitespace to extract clean plain text."""
    # Remove HTML comments
    text = re.sub(r'<!--.*?-->', '', raw_html, flags=re.DOTALL)
    # Remove HTML tags (like <sub>, <img>, <a>)
    text = re.sub(r'<.*?>', '', text)
    # Remove markdown link text wrapper if present
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    return text.strip()

def extract_all_links(cell_text):
    """Extract all valid HTTP/HTTPS URLs from Markdown syntax or raw HTML href tags."""
    urls = []
    # Match markdown links [Text](URL)
    md_matches = re.findall(r'\[.*?\]\((https?://[^\s\)]+)\)', cell_text)
    urls.extend(md_matches)
    
    # Match HTML href links <a href="URL">
    html_matches = re.findall(r'href=["\'](https?://[^\s"\']+)["\']', cell_text)
    urls.extend(html_matches)
    
    # Match direct raw HTTP URLs
    raw_matches = re.findall(r'(https?://[^\s\|<>\)]+)', cell_text)
    urls.extend(raw_matches)
    
    # Deduplicate while preserving order
    seen = set()
    clean_urls = []
    for u in urls:
        u_clean = u.rstrip('"\')')
        if u_clean not in seen:
            seen.add(u_clean)
            clean_urls.append(u_clean)
            
    return clean_urls

def fetch_and_parse_jobs():
    jobs = []
    
    for url in TARGET_README_URLS:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                print(f"[Debug] Skipped {url} (HTTP {response.status_code})")
                continue
            
            print(f"[Debug] Processing {url}...")
            lines = response.text.splitlines()
            parsed_count = 0
            
            for line in lines:
                line_str = line.strip()
                
                # Must be a markdown table row
                if not line_str.startswith("|"):
                    continue
                
                # Skip headers and separator lines
                lower_line = line_str.lower()
                if "---" in lower_line or "| company" in lower_line or "| ---" in lower_line:
                    continue
                
                cols = [c.strip() for c in line_str.split("|")[1:-1]]
                if len(cols) < 3:
                    continue
                
                company_clean = clean_text(cols[0])
                role_clean = clean_text(cols[1])
                location_clean = clean_text(cols[2]) if len(cols) > 2 else "Remote / Unknown"
                
                # Find all links in the current row
                all_links = extract_all_links(line_str)
                if not all_links:
                    continue
                
                # Filter out raw GitHub badge/asset links
                valid_links = [l for l in all_links if "githubassets.com" not in l and "shields.io" not in l]
                if not valid_links:
                    continue
                
                # Prefer direct external application links over Simplify job directory links
                target_link = valid_links[0]
                for l in valid_links:
                    if "simplify.jobs/p/" not in l and "github.com" not in l:
                        target_link = l
                        break
                
                category = categorize_job(role_clean)
                job_id = get_job_hash(company_clean, role_clean, location_clean, target_link)
                
                jobs.append({
                    "id": job_id,
                    "company": company_clean if company_clean else "Unknown Company",
                    "role": role_clean if role_clean else "Internship Position",
                    "location": location_clean if location_clean else "Remote / Unknown",
                    "link": target_link,
                    "category": category
                })
                parsed_count += 1
                
            print(f"[Debug] Extracted {parsed_count} jobs from {url}")
            
        except Exception as e:
            print(f"[Debug] Error processing {url}: {e}")
            
    return jobs

def send_discord_notification(job):
    """Builds and posts an Executive Card Discord Embed with targeted role pings."""
    category = job['category']
    role_id = ROLE_MAP.get(category)
    
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
            "text": "SimplifyJobs Tracker • Executive Alert",
            "icon_url": "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
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
