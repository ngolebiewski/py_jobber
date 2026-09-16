# PYTHON JOBBER

Gets new postings from my top companies to apply to via Greenhouse, embedded Pinpoint and more to come and adds to a SQLite database. 

## Access SQLITE

```bash
sqlite3 jobs.db
SQLite version 3.43.2 2023-10-10 13:08:14
Enter ".help" for usage hints.
sqlite> .tables
jobs
sqlite> .schema jobs
CREATE TABLE jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            title TEXT,
            link TEXT UNIQUE,
            location TEXT,
            date_seen TEXT
        );
sqlite> select * from jobs;
```

# Installation and Use Guide

# py_jobber

A small Python script that checks job boards (Greenhouse, plus a Pinpoint-based one for NYPL) for new postings that match your keywords and locations, and saves the new ones to a local SQLite database so you don't see the same listing twice.

## What it does

- Loops through a list of companies that use Greenhouse for job postings
- Pulls each company's public job list from the Greenhouse API
- Filters postings by keyword (e.g. "engineer", "python") and location (e.g. "new york", "remote")
- Saves new matches to a local SQLite database (`jobs.db`), skipping ones it's already seen
- Prints out any newly found jobs when you run it

## 1. Get the code from GitHub

Open your terminal, make and navigate to your directory and run:

```bash
git clone https://github.com/ngolebiewski/py_jobber.git
cd py_jobber
```

If you don't have `git` installed, you can also click the green "Code" button on the GitHub page and download the ZIP, then unzip it and `cd` into the folder.

## 2. Set up a virtual environment (recommended)

Still in the `py_jobber` folder:

```bash
python3 -m venv venv
source venv/bin/activate      # on Mac/Linux
venv\Scripts\activate         # on Windows
```

You'll know it worked if you see `(venv)` at the start of your terminal prompt.

## 3. Install the requirements

```bash
pip install -r requirements.txt
```

This installs `requests` and a few of its dependencies, which is all the script needs to hit the job board APIs.

## 4. Run it (this creates the SQLite database automatically)

```bash
python main.py
```
OR
```bash
python3 main.py
```

The first time you run it, the script creates `jobs.db` in the project folder and sets up a `jobs` table for you — you don't need to create the database by hand. Every time after that, it reuses the same file and only adds jobs it hasn't seen before.

## 5. Check what's in the database

You can browse the results with the built-in `sqlite3` command line tool:

```bash
sqlite3 jobs.db
```

Then, inside the SQLite prompt:

```sql
.tables               -- should show: jobs
.schema jobs           -- shows the table structure
SELECT * FROM jobs;    -- see everything that's been saved
.quit                  -- exit
```

The `jobs` table has these columns: `id`, `company`, `title`, `link`, `location`, `date_seen`.

## 6. Customize it for your own search

Open `main.py` in your editor and edit these two spots near the top of the file:

**Companies to scan** — this is a dictionary of `"greenhouse-slug": "Display Name"`. The slug is the part of the company's Greenhouse URL, e.g. for `boards.greenhouse.io/duolingo` the slug is `duolingo`.

```python
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
}
```

To find a company's slug: go to their careers page, find the link to their Greenhouse job board, and grab the last part of the URL (`boards.greenhouse.io/<slug>`).

**Keywords to match** — the script checks if any of these strings appear anywhere in a job title:

```python
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
```

There's also a `LOCATIONS` list (defaults to `["new york", "remote"]`) if you want to widen or narrow where you're searching.

Save the file, run `python main.py` again, and it'll pick up your new companies and keywords.

## Notes

- Only companies that use Greenhouse for hiring will work with `fetch_greenhouse`. NYPL uses a different system (Pinpoint) and has its own function, `fetch_nypl`, as an example of adapting the script to another job board's API.
- The script is polite about hitting the APIs — it waits 1 second between companies.
- Re-running the script is safe — it won't create duplicate rows for jobs it's already saved (matched on the job's link).
