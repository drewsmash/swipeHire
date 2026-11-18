"""Admin screens (read-only): Stats dashboard, Users (clients), Jobs.

Log in as admin@swipehire.test (created by init_db.py with DEMO_PASSWORD).
"""
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request

import db
from views import guests
from views.common import like_param, login_required

bp = Blueprint("admin", __name__, url_prefix="/admin")

MATCH_JOIN = """seeker_swipes ss JOIN employer_swipes es
                ON es.job_id = ss.job_id AND es.seeker_id = ss.seeker_id AND ss.liked = 1 AND es.liked = 1"""


def one(sql, params=()):
    row = db.fetch_one(sql, params)
    return next(iter(row.values())) or 0 if row else 0


@bp.get("")
@login_required("admin")
def stats():
    roles = {r["role"]: r["n"] for r in db.fetch_all("SELECT role, COUNT(*) AS n FROM users GROUP BY role")}
    seeker_swipes = db.fetch_one("SELECT COUNT(*) AS total, COALESCE(SUM(liked), 0) AS liked FROM seeker_swipes")
    employer_swipes = db.fetch_one("SELECT COUNT(*) AS total, COALESCE(SUM(liked), 0) AS liked FROM employer_swipes")
    matches = one(f"SELECT COUNT(*) FROM {MATCH_JOIN}")
    waiting = one("""SELECT COUNT(*) FROM seeker_swipes ss WHERE ss.liked = 1 AND NOT EXISTS
                     (SELECT 1 FROM employer_swipes es WHERE es.job_id = ss.job_id AND es.seeker_id = ss.seeker_id)""")
    kpis = {
        "seekers": roles.get("seeker", 0),
        "employers": roles.get("employer", 0),
        "open_jobs": one("SELECT COUNT(*) FROM jobs WHERE is_open = 1"),
        "all_jobs": one("SELECT COUNT(*) FROM jobs"),
        "swipes": seeker_swipes["total"] + employer_swipes["total"],
        "right_rate": round(100 * seeker_swipes["liked"] / seeker_swipes["total"]) if seeker_swipes["total"] else 0,
        "matches": matches,
        "match_rate": round(100 * matches / seeker_swipes["liked"]) if seeker_swipes["liked"] else 0,
        "waiting": waiting,
        "signups_7d": one("SELECT COUNT(*) FROM users WHERE created_at >= UTC_TIMESTAMP() - INTERVAL 7 DAY"),
        "active_7d": one("SELECT COUNT(*) FROM users WHERE last_login_at >= UTC_TIMESTAMP() - INTERVAL 7 DAY"),
    }

    # Activity for the last 14 days (UTC dates).
    rows = db.fetch_all(
        """SELECT DATE(created_at) AS d, 'swipes' AS k, COUNT(*) AS n FROM seeker_swipes
             WHERE created_at >= UTC_DATE() - INTERVAL 13 DAY GROUP BY d
           UNION ALL
           SELECT DATE(created_at), 'swipes', COUNT(*) FROM employer_swipes
             WHERE created_at >= UTC_DATE() - INTERVAL 13 DAY GROUP BY DATE(created_at)
           UNION ALL
           SELECT DATE(es.created_at), 'matches', COUNT(*) FROM """ + MATCH_JOIN + """
             WHERE es.created_at >= UTC_DATE() - INTERVAL 13 DAY GROUP BY DATE(es.created_at)
           UNION ALL
           SELECT DATE(created_at), 'signups', COUNT(*) FROM users
             WHERE created_at >= UTC_DATE() - INTERVAL 13 DAY GROUP BY DATE(created_at)""")
    today = datetime.utcnow().date()
    days = [today - timedelta(days=i) for i in range(13, -1, -1)]
    daily = {d: {"swipes": 0, "matches": 0, "signups": 0} for d in days}
    for r in rows:
        if r["d"] in daily:
            daily[r["d"]][r["k"]] += r["n"]
    peak = max([v["swipes"] for v in daily.values()] + [1])

    top_jobs = db.fetch_all(
        """SELECT j.id, j.title, c.name AS company, j.is_open,
                  SUM(ss.liked) AS interested, COUNT(*) AS seen,
                  (SELECT COUNT(*) FROM employer_swipes es WHERE es.job_id = j.id AND es.liked = 1) AS matched
           FROM seeker_swipes ss JOIN jobs j ON j.id = ss.job_id JOIN companies c ON c.id = j.company_id
           GROUP BY j.id ORDER BY interested DESC, seen DESC LIMIT 8""")
    top_companies = db.fetch_all(
        f"""SELECT c.name, COUNT(*) AS matches FROM {MATCH_JOIN}
            JOIN jobs j ON j.id = ss.job_id JOIN companies c ON c.id = j.company_id
            GROUP BY c.id ORDER BY matches DESC LIMIT 6""")
    recent = db.fetch_all(
        """(SELECT ss.created_at AS at, p.full_name AS who, IF(ss.liked, 'swiped right on', 'passed on') AS what,
                   CONCAT(j.title, ' · ', c.name) AS target, 'seeker' AS kind
            FROM seeker_swipes ss JOIN seeker_profiles p ON p.user_id = ss.seeker_id
            JOIN jobs j ON j.id = ss.job_id JOIN companies c ON c.id = j.company_id
            ORDER BY ss.created_at DESC LIMIT 12)
           UNION ALL
           (SELECT es.created_at, c.name, IF(es.liked, 'matched with', 'passed on'), p.full_name, 'employer'
            FROM employer_swipes es JOIN jobs j ON j.id = es.job_id JOIN companies c ON c.id = j.company_id
            JOIN seeker_profiles p ON p.user_id = es.seeker_id
            ORDER BY es.created_at DESC LIMIT 12)
           UNION ALL
           (SELECT u.created_at, u.email, 'signed up as', u.role, 'signup' FROM users u
            ORDER BY u.created_at DESC LIMIT 12)
           ORDER BY at DESC LIMIT 15""")
    return render_template("admin/stats.html", k=kpis, daily=daily, peak=peak, top_jobs=top_jobs,
                           top_companies=top_companies, recent=recent, now=datetime.utcnow())


@bp.get("/users")
@login_required("admin")
def users():
    q = request.args.get("q", "").strip()
    role = request.args.get("role", "")
    sql = """SELECT u.id, u.email, u.role, u.created_at, u.last_login_at,
                    COALESCE(p.full_name, c.name, '') AS name, p.preferred_title, c.id AS company_id,
                    (SELECT COUNT(*) FROM seeker_swipes s WHERE s.seeker_id = u.id) AS swipes,
                    (SELECT COUNT(*) FROM seeker_swipes s WHERE s.seeker_id = u.id AND s.liked = 1) AS likes,
                    (SELECT COUNT(*) FROM seeker_swipes ss JOIN employer_swipes es ON es.job_id = ss.job_id
                       AND es.seeker_id = ss.seeker_id AND ss.liked = 1 AND es.liked = 1
                     WHERE ss.seeker_id = u.id) AS seeker_matches,
                    (SELECT COUNT(*) FROM jobs j WHERE j.company_id = c.id) AS jobs,
                    (SELECT COUNT(*) FROM employer_swipes es JOIN jobs j ON j.id = es.job_id
                     WHERE j.company_id = c.id AND es.liked = 1) AS employer_matches
             FROM users u
             LEFT JOIN seeker_profiles p ON p.user_id = u.id
             LEFT JOIN companies c ON c.user_id = u.id
             WHERE 1 = 1"""
    params = []
    if role in ("seeker", "employer", "admin"):
        sql += " AND u.role = %s"
        params.append(role)
    elif role == "guest":
        sql += " AND u.email LIKE %s"
        params.append(f"%@{guests.GUEST_DOMAIN}")
    if q:
        sql += " AND (u.email LIKE %s OR p.full_name LIKE %s OR c.name LIKE %s OR p.preferred_title LIKE %s)"
        params += [like_param(q)] * 4
    rows = db.fetch_all(sql + " ORDER BY u.created_at DESC, u.id DESC LIMIT 300", params)
    return render_template("admin/users.html", users=rows, q=q, role=role)


@bp.get("/jobs")
@login_required("admin")
def jobs():
    q = request.args.get("q", "").strip()
    sql = """SELECT j.*, c.name AS company,
                    (SELECT COUNT(*) FROM seeker_swipes s WHERE s.job_id = j.id) AS seen,
                    (SELECT COUNT(*) FROM seeker_swipes s WHERE s.job_id = j.id AND s.liked = 1) AS interested,
                    (SELECT COUNT(*) FROM employer_swipes e WHERE e.job_id = j.id AND e.liked = 1) AS matched
             FROM jobs j JOIN companies c ON c.id = j.company_id"""
    params = []
    if q:
        sql += " WHERE j.title LIKE %s OR c.name LIKE %s OR j.location LIKE %s"
        params += [like_param(q)] * 3
    rows = db.fetch_all(sql + " ORDER BY j.created_at DESC, j.id DESC LIMIT 300", params)
    return render_template("admin/jobs.html", jobs=rows, q=q)
