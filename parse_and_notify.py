import os
import re
import json
import hashlib
import requests

# Target raw markdown URL for Simplify Jobs Summer 2027 repository
TARGET_README_URL = "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/README.md"
STATE_FILE = "seen_jobs.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def get_job_hash(company, role, location, link):
    """Generate a unique ID for each listing to track duplicate postings."""
    raw_id = f"{company.strip().lower()}|{role.strip().lower()}|{location.strip().lower()}|{link.strip()}"
    return hashlib.md5(raw_id.encode('utf-8')).hexdigest()

def clean_markdown_link(text):
    """Extract clean text and URL from markdown link syntax [Text](URL)."""
    match = re.search(r'\[(.*?)\]\((.*?)\)', text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return text.strip(), ""

def fetch_and_parse_jobs():
    response = requests.get(TARGET_README_URL)
    if response.status_code != 200:
        # Fallback to main branch or Off-Season if dev/README isn't accessible
        fallback_url = "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/main/README.md"
        response = requests.get(fallback_url)
    
    lines = response.text.splitlines()
    jobs = []
    
    # Locate the table entries (Markdown lines starting with '|')
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
        
        company_name, company_url = clean_markdown_link(company_raw)
        role_title, role_url = clean_markdown_link(role_raw)
        _, app_url = clean_markdown_link(application_raw)
        
        target_link = app_url if app_url else role_url
        if not target_link:
            continue
            
        job_id = get_job_hash(company_name, role_title, location, target_link)
        
        jobs.append({
            "id": job_id,
            "company": company_name,
            "role": role_title,
            "location": location if location else "Unknown / Remote",
            "link": target_link
        })
        
    return jobs

def send_discord_notification(job):
    """Post formatted Discord Embed card."""
    embed = {
        "title": f"💼 New Internship Opening: {job['company']}",
        "color": 3447003,  # Vibrant Blue
        "fields": [
            {"name": "Role", "value": job['role'], "inline": True},
            {"name": "Location", "value": job['location'], "inline": True},
            {"name": "Application Link", "value": f"[Apply Here]({job['link']})", "inline": False}
        ],
        "footer": {
            "text": "SimplifyJobs Summer 2027 Tracker"
        }
    }
    
    payload = {
        "username": "Simplify Job Alerts",
        "avatar_url": "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png",
        "embeds": [embed]
    }
    
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def main():
    if not DISCORD_WEBHOOK_URL:
        print("Error: DISCORD_WEBHOOK_URL environment variable is missing.")
        return

    # Load existing state
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

    # Process and notify for new listings
    for job in reversed(new_jobs):  # Post older new jobs first to preserve order
        send_discord_notification(job)
        seen_ids.add(job['id'])

    # Save state back to file
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen_ids), f, indent=2)

if __name__ == "__main__":
    main()
