"""Job seeker screens: Homepage (swipe on jobs), Profile and Matches."""
import mysql.connector
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for

import db
from views import recommend
from views.common import current_user, like_param, login_required, to_int, wants_json
from views.files import save_upload

bp = Blueprint("seeker", __name__)

# Hourly pay is compared with yearly minimums as 40 h x 52 weeks.
ANNUAL_MAX = "(CASE j.pay_period WHEN 'hour' THEN j.pay_max * 2080 ELSE j.pay_max END)"


def load_profile(user_id):
    return db.fetch_one("SELECT * FROM seeker_profiles WHERE user_id = %s", (user_id,))


@bp.get("/home")
@login_required("seeker")
def home():
    me = current_user()
    profile = load_profile(me["id"])
    q = request.args.get("q", "").strip()
    show_all = request.args.get("all") == "1"

    where = ["j.is_open = 1",
             "NOT EXISTS (SELECT 1 FROM seeker_swipes s WHERE s.seeker_id = %s AND s.job_id = j.id)"]
    params = [me["id"]]
    if q:
        where.append("(j.title LIKE %s OR c.name LIKE %s OR j.responsibilities LIKE %s "
                     "OR j.requirements LIKE %s OR j.location LIKE %s)")
        params += [like_param(q)] * 5

    # Profile filters: these settings decide which jobs the seeker sees.
    filters = []
    if profile and not show_all:
        if profile["min_compensation"]:
            where.append(f"{ANNUAL_MAX} >= %s")
            params.append(profile["min_compensation"])
            filters.append(f"${profile['min_compensation']:,}+ / yr")
        if profile["job_type"] != "any":
            where.append("j.job_type = %s")
            params.append(profile["job_type"])
            filters.append(profile["job_type"])
        if profile["schedule"] != "any":
            where.append("j.schedule = %s")
            params.append(profile["schedule"])
            filters.append(profile["schedule"])

    candidates = db.fetch_all(
        f"""SELECT j.*, c.name AS company
            FROM jobs j JOIN companies c ON c.id = j.company_id
            WHERE {' AND '.join(where)}
            ORDER BY j.created_at DESC LIMIT 1000""",
        params)
    # Past swipes, newest first, teach the recommender what this seeker likes.
    history = db.fetch_all(
        """SELECT j.*, s.liked FROM seeker_swipes s JOIN jobs j ON j.id = s.job_id
           WHERE s.seeker_id = %s ORDER BY s.created_at DESC LIMIT %s""",
        (me["id"], recommend.HISTORY_LIMIT))
    jobs = recommend.rank(candidates, profile, history)
    return render_template("seeker/home.html", jobs=jobs, q=q, filters=filters, show_all=show_all,
                           learned_from=len(history))


@bp.post("/jobs/<int:job_id>/swipe")
@login_required("seeker")
def swipe(job_id):
    me = current_user()
    liked = 1 if request.form.get("liked") == "1" else 0
    job = db.fetch_one("SELECT j.id, c.name AS company FROM jobs j JOIN companies c ON c.id = j.company_id "
                       "WHERE j.id = %s AND j.is_open = 1", (job_id,))
    if not job:
        abort(404)
    try:
        db.execute("INSERT INTO seeker_swipes (seeker_id, job_id, liked) VALUES (%s, %s, %s)",
                   (me["id"], job_id, liked))
    except mysql.connector.IntegrityError:
        pass  # already swiped (double click / two tabs) - keep the first answer
    message = f"Profile sent to {job['company']}" if liked else "Passed"
    if wants_json():
        return jsonify(ok=True, message=message)
    flash(message)
    return redirect(url_for("seeker.home", q=request.args.get("q", "")))


@bp.route("/profile", methods=["GET", "POST"])
@login_required("seeker")
def profile():
    me = current_user()
    prof = load_profile(me["id"])
    if request.method == "POST":
        f = request.form
        job_type = f.get("job_type") if f.get("job_type") in ("any", "remote", "hybrid", "in_person") else "any"
        schedule = f.get("schedule") if f.get("schedule") in ("any", "full_time", "part_time") else "any"
        values = {
            "full_name": f.get("full_name", "").strip()[:120],
            "phone": f.get("phone", "").strip()[:40],
            "contact_email": f.get("contact_email", "").strip()[:255],
            "preferred_title": f.get("preferred_title", "").strip()[:120],
            "min_compensation": to_int(f.get("min_compensation")),
            "job_type": job_type,
            "commute_miles": to_int(f.get("commute_miles"), 0, 500),
            "schedule": schedule,
            "certifications": f.get("certifications", "").strip(),
            "about": f.get("about", "").strip(),
        }
        try:
            resume = save_upload(request.files.get("resume"), "resume")
            photo = save_upload(request.files.get("photo"), "photo")
        except ValueError as exc:
            flash(str(exc))
            return render_template("seeker/profile.html", p={**prof, **values})
        if resume:
            values["resume_file"], values["resume_name"] = resume
        if photo:
            values["photo_file"] = photo[0]
        cols = ", ".join(f"{k} = %s" for k in values)
        db.execute(f"UPDATE seeker_profiles SET {cols} WHERE user_id = %s", (*values.values(), me["id"]))
        flash("Profile saved.")
        return redirect(url_for("seeker.profile"))
    return render_template("seeker/profile.html", p=prof)


@bp.get("/matches")
@login_required("seeker")
def matches():
    me = current_user()
    q = request.args.get("q", "").strip()
    sql = """SELECT j.*, c.name AS company, c.contact_email AS company_email, c.website,
                    es.created_at AS matched_at
             FROM seeker_swipes ss
             JOIN employer_swipes es ON es.job_id = ss.job_id AND es.seeker_id = ss.seeker_id AND es.liked = 1
             JOIN jobs j ON j.id = ss.job_id
             JOIN companies c ON c.id = j.company_id
             WHERE ss.seeker_id = %s AND ss.liked = 1"""
    params = [me["id"]]
    if q:
        sql += " AND (c.name LIKE %s OR j.title LIKE %s)"
        params += [like_param(q)] * 2
    rows = db.fetch_all(sql + " ORDER BY es.created_at DESC", params)
    pending = db.fetch_one(
        """SELECT COUNT(*) AS n FROM seeker_swipes ss
           WHERE ss.seeker_id = %s AND ss.liked = 1 AND NOT EXISTS
                 (SELECT 1 FROM employer_swipes es WHERE es.job_id = ss.job_id AND es.seeker_id = ss.seeker_id)""",
        (me["id"],))["n"]
    return render_template("seeker/matches.html", matches=rows, q=q, pending=pending)
