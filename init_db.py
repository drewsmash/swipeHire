"""Create the tables and, on an empty database, load demo data.

Runs automatically when the web container starts (see Dockerfile CMD).
Safe to run again: tables use IF NOT EXISTS and seeding is skipped once any
user exists. To reseed from scratch: docker compose down -v && docker compose up -d

Every demo account uses the password in DEMO_PASSWORD (default "swipehire").
"""
import os
import sys
import time
from pathlib import Path

from werkzeug.security import generate_password_hash

import db
import fake_jobs

SCHEMA = Path(__file__).with_name("sql") / "schema.sql"

# --- Demo data -------------------------------------------------------------
# Each company gets an employer login: <key>@swipehire.test
COMPANIES = [
    ("google", "Google", "Search, cloud, Android and AI products used by billions.", "careers.google.com"),
    ("nvidia", "Nvidia", "GPUs and accelerated computing for gaming, AI and data centers.", "nvidia.com/careers"),
    ("lockheed", "Lockheed Martin", "Aerospace, defense and space systems.", "lockheedmartinjobs.com"),
    ("publix", "Publix", "Employee-owned supermarket chain across the Southeast.", "publix.jobs"),
    ("royal", "Royal Caribbean", "Cruise line headquartered at PortMiami.", "royalcaribbeangroup.com/careers"),
    ("chewy", "Chewy", "Online pet supplies with 24/7 customer care.", "careers.chewy.com"),
    ("baptist", "Baptist Health", "Not-for-profit health care system in South Florida.", "baptisthealth.net/careers"),
    ("fpl", "Florida Power & Light", "Electric utility serving more than 5 million customers.", "nexteraenergy.com/careers"),
]

# (company key, title, location, job_type, schedule, responsibilities, requirements, pay_min, pay_max, period)
JOBS = [
    ("google", "Software Engineering Intern", "Mountain View, CA", "in_person", "full_time",
     "Build and ship features on a production team.\nWrite tests and take part in code reviews.\nPresent your project at the end of the summer.",
     "Pursuing a BS in Computer Science or related field.\nExperience with Python, Java, C++ or Go.\nData structures and algorithms.",
     45, 58, "hour"),
    ("google", "Associate Product Manager", "Remote (US)", "remote", "full_time",
     "Work with engineers and designers to define product features.\nTalk to users and turn feedback into requirements.\nTrack launch metrics.",
     "Bachelor's degree, technical background preferred.\nStrong written communication.\nComfort with data and SQL.",
     115000, 145000, "year"),
    ("nvidia", "Junior Data Analyst", "Santa Clara, CA", "hybrid", "full_time",
     "Build dashboards for GPU supply chain data.\nClean and join large datasets.\nShare findings with operations teams.",
     "Degree in statistics, CS or business analytics.\nSQL and Python (pandas).\nTableau or Power BI a plus.",
     85000, 105000, "year"),
    ("nvidia", "Deep Learning Engineer (New Grad)", "Remote (US)", "remote", "full_time",
     "Train and optimize neural networks on NVIDIA hardware.\nProfile CUDA kernels.\nContribute to open-source libraries.",
     "MS or BS in CS/EE.\nPyTorch experience.\nLinear algebra and probability.",
     140000, 180000, "year"),
    ("lockheed", "Systems Engineer Associate", "Orlando, FL", "in_person", "full_time",
     "Write and trace system requirements.\nSupport integration and test events.\nDocument designs for customer reviews.",
     "BS in engineering.\nU.S. citizenship (security clearance required).\nMATLAB or Python.",
     78000, 95000, "year"),
    ("lockheed", "Cybersecurity Analyst", "Orlando, FL", "hybrid", "full_time",
     "Monitor alerts and investigate incidents.\nHarden Linux and Windows systems.\nHelp with compliance audits.",
     "Security+ or similar certification.\nNetworking fundamentals.\nU.S. citizenship.",
     82000, 104000, "year"),
    ("publix", "Customer Service Associate", "Miami, FL", "in_person", "part_time",
     "Help customers find products.\nBag groceries and keep the front end clean.\nRun a register when needed.",
     "16 or older.\nFriendly and dependable.\nWeekend availability.",
     14, 16, "hour"),
    ("royal", "Guest Services Coordinator", "Miami, FL", "in_person", "full_time",
     "Answer guest questions before and after cruises.\nResolve booking issues.\nCoordinate with ship teams.",
     "1+ year customer service experience.\nSpanish a plus.\nComfort with booking systems.",
     42000, 50000, "year"),
    ("chewy", "Customer Care Specialist", "Remote (FL)", "remote", "part_time",
     "Help pet parents by phone, chat and email.\nProcess orders, returns and pharmacy requests.\nWrite handwritten-style notes to customers.",
     "High school diploma.\nQuiet home workspace and reliable internet.\nLove of pets.",
     17, 19, "hour"),
    ("baptist", "Patient Access Representative", "Coral Gables, FL", "in_person", "full_time",
     "Register patients and verify insurance.\nSchedule appointments.\nCollect co-pays.",
     "High school diploma.\nBilingual English/Spanish preferred.\nMedical terminology a plus.",
     18, 22, "hour"),
    ("baptist", "IT Help Desk Technician", "Miami, FL", "hybrid", "full_time",
     "Resolve hardware, software and account tickets.\nImage and deploy laptops.\nDocument fixes in the knowledge base.",
     "CompTIA A+ or equivalent experience.\nWindows and Active Directory.\nGood bedside manner with users.",
     48000, 58000, "year"),
    ("fpl", "Electrical Engineering Co-op", "Juno Beach, FL", "hybrid", "full_time",
     "Support substation design projects.\nReview drawings and load studies.\nVisit field sites with senior engineers.",
     "Pursuing BS in Electrical Engineering.\nAutoCAD familiarity.\nValid driver's license.",
     25, 30, "hour"),
]

# Seekers: (key, full_name, phone, preferred_title, min_comp, job_type, commute, schedule, certifications, about)
SEEKERS = [
    ("seeker", "Alex Rivera", "(305) 555-0142", "Software Engineer", 50000, "any", 25, "full_time",
     "AWS Cloud Practitioner", "FIU senior studying Computer Science. Built a campus ride-share app."),
    ("maria", "Maria Gonzalez", "(305) 555-0177", "Data Analyst", 60000, "hybrid", 30, "full_time",
     "Google Data Analytics Certificate", "Statistics major who loves turning messy spreadsheets into answers."),
    ("jordan", "Jordan Lee", "(786) 555-0110", "Product Manager", 90000, "remote", None, "full_time",
     "", "Ran a 2,000-member student startup club. Shipped two mobile apps."),
    ("sam", "Sam Patel", "(954) 555-0133", "Software Engineering Intern", 0, "any", 50, "any",
     "Oracle Java SE", "Sophomore, competitive programmer, ICPC regional finalist."),
    ("taylor", "Taylor Brooks", "(305) 555-0199", "Cybersecurity Analyst", 70000, "any", 40, "full_time",
     "CompTIA Security+, CCNA", "Navy veteran with active Secret clearance."),
]

# (seeker key, company key, job index within that company, seeker liked, employer liked or None)
SWIPES = [
    # Alex already matched with the three companies from the paper prototype.
    ("seeker", "google", 0, 1, 1),
    ("seeker", "nvidia", 0, 1, 1),
    ("seeker", "lockheed", 0, 1, 1),
    # Other seekers liked Google jobs, so the Google employer has applicants to swipe on.
    ("maria", "google", 1, 1, None),
    ("jordan", "google", 1, 1, None),
    ("sam", "google", 0, 1, None),
    ("taylor", "google", 0, 1, None),
    ("maria", "nvidia", 0, 1, 1),
    ("taylor", "lockheed", 1, 1, 1),
]


def wait_for_db(seconds=90):
    deadline = time.time() + seconds
    while True:
        try:
            db.fetch_one("SELECT 1")
            return
        except Exception as exc:
            if time.time() > deadline:
                print(f"Database not reachable: {exc}", file=sys.stderr)
                sys.exit(1)
            time.sleep(2)


def create_tables():
    sql = SCHEMA.read_text(encoding="utf-8")
    body = "\n".join(line for line in sql.splitlines() if not line.strip().startswith("--"))
    for statement in body.split(";\n"):
        if statement.strip():
            db.execute(statement)


def seed():
    if db.fetch_one("SELECT COUNT(*) AS n FROM users")["n"]:
        print("Database already has users; skipping demo data.")
        return
    pw = generate_password_hash(os.getenv("DEMO_PASSWORD", "swipehire"))

    company_ids, job_ids = {}, {}
    for key, name, desc, site in COMPANIES:
        email = f"{key}@swipehire.test"
        uid = db.execute("INSERT INTO users (email, password_hash, role) VALUES (%s, %s, 'employer')",
                         (email, pw))
        company_ids[key] = db.execute(
            "INSERT INTO companies (user_id, name, description, contact_email, website) VALUES (%s,%s,%s,%s,%s)",
            (uid, name, desc, f"recruiting@{key}.example", site))
    for key, title, loc, jtype, sched, resp, req, lo, hi, period in JOBS:
        jid = db.execute(
            """INSERT INTO jobs (company_id, title, location, job_type, schedule, responsibilities,
                                 requirements, pay_min, pay_max, pay_period)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (company_ids[key], title, loc, jtype, sched, resp, req, lo, hi, period))
        job_ids.setdefault(key, []).append(jid)

    seeker_ids = {}
    for key, name, phone, title, comp, jtype, commute, sched, certs, about in SEEKERS:
        email = f"{key}@swipehire.test"
        uid = db.execute("INSERT INTO users (email, password_hash, role) VALUES (%s, %s, 'seeker')",
                         (email, pw))
        db.execute(
            """INSERT INTO seeker_profiles (user_id, full_name, phone, contact_email, preferred_title,
                   min_compensation, job_type, commute_miles, schedule, certifications, about)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (uid, name, phone, email, title, comp or None, jtype, commute, sched, certs, about))
        seeker_ids[key] = uid

    for s_key, c_key, idx, s_liked, e_liked in SWIPES:
        sid, jid = seeker_ids[s_key], job_ids[c_key][idx]
        db.execute("INSERT INTO seeker_swipes (seeker_id, job_id, liked) VALUES (%s,%s,%s)",
                   (sid, jid, s_liked))
        if e_liked is not None:
            db.execute("INSERT INTO employer_swipes (job_id, seeker_id, liked) VALUES (%s,%s,%s)",
                       (jid, sid, e_liked))
    print(f"Seeded {len(COMPANIES)} companies, {len(JOBS)} jobs, {len(SEEKERS)} seekers.")
    # Extra made-up listings for testing (see fake_jobs.py). Fixed seed = same jobs every reset.
    print(f"Added {fake_jobs.add_fake_jobs(60, seed=15)} fake test jobs.")


if __name__ == "__main__":
    wait_for_db()
    create_tables()
    seed()
