import sqlite3


def init_db():
    conn = sqlite3.connect('jobs.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS seen_jobs (
            job_id TEXT PRIMARY KEY,
            title TEXT,
            location TEXT,
            date_found TEXT
        )
    ''')
    conn.commit()
    conn.close()


def is_new_job(job_id):
    conn = sqlite3.connect('jobs.db')
    result = conn.execute(
        'SELECT 1 FROM seen_jobs WHERE job_id=?',
        (job_id,)
    ).fetchone()
    conn.close()

    return result is None


def save_job(job_id, title, location):
    conn = sqlite3.connect('jobs.db')
    conn.execute(
        'INSERT INTO seen_jobs VALUES (?,?,?,datetime("now"))',
        (job_id, title, location)
    )
    conn.commit()
    conn.close()