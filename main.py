import requests
import sqlite3
from datetime import datetime
import time

DB_NAME = "jobs.db"

# Companies with Greenhouse boards
GREENHOUSE_COMPANIES = {
    "thenewyorktimes": "The New York Times",
    "duolingo": "Duolingo",
    "etsy": "Etsy",
    "zyngacareers": "Zynga",
    "discord": "Discord",
    "figma": "Figma",
    "netlify": "Netlify",
}

# Keywords to filter jobs
KEYWORDS = [
    "engineer",
    "frontend",
    "react",
    "web",
    "full stack",
    "go",
    "games",
    "game",
    "python"
]

# Locations to keep
LOCATIONS = [
    "new york",
    "remote"
]


def init_db():
    """Create SQLite database and jobs table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            title TEXT,
            link TEXT UNIQUE,
            location TEXT,
            date_seen TEXT
        )
    """)

    conn.commit()
    conn.close()


def job_exists(link):
    """Check if a job already exists in the DB."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT 1 FROM jobs WHERE link=?", (link,))
    exists = c.fetchone()
    conn.close()
    return exists is not None


def save_job(job):
    """Save a new job to the DB."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        INSERT OR IGNORE INTO jobs (company, title, link, location, date_seen)
        VALUES (?, ?, ?, ?, ?)
    """, (
        job["company"],
        job["title"],
        job["link"],
        job["location"],
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def fetch_greenhouse(company_slug, company_name):
    """Fetch jobs from Greenhouse API for a given company."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs"

    try:
        res = requests.get(url, timeout=10)
        data = res.json()
    except Exception as e:
        print(f"Error fetching {company_name}: {e}")
        return []

    jobs = []

    for job in data.get("jobs", []):
        title = job["title"].lower()
        location = job["location"]["name"].lower()

        # Filter by keywords AND location
        if any(k in title for k in KEYWORDS) and any(l in location for l in LOCATIONS):
            jobs.append({
                "company": company_name,
                "title": job["title"],
                "link": job["absolute_url"],
                "location": job["location"]["name"]
            })

    return jobs

def fetch_nypl():
    url = "https://nypl.pinpointhq.com/postings.json?department_id[]=6486"

    try:
        res = requests.get(url, timeout=10)
        data = res.json()
    except Exception as e:
        print(f"Error fetching NYPL: {e}")
        return []

    jobs = []

    for job in data.get("data", []):
        title = job.get("title", "")

        location_obj = job.get("job", {}).get("location", {})
        city = location_obj.get("city", "")
        province = location_obj.get("province", "")
        location = f"{city}, {province}".strip(", ")

        jobs.append({
            "company": "NYPL",
            "title": title,
            "link": job.get("url") or f"https://nypl.pinpointhq.com{job.get('path', '')}",
            "location": location
        })

    return jobs
    

def main():
    init_db()

    new_jobs = []

    for slug, name in GREENHOUSE_COMPANIES.items():
        print(f"\nChecking {name}...")
        jobs = fetch_greenhouse(slug, name)

        for job in jobs:
            if not job_exists(job["link"]):
                save_job(job)
                new_jobs.append(job)

        time.sleep(1)  # polite delay
        
       # --- NYPL ---
    print("\nChecking NYPL...")
    nypl_jobs = fetch_nypl()

    for job in nypl_jobs:
        if not job_exists(job["link"]):
            save_job(job)
            new_jobs.append(job)

    print(f"\nFound {len(new_jobs)} new jobs\n")

    for job in new_jobs:
        print(f"{job['company']} | {job['title']} | {job['location']}")
        print(job["link"])
        print("-" * 50)


if __name__ == "__main__":
    main()
