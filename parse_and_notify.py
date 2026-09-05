import os
import re
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

TARGET_README_URLS = [
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/README.md",
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/README-Off-Season.md",
]

STATE_FILE = "seen_jobs.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# --- DISCORD ROLE CONFIGURATION ---
ROLE_MAP = {
    "SWE": "1545537970856140821",
    "Data/AI": "1545538128666955886",
    "Quant": "1545538199525527693",
    "PM": "1545538164268212224",
    "Hardware": "1545538181095624856",
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
    title_lower = role_title.lower()

    if any(k in title_lower for k in ["quant", "trader", "trading", "financial engineer", "quantitative"]):
        return "Quant"
    elif any(k in title_lower for k in ["data engineer", "ai", "machine learning", "ml", "deep learning", "analytics", "data analytics", "ai engineer", "data science", "data scientist"]):
        return "Data/AI"
    elif any(k in title_lower for k in ["product manager", "product management", "program manager", "pm"]):
        return "PM"
    elif any(k in title_lower for k in ["hardware", "silicon", "fpga", "asic", "firmware", "embedded", "digital signal", "electrical engineer", "chip", "microcontroller"]):
        return "Hardware"
    elif any(k in title_lower for k in ["software", "swe", "developer", "backend", "frontend", "full stack", "fullstack", "ios", "android", "web"]):
        return "SWE"
    
    return "General"

def get_job_hash(company, role, location, link):
    raw_id = f"{company.strip().lower()}|{role.strip().lower()}|{location.strip().lower()}|{link.strip()}"
    return hashlib.md5(raw_id.encode('utf-8')).hexdigest()

def clean_text(text):
    """Strip unnecessary whitespace and non-breaking spaces."""
    return re.sub(r'\s+', ' ', text).strip()

def fetch_and_parse_jobs():
    jobs = []
    
    for url in TARGET_README_URLS:
        try:
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                print(f"[Debug] Skipped {url} (HTTP {response.status_code})")
                continue
            
            print(f"[Debug] Parsing HTML content from {url}...")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Locate all tables in the document
            tables = soup.find_all('table')
            parsed_count = 0
            
            for table in tables:
                rows = table.find_all('tr')
                last_company = "Unknown Company"
                
                for row in rows:
                    cols = row.find_all('td')
                    if not cols or len(cols) < 4:
                        continue  # Skip table header (th) rows
                    
                    # 1. Company Column Extraction
                    company_col = cols[0]
                    company_raw = clean_text(company_col.get_text())
                    
                    if "↳" in company_raw or not company_raw:
                        company_name = last_company
                    else:
                        company_name = company_raw.replace("🔥", "").strip()
                        last_company = company_name

                    # 2. Role Title Extraction
                    role_title = clean_text(cols[1].get_text())

                    # 3. Location Extraction (Handles multi-location dropdowns)
                    location_col = cols[2]
                    summary_tag = location_col.find('summary')
                    if summary_tag:
                        # Extract dropdown label e.g., "7 locations"
                        location = clean_text(summary_tag.get_text())
                    else:
                        location = clean_text(location_col.get_text())
                    
                    if not location:
                        location = "Remote / Unknown"

                    # 4. Application Link Extraction
                    app_col = cols[3]
                    target_link = ""
                    
                    # Look for explicit Apply button image
                    apply_img = app_col.find('img', alt=re.compile(r'Apply', re.I))
                    if apply_img and apply_img.parent and apply_img.parent.name == 'a':
                        target_link = apply_img.parent.get('href', '')
                    else:
                        # Fallback to any external link inside the cell
                        all_anchors = app_col.find_all('a', href=True)
                        for a in all_anchors:
                            href = a['href']
                            if "simplify.jobs/p/" not in href and href.startswith("http"):
                                target_link = href
                                break
                            elif not target_link and href.startswith("http"):
                                target_link = href

                    if not target_link:
                        continue

                    category = categorize_job(role_title)
                    job_id = get_job_hash(company_name, role_title, location, target_link)

                    jobs.append({
                        "id": job_id,
                        "company": company_name,
                        "role": role_title,
                        "location": location,
                        "link": target_link,
                        "category": category
                    })
                    parsed_count += 1

            print(f"[Debug] Extracted {parsed_count} jobs from {url}")

        except Exception as e:
            print(f"[Debug] Error processing {url}: {e}")

    return jobs

def send_discord_notification(job):
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
