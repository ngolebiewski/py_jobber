import requests
import sqlite3
from datetime import datetime
import time
from html.parser import HTMLParser
from urllib.parse import urljoin


DB_NAME = "jobs.db"

# ============================================================
# GLOBAL SWITCHES
# ============================================================

# True  = search tech jobs AND museums
# False = search tech jobs only
SEARCH_MUSEUMS = True


# ============================================================
# TECH JOBS
# ============================================================

GREENHOUSE_COMPANIES = {
    "thenewyorktimes": "The New York Times",
    "duolingo": "Duolingo",
    "zyngacareers": "Zynga",
    "discord": "Discord",
    "figma": "Figma",
    "netlify": "Netlify",
    "chartbeatinc": "Chartbeat",
    "thefarmersdog": "The Farmers Dog",
    "datadog": "Datadog",
    "tailscale": "Tailscale",
}

KEYWORDS = [
    "engineer",
    "frontend",
    "react",
    "web",
    "full stack",
    "go",
    "games",
    "game",
    "python",
    "customer success",
    "developer relations",
]

LOCATIONS = [
    "new york",
    "remote"
]


# ============================================================
# HTTP
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def get(url, **kwargs):
    """GET with common headers and timeout."""

    headers = HEADERS.copy()
    headers.update(kwargs.pop("headers", {}))

    return requests.get(
        url,
        headers=headers,
        timeout=kwargs.pop("timeout", 15),
        **kwargs
    )


# ============================================================
# HTML LINK PARSER
# ============================================================

class LinkParser(HTMLParser):
    """Small HTML parser for extracting links."""

    def __init__(self):
        super().__init__()

        self.links = []
        self.current_href = None
        self.current_text = []

    def handle_starttag(self, tag, attrs):

        if tag.lower() != "a":
            return

        attrs = dict(attrs)

        self.current_href = attrs.get("href")
        self.current_text = []

    def handle_data(self, data):

        if self.current_href is not None:
            self.current_text.append(data)

    def handle_endtag(self, tag):

        if tag.lower() != "a":
            return

        if self.current_href:

            text = " ".join(
                "".join(self.current_text).split()
            )

            self.links.append({
                "href": self.current_href,
                "text": text
            })

        self.current_href = None
        self.current_text = []


def get_links(url, **kwargs):
    """Fetch a page and return links."""

    try:

        res = get(url, **kwargs)
        res.raise_for_status()

    except Exception as e:

        print(
            f"Error fetching {url}: {e}"
        )

        return []

    parser = LinkParser()
    parser.feed(res.text)

    return parser.links


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):

    if not value:
        return ""

    return " ".join(
        str(value).split()
    ).strip()


def unique_jobs(jobs):

    seen = set()
    result = []

    for job in jobs:

        link = job.get("link")

        if not link:
            continue

        if link in seen:
            continue

        seen.add(link)
        result.append(job)

    return result


# ============================================================
# DATABASE
# ============================================================

def init_db():

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

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute(
        "SELECT 1 FROM jobs WHERE link=?",
        (link,)
    )

    exists = c.fetchone()

    conn.close()

    return exists is not None


def save_job(job):

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        INSERT OR IGNORE INTO jobs
        (company, title, link, location, date_seen)
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


def add_jobs(jobs, new_jobs):

    count = 0

    for job in jobs:

        if not job.get("link"):
            continue

        if not job_exists(job["link"]):

            save_job(job)
            new_jobs.append(job)

            count += 1

    return count


# ============================================================
# GREENHOUSE
# ============================================================

def fetch_greenhouse(
    company_slug,
    company_name
):

    url = (
        "https://boards-api.greenhouse.io/"
        f"v1/boards/{company_slug}/jobs"
    )

    try:

        res = get(url)
        res.raise_for_status()

        data = res.json()

    except Exception as e:

        print(
            f"Error fetching "
            f"{company_name}: {e}"
        )

        return []

    jobs = []

    for job in data.get("jobs", []):

        title = clean_text(
            job.get("title")
        )

        location = clean_text(
            job.get("location", {})
            .get("name")
        )

        title_lower = title.lower()
        location_lower = location.lower()

        if not any(
            keyword in title_lower
            for keyword in KEYWORDS
        ):
            continue

        if not any(
            location_name in location_lower
            for location_name in LOCATIONS
        ):
            continue

        jobs.append({
            "company": company_name,
            "title": title,
            "link": job.get(
                "absolute_url",
                ""
            ),
            "location": location
        })

    return unique_jobs(jobs)


# ============================================================
# NYPL
# ============================================================

def fetch_nypl():

    url = (
        "https://nypl.pinpointhq.com/"
        "postings.json?department_id[]=6486"
    )

    try:

        res = get(url)
        res.raise_for_status()

        data = res.json()

    except Exception as e:

        print(
            f"Error fetching NYPL: {e}"
        )

        return []

    jobs = []

    for job in data.get("data", []):

        title = clean_text(
            job.get("title")
        )

        location_obj = (
            job.get("job", {})
            .get("location", {})
        )

        city = clean_text(
            location_obj.get("city")
        )

        province = clean_text(
            location_obj.get("province")
        )

        if city and province:
            location = (
                f"{city}, {province}"
            )
        else:
            location = city or province

        link = (
            job.get("url")
            or (
                "https://nypl.pinpointhq.com"
                + job.get("path", "")
            )
        )

        jobs.append({
            "company": "NYPL",
            "title": title,
            "link": link,
            "location": location
        })

    return unique_jobs(jobs)


# ============================================================
# MUSEUMS
# ============================================================


# ------------------------------------------------------------
# Whitney
# ------------------------------------------------------------

def fetch_whitney():

    url = "https://jobs.whitney.org/"

    print(
        "  Whitney: fetching jobs..."
    )

    links = get_links(url)

    jobs = []

    for item in links:

        href = urljoin(
            url,
            item["href"]
        )

        title = clean_text(
            item["text"]
        )

        if not title:
            continue

        if (
            "jobs.whitney.org"
            not in href
        ):
            continue

        if (
            href.rstrip("/")
            == url.rstrip("/")
        ):
            continue

        jobs.append({
            "company": "Whitney Museum",
            "title": title,
            "link": href,
            "location": "New York, NY"
        })

    return unique_jobs(jobs)


# ------------------------------------------------------------
# Guggenheim / Applicant Manager
# ------------------------------------------------------------

def fetch_guggenheim():

    url = (
        "https://theapplicantmanager.com/"
        "careers?co=ny"
    )

    print(
        "  Guggenheim: "
        "fetching Applicant Manager jobs..."
    )

    links = get_links(url)

    jobs = []

    for item in links:

        href = urljoin(
            url,
            item["href"]
        )

        title = clean_text(
            item["text"]
        )

        if not title:
            continue

        # IMPORTANT:
        #
        # Current Guggenheim URLs look like:
        #
        # https://theapplicantmanager.com/jobs?
        # fs=1.0em&pos=ny699
        #
        # So do NOT require "?pos=".

        if (
            "theapplicantmanager.com/jobs"
            not in href
        ):
            continue

        if "pos=" not in href:
            continue

        jobs.append({
            "company": "Guggenheim",
            "title": title,
            "link": href,
            "location": "New York, NY"
        })

    return unique_jobs(jobs)


# ------------------------------------------------------------
# New Museum / ADP
# ------------------------------------------------------------

def fetch_new_museum():

    cid = (
        "1f6b9d4e-d9c9-4a65-9886-"
        "3ae2bc274c25"
    )

    url = (
        "https://workforcenow.adp.com/"
        "mascsr/default/careercenter/"
        "public/events/staffing/v1/"
        "job-requisitions"
    )

    params = {
        "cid": cid,
        "$skip": 0,
        "$top": 100
    }

    print(
        "  New Museum: "
        "fetching ADP jobs..."
    )

    try:

        res = get(
            url,
            params=params
        )

        res.raise_for_status()

        data = res.json()

    except Exception as e:

        print(
            f"Error fetching "
            f"New Museum: {e}"
        )

        return []

    postings = (
        data.get("jobRequisitions")
        or data.get("jobRequisitionsList")
        or data.get("data")
        or []
    )

    jobs = []

    for job in postings:

        title = clean_text(
            job.get("requisitionTitle")
            or job.get("jobTitle")
            or job.get("title")
        )

        job_id = (
            job.get("itemID")
            or job.get("itemId")
            or job.get("jobId")
            or job.get("requisitionId")
        )

        if not title or not job_id:
            continue

        link = (
            "https://workforcenow.adp.com/"
            "mascsr/default/mdf/recruitment/"
            "recruitment.html"
            f"?cid={cid}"
            "&ccId=19000101_000001"
            "&source=CC2"
            "&lang=en_US"
            "&selectedMenuKey=CurrentOpenings"
            f"&jobId={job_id}"
        )

        jobs.append({
            "company": "New Museum",
            "title": title,
            "link": link,
            "location": "New York, NY"
        })

    return unique_jobs(jobs)


# ------------------------------------------------------------
# Met / Workday
# ------------------------------------------------------------

def fetch_met():

    api_url = (
        "https://metmuseum.wd5.myworkdayjobs.com/"
        "wday/cxs/metmuseum/"
        "metmuseumcareers/jobs"
    )

    careers_url = (
        "https://metmuseum.wd5.myworkdayjobs.com/"
        "en-US/metmuseumcareers"
    )

    print(
        "  Met Museum: "
        "fetching Workday jobs..."
    )

    # Workday's public CXS API currently rejects
    # our tenant request with HTTP 400.
    #
    # Try it first, because this is the cleanest
    # method if the Met fixes/changes the endpoint.

    payloads = [
        {
            "appliedFacets": {},
            "limit": 20,
            "offset": 0,
            "searchText": ""
        },
        {
            "limit": 20,
            "offset": 0,
            "searchText": ""
        }
    ]

    data = None

    for payload in payloads:

        try:

            res = requests.post(
                api_url,
                json=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": (
                        "application/json"
                    ),
                    "User-Agent": (
                        HEADERS["User-Agent"]
                    ),
                    "Referer": careers_url,
                    "Origin": (
                        "https://metmuseum."
                        "wd5.myworkdayjobs.com"
                    )
                },
                timeout=20
            )

            print(
                f"  Met Workday response: "
                f"{res.status_code}"
            )

            if res.status_code == 200:

                data = res.json()
                break

        except Exception as e:

            print(
                f"  Workday API attempt "
                f"failed: {e}"
            )

    if data is None:

        print(
            "  Workday API unavailable; "
            "trying public Workday page..."
        )

        # The public page itself may contain
        # useful job links depending on what
        # Workday serves to requests.

        links = get_links(
            careers_url
        )

        jobs = []

        for item in links:

            href = urljoin(
                careers_url,
                item["href"]
            )

            title = clean_text(
                item["text"]
            )

            if not title:
                continue

            if (
                "metmuseum.wd5.myworkdayjobs.com"
                not in href
            ):
                continue

            if "/job/" not in href:
                continue

            jobs.append({
                "company": "Met Museum",
                "title": title,
                "link": href,
                "location": "New York, NY"
            })

        return unique_jobs(jobs)

    jobs = []

    for job in data.get(
        "jobPostings",
        []
    ):

        title = clean_text(
            job.get("title")
        )

        path = (
            job.get("externalPath")
            or job.get("externalUrl")
            or ""
        )

        location = clean_text(
            job.get("locationsText")
            or job.get("location")
            or "New York, NY"
        )

        if not title or not path:
            continue

        if path.startswith("http"):
            link = path
        else:
            link = urljoin(
                "https://metmuseum."
                "wd5.myworkdayjobs.com",
                path
            )

        jobs.append({
            "company": "Met Museum",
            "title": title,
            "link": link,
            "location": location
        })

    return unique_jobs(jobs)


# ------------------------------------------------------------
# Paylocity generic fetcher
# ------------------------------------------------------------

def fetch_paylocity(
    guid,
    museum_name
):
    """
    Fetch published jobs from Paylocity.

    Paylocity V2 returns:

        {
            "displayName": "...",
            "jobs": [
                {
                    "title": "...",
                    "applyUrl": "...",
                    "jobLocation": {
                        "city": "...",
                        "state": "..."
                    }
                }
            ]
        }
    """

    url = (
        "https://recruiting.paylocity.com/"
        f"recruiting/v2/api/feed/jobs/{guid}"
    )

    print(
        f"  {museum_name}: "
        f"fetching Paylocity jobs..."
    )

    try:

        res = requests.get(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": (
                    HEADERS["User-Agent"]
                )
            },
            timeout=20
        )

        print(
            f"  Paylocity response: "
            f"{res.status_code}"
        )

        res.raise_for_status()

        data = res.json()

    except Exception as e:

        print(
            f"Error fetching "
            f"{museum_name}: {e}"
        )

        return []

    # V2 = dictionary with "jobs".
    postings = []

    if isinstance(data, dict):

        postings = data.get(
            "jobs",
            []
        )

    elif isinstance(data, list):

        # Defensive fallback for V1-style
        # responses.
        postings = data

    jobs = []

    for job in postings:

        title = clean_text(
            job.get("title")
            or job.get("Title")
        )

        link = clean_text(
            job.get("applyUrl")
            or job.get("ApplyUrl")
            or job.get("displayUrl")
            or job.get("DisplayUrl")
        )

        # IMPORTANT:
        #
        # Paylocity V2 nests location under
        # jobLocation.
        location_obj = (
            job.get("jobLocation")
            or job.get("JobLocation")
            or {}
        )

        city = clean_text(
            location_obj.get("city")
            or location_obj.get("City")
        )

        state = clean_text(
            location_obj.get("state")
            or location_obj.get("State")
        )

        location_name = clean_text(
            location_obj.get(
                "locationDisplayName"
            )
            or location_obj.get(
                "LocationDisplayName"
            )
            or location_obj.get("name")
            or location_obj.get("Name")
        )

        if city and state:

            location = (
                f"{city}, {state}"
            )

        elif location_name:

            location = location_name

        elif city:

            location = city

        else:

            location = "New York, NY"

        if not title or not link:
            continue

        jobs.append({
            "company": museum_name,
            "title": title,
            "link": link,
            "location": location
        })

    return unique_jobs(jobs)


# ------------------------------------------------------------
# Frick Collection / Paylocity
# ------------------------------------------------------------

def fetch_frick():

    guid = (
        "aba29db6-33d4-433d-b062-"
        "02c67cda2776"
    )

    return fetch_paylocity(
        guid,
        "Frick Collection"
    )


# ------------------------------------------------------------
# Brooklyn Museum
# ------------------------------------------------------------

def fetch_brooklyn_museum():

    url = (
        "https://www.brooklynmuseum.org/"
        "about/careers"
    )

    print(
        "  Brooklyn Museum: "
        "fetching careers page..."
    )

    links = get_links(url)

    jobs = []

    for item in links:

        href = urljoin(
            url,
            item["href"]
        )

        title = clean_text(
            item["text"]
        )

        if not title:
            continue

        if "paycor" not in href.lower():
            continue

        jobs.append({
            "company": "Brooklyn Museum",
            "title": title,
            "link": href,
            "location": "Brooklyn, NY"
        })

    return unique_jobs(jobs)


# ------------------------------------------------------------
# Neue Galerie / NYFA
# ------------------------------------------------------------

def fetch_neue_galerie():

    # NYFA's current job page does not expose
    # the search results as ordinary HTML links
    # to requests.
    #
    # We therefore use known current NYFA
    # listing URLs as seeds and verify them.
    #
    # These should be replaced/extended as
    # new Neue Galerie NYFA listings appear.

    known_jobs = [
        {
            "title": (
                "Visitor Services Associate"
            ),
            "link": (
                "https://www.nyfa.org/jobs/"
                "job-info/?id="
                "e6a7efa0-9374-4a6a-a37c-"
                "e44ae9418b67"
                "&title=visitor-services-associate"
            )
        },
        {
            "title": (
                "Part-Time Visitor and "
                "Member Services Supervisor"
            ),
            "link": (
                "https://www.nyfa.org/jobs/"
                "job-info/?id="
                "03b63a3c-ace8-4f56-9aa4-"
                "561f6a3b067a"
            )
        }
    ]

    print(
        "  Neue Galerie: "
        "checking NYFA..."
    )

    jobs = []

    for item in known_jobs:

        try:

            res = get(
                item["link"]
            )

            if res.status_code != 200:
                continue

            page = res.text.lower()

            if (
                "neue galerie"
                not in page
            ):
                continue

        except Exception:
            continue

        jobs.append({
            "company": "Neue Galerie",
            "title": item["title"],
            "link": item["link"],
            "location": "New York, NY"
        })

    return unique_jobs(jobs)


# ------------------------------------------------------------
# Morgan Library & Museum / Paylocity
# ------------------------------------------------------------

def fetch_morgan():

    # DO NOT request:
    #
    # https://www.themorgan.org/
    #
    # The site is Cloudflare protected.
    #
    # Morgan's jobs are publicly available
    # through Paylocity.

    guid = (
        "1e7e9e18-1e33-4f87-a451-"
        "e89ccb2290f4"
    )

    return fetch_paylocity(
        guid,
        "Morgan Library & Museum"
    )


# ============================================================
# MUSEUM FETCHERS
# ============================================================

MUSEUM_FETCHERS = [
    fetch_whitney,
    fetch_guggenheim,
    fetch_new_museum,
    fetch_met,
    fetch_frick,
    fetch_brooklyn_museum,
    fetch_neue_galerie,
    fetch_morgan,
]


# ============================================================
# MAIN
# ============================================================

def main():

    init_db()

    new_jobs = []

    # --------------------------------------------------------
    # GREENHOUSE
    # --------------------------------------------------------

    for slug, name in GREENHOUSE_COMPANIES.items():

        print(
            f"\nChecking {name}..."
        )

        jobs = fetch_greenhouse(
            slug,
            name
        )

        added = add_jobs(
            jobs,
            new_jobs
        )

        print(
            f"  Found {len(jobs)} "
            f"matching jobs"
        )

        if added:
            print(
                f"  Added {added} new jobs"
            )

        time.sleep(1)


    # --------------------------------------------------------
    # NYPL
    # --------------------------------------------------------

    print("\nChecking NYPL...")

    nypl_jobs = fetch_nypl()

    added = add_jobs(
        nypl_jobs,
        new_jobs
    )

    print(
        f"  Found {len(nypl_jobs)} jobs"
    )

    if added:
        print(
            f"  Added {added} new jobs"
        )


    # --------------------------------------------------------
    # MUSEUMS
    # --------------------------------------------------------

    if SEARCH_MUSEUMS:

        print(
            "\n"
            + "=" * 60
        )

        print(
            "SEARCH_MUSEUMS = True"
        )

        print(
            "Checking NYC museums..."
        )

        print(
            "=" * 60
        )

        for fetcher in MUSEUM_FETCHERS:

            print(
                f"\nChecking museum: "
                f"{fetcher.__name__}..."
            )

            try:

                jobs = fetcher()

                added = add_jobs(
                    jobs,
                    new_jobs
                )

                print(
                    f"  Found {len(jobs)} jobs"
                )

                if added:
                    print(
                        f"  Added {added} new jobs"
                    )

            except Exception as e:

                print(
                    f"  ERROR in "
                    f"{fetcher.__name__}: {e}"
                )

            time.sleep(1)

    else:

        print(
            "\nMuseum search disabled "
            "(SEARCH_MUSEUMS = False)"
        )


    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    print(
        "\n"
        + "=" * 60
    )

    print(
        f"Found {len(new_jobs)} "
        f"new jobs"
    )

    print(
        "=" * 60
    )

    for job in new_jobs:

        print(
            f"{job['company']} | "
            f"{job['title']} | "
            f"{job['location']}"
        )

        print(
            job["link"]
        )

        print(
            "-" * 50
        )


if __name__ == "__main__":
    main()
