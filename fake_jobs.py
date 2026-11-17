"""Fill the database with fake job listings for testing.

Run inside the web container (works on an existing database, keeps all data):
    docker compose exec web python fake_jobs.py            # adds 60 jobs
    docker compose exec web python fake_jobs.py 200        # adds 200 jobs
    docker compose exec web python fake_jobs.py --clear    # removes all fake companies + their jobs

All companies here are made up. Each one gets an employer login
<slug>@fake.swipehire.test with the DEMO_PASSWORD, so you can also log in as
them. init_db.py calls add_fake_jobs() on first start.
"""
import os
import random
import sys

from werkzeug.security import generate_password_hash

import db

FAKE_DOMAIN = "fake.swipehire.test"

COMPANIES = [
    ("Bayfront Analytics", "Data consulting for retail and hospitality brands.", "tech business"),
    ("Coral Reef Robotics", "Underwater drones for marine research.", "tech trades design"),
    ("Sunshine State Credit Union", "Member-owned banking across South Florida.", "business service"),
    ("Palmetto Health Partners", "Network of urgent care clinics.", "health business service"),
    ("Biscayne Software Co.", "Custom web and mobile apps for small businesses.", "tech design"),
    ("Everglades Logistics", "Same-day freight and warehousing.", "service business trades"),
    ("Mango Tree Media", "Social video studio for consumer brands.", "design business"),
    ("Atlantic Grid Energy", "Solar installs and battery storage.", "trades business tech"),
    ("Little Havana Eats", "Family restaurant group with eight locations.", "service business"),
    ("Keystone Cyber", "Managed security for hospitals and schools.", "tech"),
    ("Orange Bowl Sports Co.", "Youth sports leagues and summer camps.", "education service business"),
    ("Harborview Hotels", "Boutique waterfront hotels.", "service business"),
    ("Pinecrest Learning", "After-school tutoring and test prep.", "education business"),
    ("Starfish Games", "Indie mobile game studio.", "tech design"),
    ("Magic City Motors", "Electric scooter and bike sharing.", "service tech trades"),
    ("Gulfstream Aero Services", "Aircraft maintenance and parts.", "trades business"),
    ("Brickell Legal Group", "Immigration and business law firm.", "business"),
    ("Seagrape Retail", "Beachwear and surf shops.", "service design business"),
]

# (title, category, responsibilities, requirements, pay_min, pay_max, period, schedules)
ROLES = [
    ("Junior Web Developer", "tech",
     ["Build pages in React and TypeScript", "Fix bugs reported by customers", "Write unit tests", "Join daily stand-ups"],
     ["Portfolio or GitHub with web projects", "HTML, CSS and JavaScript", "Git basics", "CS degree or bootcamp"],
     55000, 75000, "year", ["full_time"]),
    ("Mobile App Developer", "tech",
     ["Ship features in our iOS and Android apps", "Work with designers on new screens", "Monitor crash reports"],
     ["Swift, Kotlin or React Native", "One published app (school projects count)", "REST APIs"],
     70000, 95000, "year", ["full_time"]),
    ("Software Engineering Intern", "tech",
     ["Pair with a mentor on a real project", "Write code reviews", "Demo your work at the end of the term"],
     ["Currently enrolled in CS or related", "Any programming language", "Curiosity"],
     22, 32, "hour", ["full_time", "part_time"]),
    ("Data Analyst", "tech",
     ["Build weekly dashboards", "Answer business questions with SQL", "Clean messy spreadsheets"],
     ["SQL", "Excel or Google Sheets", "Tableau, Power BI or Looker a plus", "Clear writing"],
     58000, 78000, "year", ["full_time"]),
    ("IT Support Specialist", "tech",
     ["Answer help desk tickets", "Set up laptops and phones", "Reset accounts and passwords"],
     ["CompTIA A+ or similar", "Windows and macOS", "Patient with non-technical users"],
     20, 26, "hour", ["full_time", "part_time"]),
    ("QA Tester", "tech",
     ["Test new features before release", "Write clear bug reports", "Keep test checklists up to date"],
     ["Detail-oriented", "Comfortable with phones and browsers", "Automation experience a plus"],
     19, 27, "hour", ["full_time", "part_time"]),
    ("Cybersecurity Analyst", "tech",
     ["Watch security alerts", "Run phishing training", "Patch servers"],
     ["Security+ or working toward it", "Networking basics", "Linux command line"],
     68000, 90000, "year", ["full_time"]),
    ("UX/UI Designer", "design",
     ["Design app screens in Figma", "Run quick user tests", "Keep the design system tidy"],
     ["Portfolio with case studies", "Figma", "Understanding of accessibility"],
     60000, 82000, "year", ["full_time"]),
    ("Graphic Designer", "design",
     ["Create social posts and ads", "Design menus, flyers and signs", "Keep the brand consistent"],
     ["Adobe Illustrator and Photoshop", "Portfolio", "Fast turnaround"],
     20, 28, "hour", ["full_time", "part_time"]),
    ("Video Editor", "design",
     ["Edit short-form videos for TikTok and Reels", "Add captions and music", "Track what performs well"],
     ["Premiere Pro, Final Cut or CapCut", "Sense of timing and trends", "Reel of past work"],
     21, 30, "hour", ["part_time", "full_time"]),
    ("Social Media Coordinator", "business",
     ["Plan and post content calendar", "Reply to comments and DMs", "Report monthly growth"],
     ["Active on Instagram and TikTok", "Good writing", "Canva"],
     42000, 52000, "year", ["full_time", "part_time"]),
    ("Marketing Assistant", "business",
     ["Help run email campaigns", "Update the website", "Organize events and promos"],
     ["Marketing or communications student/grad", "Organized", "Bilingual a plus"],
     18, 22, "hour", ["part_time", "full_time"]),
    ("Sales Development Rep", "business",
     ["Call and email new leads", "Book demos for account executives", "Log activity in the CRM"],
     ["Confident on the phone", "Goal-driven", "Salesforce or HubSpot a plus"],
     45000, 60000, "year", ["full_time"]),
    ("Bookkeeper", "business",
     ["Enter invoices and receipts", "Reconcile bank accounts", "Prepare monthly reports"],
     ["QuickBooks", "Accounting coursework", "Attention to detail"],
     22, 28, "hour", ["part_time", "full_time"]),
    ("Office Administrator", "business",
     ["Greet visitors and answer phones", "Order supplies", "Manage calendars"],
     ["Microsoft Office or Google Workspace", "Friendly and organized", "1 year office experience"],
     38000, 46000, "year", ["full_time"]),
    ("Paralegal", "business",
     ["Draft letters and forms", "Organize case files", "Schedule client meetings"],
     ["Paralegal certificate or in progress", "Spanish preferred", "Strong writing"],
     45000, 56000, "year", ["full_time"]),
    ("Customer Support Rep", "service",
     ["Help customers by chat, email and phone", "Solve order and billing issues", "Log feedback for the product team"],
     ["Patient and friendly", "Typing 40+ wpm", "Quiet space if remote"],
     16, 20, "hour", ["full_time", "part_time"]),
    ("Barista", "service",
     ["Make espresso drinks", "Keep the cafe clean", "Handle the register"],
     ["Weekend availability", "Food handler card (we can help)", "Good energy"],
     13, 16, "hour", ["part_time"]),
    ("Line Cook", "service",
     ["Prep ingredients", "Cook to recipe on a busy line", "Follow food safety rules"],
     ["Kitchen experience preferred", "Can stand for long shifts", "Team player"],
     16, 20, "hour", ["full_time", "part_time"]),
    ("Front Desk Agent", "service",
     ["Check guests in and out", "Answer questions about the area", "Handle reservations"],
     ["Customer service experience", "Evening and weekend shifts", "Bilingual a plus"],
     16, 19, "hour", ["full_time", "part_time"]),
    ("Retail Sales Associate", "service",
     ["Help shoppers find the right fit", "Restock and organize displays", "Run the register"],
     ["Friendly", "Weekend availability", "Retail experience a plus"],
     14, 17, "hour", ["part_time"]),
    ("Delivery Driver", "service",
     ["Deliver packages on a set route", "Scan and photo each drop", "Keep the van clean"],
     ["Valid driver's license", "Clean driving record", "Can lift 50 lbs"],
     18, 22, "hour", ["full_time", "part_time"]),
    ("Warehouse Associate", "service",
     ["Pick and pack orders", "Load and unload trucks", "Count inventory"],
     ["Can lift 50 lbs", "Forklift cert a plus", "Reliable"],
     17, 20, "hour", ["full_time", "part_time"]),
    ("Medical Assistant", "health",
     ["Take vitals and patient history", "Prepare exam rooms", "Schedule follow-ups"],
     ["MA certificate", "BLS/CPR", "Bilingual English/Spanish preferred"],
     18, 23, "hour", ["full_time"]),
    ("Pharmacy Technician", "health",
     ["Fill prescriptions", "Help customers at pickup", "Process insurance claims"],
     ["Florida pharmacy tech registration", "Detail oriented", "Retail experience a plus"],
     17, 21, "hour", ["full_time", "part_time"]),
    ("Tutor", "education",
     ["Tutor students in math or reading", "Track progress", "Talk with parents"],
     ["Strong in your subject", "Patient and encouraging", "Background check"],
     20, 30, "hour", ["part_time"]),
    ("Camp Counselor", "education",
     ["Lead games and activities", "Keep kids safe", "Help with drop-off and pickup"],
     ["CPR or willing to get it", "High energy", "Summer availability"],
     14, 17, "hour", ["full_time", "part_time"]),
    ("Solar Installer", "trades",
     ["Mount panels on roofs", "Run conduit and wiring", "Clean up job sites"],
     ["Comfortable on ladders and roofs", "Driver's license", "Will train"],
     19, 26, "hour", ["full_time"]),
    ("Aircraft Mechanic Apprentice", "trades",
     ["Inspect and repair aircraft parts", "Keep maintenance logs", "Learn under certified A&P mechanics"],
     ["Enrolled in or finished A&P program", "Mechanical aptitude", "Can pass background check"],
     21, 27, "hour", ["full_time"]),
    ("Electrician Helper", "trades",
     ["Assist licensed electricians", "Pull wire and install fixtures", "Keep tools organized"],
     ["Basic hand tools", "Reliable transportation", "Interest in an apprenticeship"],
     17, 22, "hour", ["full_time"]),
]

REMOTE_OK = {"tech", "design", "business"}
CITIES = ["Miami, FL", "Doral, FL", "Coral Gables, FL", "Miami Beach, FL", "Hialeah, FL", "Fort Lauderdale, FL",
          "Kendall, FL", "Homestead, FL", "Boca Raton, FL", "Orlando, FL", "Tampa, FL"]
PERKS = ["Free parking", "Tuition reimbursement", "Flexible schedule", "Free meals on shift",
         "401(k) match", "Health, dental and vision", "Paid time off", "Employee discount"]


def slug(name):
    return "".join(c for c in name.lower() if c.isalnum())[:30]


def ensure_companies(password_hash):
    """Create any missing fake companies; return [(company_id, [industries]), ...]."""
    ids = []
    for name, desc, _cats in COMPANIES:
        email = f"{slug(name)}@{FAKE_DOMAIN}"
        row = db.fetch_one("SELECT c.id FROM companies c JOIN users u ON u.id = c.user_id WHERE u.email = %s", (email,))
        if row:
            ids.append((row["id"], _cats.split()))
            continue
        uid = db.execute("INSERT INTO users (email, password_hash, role) VALUES (%s, %s, 'employer')",
                         (email, password_hash))
        ids.append((db.execute(
            "INSERT INTO companies (user_id, name, description, contact_email, website) VALUES (%s,%s,%s,%s,%s)",
            (uid, name, desc, f"jobs@{slug(name)}.example", f"{slug(name)}.example/careers")), _cats.split()))
    return ids


def round_pay(n, period):
    return int(round(n)) if period == "hour" else int(round(n / 1000) * 1000)


def add_fake_jobs(count=60, seed=None):
    rng = random.Random(seed)
    pw = generate_password_hash(os.getenv("DEMO_PASSWORD", "swipehire"))
    company_ids = ensure_companies(pw)
    rows = []
    for _ in range(count):
        title, cat, resp, req, lo, hi, period, schedules = rng.choice(ROLES)
        level = rng.random()
        if level > 0.85 and period == "year":
            title = "Senior " + title.replace("Junior ", "")
            lo, hi = lo * 1.4, hi * 1.5
        scale = rng.uniform(0.92, 1.1)
        pay_min = round_pay(lo * scale, period)
        pay_max = max(pay_min, round_pay(hi * scale, period))
        if cat in REMOTE_OK:
            job_type = rng.choices(["remote", "hybrid", "in_person"], weights=[3, 3, 2])[0]
        else:
            job_type = "in_person"
        location = "Remote (US)" if job_type == "remote" else rng.choice(CITIES)
        # Cards only have responsibilities / requirements / pay, so a perk rides
        # along as the last responsibilities bullet.
        responsibilities = rng.sample(resp, min(len(resp), rng.randint(3, 4))) + [f"Perk: {rng.choice(PERKS)}"]
        requirements = rng.sample(req, min(len(req), rng.randint(2, 4)))
        rows.append((
            rng.choice([cid for cid, cats in company_ids if cat in cats]), title, location, job_type, rng.choice(schedules),
            "\n".join(responsibilities), "\n".join(requirements), pay_min, pay_max, period,
        ))
    db.transaction([(
        """INSERT INTO jobs (company_id, title, location, job_type, schedule, responsibilities,
                             requirements, pay_min, pay_max, pay_period) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        r) for r in rows])
    return len(rows)


def clear_fake():
    n = db.fetch_one("SELECT COUNT(*) AS n FROM users WHERE email LIKE %s", (f"%@{FAKE_DOMAIN}",))["n"]
    db.execute("DELETE FROM users WHERE email LIKE %s", (f"%@{FAKE_DOMAIN}",))  # cascades to companies/jobs/swipes
    return n


if __name__ == "__main__":
    if "--clear" in sys.argv:
        print(f"Removed {clear_fake()} fake companies and all their jobs.")
    else:
        n = int(next((a for a in sys.argv[1:] if a.isdigit()), 60))
        print(f"Added {add_fake_jobs(n)} fake jobs across {len(COMPANIES)} fake companies.")
