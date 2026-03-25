# PYTHON JOBBER

Gets new postings from my top companies to apply to via Greenhouse, embedded Pinpoint and more to come and adds to a SQLite database. 

## Access SQLITE


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
