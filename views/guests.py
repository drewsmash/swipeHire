"""Throwaway guest accounts for testing.

Every click on a guest button creates a NEW account, so several testers never
share one and nobody inherits someone else's swipes:

- Guest seeker: random name and preferred title, no profile filters (sees every
  job), plus 2 starter matches and 1 pending application so Matches isn't empty.
- Guest employer: its own made-up company with 3 jobs, ~8 applicants waiting
  (taken from the demo/fake seekers) and 1 starter match.

Guest emails end in @guest.swipehire.test and have a random, never-shown
password, so the only way in is the guest button (and the browser session).
Guests older than GUEST_TTL_HOURS are deleted whenever a new guest is made;
deleting a user cascades to their profile, company, jobs and swipes.
"""
import datetime as dt
import random
import secrets

from werkzeug.security import generate_password_hash

import db
import fake_jobs

GUEST_DOMAIN = "guest.swipehire.test"
GUEST_TTL_HOURS = 24
COMPANY_WORDS = (["Sunrise", "Blue Heron", "Palm Grove", "Tidewater", "Mangrove", "Key Lime", "Coquina", "Seabreeze"],
                 ["Labs", "Studios", "Group", "Works", "Collective", "Co."])


def is_guest(user):
    return bool(user) and user["email"].endswith("@" + GUEST_DOMAIN)


def cleanup_old_guests():
    return db.execute(f"DELETE FROM users WHERE email LIKE %s AND created_at < UTC_TIMESTAMP() - INTERVAL {GUEST_TTL_HOURS} HOUR",
                      (f"%@{GUEST_DOMAIN}",))


def _new_user(cur, role):
    email = f"guest-{secrets.token_hex(4)}@{GUEST_DOMAIN}"
    cur.execute("INSERT INTO users (email, password_hash, role) VALUES (%s, %s, %s)",
                (email, generate_password_hash(secrets.token_hex(16)), role))
    return cur.lastrowid


def _open_jobs(cur):
    """Open jobs that belong to real/demo/fake companies, not to other guests."""
    cur.execute("""SELECT j.id FROM jobs j JOIN companies c ON c.id = j.company_id JOIN users u ON u.id = c.user_id
                   WHERE j.is_open = 1 AND u.email NOT LIKE %s""", (f"%@{GUEST_DOMAIN}",))
    return [r[0] for r in cur.fetchall()]


def create_seeker():
    rng = random.Random()
    now = dt.datetime.utcnow()
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        uid = _new_user(cur, "seeker")
        role = rng.choice(fake_jobs.ROLES)
        first, last = rng.choice(fake_jobs.FIRST), rng.choice(fake_jobs.LAST)
        cur.execute(
            """INSERT INTO seeker_profiles (user_id, full_name, phone, contact_email, preferred_title,
                   job_type, schedule, certifications, about)
               VALUES (%s,%s,%s,%s,%s,'any','any',%s,%s)""",
            (uid, f"{first} {last} (guest)", f"(305) 555-{rng.randint(1000, 9999)}", f"{first.lower()}@example.com",
             role[0], rng.choice(fake_jobs.CERTS[role[1]]),
             "Guest test account. Change anything on this profile - it is deleted after a day."))
        jobs = _open_jobs(cur)
        for i, job_id in enumerate(rng.sample(jobs, min(3, len(jobs)))):
            liked_at = now - dt.timedelta(hours=rng.uniform(20, 40))
            cur.execute("INSERT INTO seeker_swipes (seeker_id, job_id, liked, created_at) VALUES (%s,%s,1,%s)",
                        (uid, job_id, liked_at))
            if i < 2:  # the first two are already matches; the third waits on the employer
                cur.execute("INSERT INTO employer_swipes (job_id, seeker_id, liked, created_at) VALUES (%s,%s,1,%s)",
                            (job_id, uid, liked_at + dt.timedelta(hours=rng.uniform(1, 12))))
        conn.commit()
        return uid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_employer():
    rng = random.Random()
    now = dt.datetime.utcnow()
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        uid = _new_user(cur, "employer")
        name = f"{rng.choice(COMPANY_WORDS[0])} {rng.choice(COMPANY_WORDS[1])} (guest)"
        cur.execute("INSERT INTO companies (user_id, name, description, contact_email) VALUES (%s,%s,%s,%s)",
                    (uid, name, "Guest test company. Post, edit and close jobs freely - it is deleted after a day.",
                     "hiring@example.com"))
        company_id = cur.lastrowid
        category = rng.choice(sorted({r[1] for r in fake_jobs.ROLES}))
        roles = [r for r in fake_jobs.ROLES if r[1] == category] or fake_jobs.ROLES
        job_ids = []
        for _ in range(3):
            sql, params = fake_jobs.job_insert(company_id, fake_jobs.make_job(rng, rng.choice(roles)),
                                               now - dt.timedelta(days=rng.uniform(1, 5)))
            cur.execute(sql, params)
            job_ids.append(cur.lastrowid)
        # Applicants: demo and fake seekers (never other guests) "swipe right" on these jobs.
        cur.execute("SELECT id FROM users WHERE role = 'seeker' AND email LIKE %s AND email NOT LIKE %s",
                    ("%swipehire.test", f"%@{GUEST_DOMAIN}"))
        seekers = [r[0] for r in cur.fetchall()]
        for i, seeker_id in enumerate(rng.sample(seekers, min(9, len(seekers)))):
            job_id = rng.choice(job_ids)
            liked_at = now - dt.timedelta(hours=rng.uniform(1, 48))
            cur.execute("INSERT INTO seeker_swipes (seeker_id, job_id, liked, created_at) VALUES (%s,%s,1,%s)",
                        (seeker_id, job_id, liked_at))
            if i == 0:  # one starter match so the Matches tab isn't empty
                cur.execute("INSERT INTO employer_swipes (job_id, seeker_id, liked, created_at) VALUES (%s,%s,1,%s)",
                            (job_id, seeker_id, liked_at + dt.timedelta(minutes=30)))
        conn.commit()
        return uid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
