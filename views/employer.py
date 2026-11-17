"""Employer screens: Applicants (swipe on seekers), Jobs, Company profile, Matches.

Employers only ever see seekers who already swiped right on one of their jobs.
When the employer swipes right too, it is a match for both sides.
"""
import mysql.connector
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for

import db
from views.common import current_user, like_param, login_required, to_int, wants_json

bp = Blueprint("employer", __name__, url_prefix="/employer")


def my_company():
    return db.fetch_one("SELECT * FROM companies WHERE user_id = %s", (current_user()["id"],))


def my_job(job_id):
    job = db.fetch_one("SELECT j.* FROM jobs j JOIN companies c ON c.id = j.company_id "
                       "WHERE j.id = %s AND c.user_id = %s", (job_id, current_user()["id"]))
    if not job:
        abort(404)
    return job


@bp.get("/applicants")
@login_required("employer")
def applicants():
    company = my_company()
    q = request.args.get("q", "").strip()
    job_filter = to_int(request.args.get("job"))
    sql = """SELECT ss.job_id, j.title AS job_title, p.*
             FROM seeker_swipes ss
             JOIN jobs j ON j.id = ss.job_id
             JOIN seeker_profiles p ON p.user_id = ss.seeker_id
             WHERE j.company_id = %s AND ss.liked = 1 AND NOT EXISTS
                   (SELECT 1 FROM employer_swipes es WHERE es.job_id = ss.job_id AND es.seeker_id = ss.seeker_id)"""
    params = [company["id"]]
    if job_filter:
        sql += " AND j.id = %s"
        params.append(job_filter)
    if q:
        sql += " AND (p.full_name LIKE %s OR p.preferred_title LIKE %s OR p.certifications LIKE %s OR j.title LIKE %s)"
        params += [like_param(q)] * 4
    cards = db.fetch_all(sql + " ORDER BY ss.created_at, ss.seeker_id LIMIT 25", params)
    jobs = db.fetch_all("SELECT id, title FROM jobs WHERE company_id = %s ORDER BY title", (company["id"],))
    return render_template("employer/applicants.html", cards=cards, q=q, jobs=jobs, job_filter=job_filter,
                           company=company)


@bp.post("/jobs/<int:job_id>/applicants/<int:seeker_id>/swipe")
@login_required("employer")
def swipe(job_id, seeker_id):
    my_job(job_id)
    applied = db.fetch_one("SELECT 1 FROM seeker_swipes WHERE seeker_id = %s AND job_id = %s AND liked = 1",
                           (seeker_id, job_id))
    if not applied:
        abort(404)
    liked = 1 if request.form.get("liked") == "1" else 0
    try:
        db.execute("INSERT INTO employer_swipes (job_id, seeker_id, liked) VALUES (%s, %s, %s)",
                   (job_id, seeker_id, liked))
    except mysql.connector.IntegrityError:
        pass
    name = db.fetch_one("SELECT full_name FROM seeker_profiles WHERE user_id = %s", (seeker_id,))["full_name"]
    message = f"It's a match with {name}!" if liked else "Passed"
    if wants_json():
        return jsonify(ok=True, message=message, matched=bool(liked))
    flash(message)
    return redirect(url_for("employer.applicants"))


@bp.get("/jobs")
@login_required("employer")
def jobs():
    company = my_company()
    rows = db.fetch_all(
        """SELECT j.*,
                  (SELECT COUNT(*) FROM seeker_swipes s WHERE s.job_id = j.id AND s.liked = 1) AS interested,
                  (SELECT COUNT(*) FROM employer_swipes e WHERE e.job_id = j.id AND e.liked = 1) AS matched
           FROM jobs j WHERE j.company_id = %s ORDER BY j.is_open DESC, j.created_at DESC, j.id DESC""",
        (company["id"],))
    return render_template("employer/jobs.html", jobs=rows, company=company)


def job_values(form):
    """Validate the job form. Returns (values, error)."""
    v = {
        "title": form.get("title", "").strip()[:120],
        "location": form.get("location", "").strip()[:120],
        "job_type": form.get("job_type"),
        "schedule": form.get("schedule"),
        "responsibilities": form.get("responsibilities", "").strip(),
        "requirements": form.get("requirements", "").strip(),
        "pay_min": to_int(form.get("pay_min")),
        "pay_max": to_int(form.get("pay_max")),
        "pay_period": form.get("pay_period"),
    }
    if not v["title"] or not v["responsibilities"] or not v["requirements"]:
        return v, "Title, responsibilities and requirements are required."
    if v["job_type"] not in ("remote", "hybrid", "in_person") or v["schedule"] not in ("full_time", "part_time") \
            or v["pay_period"] not in ("year", "hour"):
        return v, "Pick a job type, schedule and pay period."
    if v["pay_min"] is None or v["pay_max"] is None or v["pay_max"] < v["pay_min"]:
        return v, "Enter a pay range where the maximum is at least the minimum."
    return v, None


@bp.route("/jobs/new", methods=["GET", "POST"])
@login_required("employer")
def job_new():
    company = my_company()
    if request.method == "POST":
        v, error = job_values(request.form)
        if error:
            flash(error)
            return render_template("employer/job_form.html", job=v, new=True)
        cols = ", ".join(v)
        db.execute(f"INSERT INTO jobs (company_id, {cols}) VALUES (%s, {', '.join(['%s'] * len(v))})",
                   (company["id"], *v.values()))
        flash("Job posted. Seekers can swipe on it now.")
        return redirect(url_for("employer.jobs"))
    blank = {"job_type": "in_person", "schedule": "full_time", "pay_period": "year"}
    return render_template("employer/job_form.html", job=blank, new=True)


@bp.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
@login_required("employer")
def job_edit(job_id):
    job = my_job(job_id)
    if request.method == "POST":
        v, error = job_values(request.form)
        if error:
            flash(error)
            return render_template("employer/job_form.html", job={**job, **v}, new=False)
        cols = ", ".join(f"{k} = %s" for k in v)
        db.execute(f"UPDATE jobs SET {cols} WHERE id = %s", (*v.values(), job_id))
        flash("Job updated.")
        return redirect(url_for("employer.jobs"))
    return render_template("employer/job_form.html", job=job, new=False)


@bp.post("/jobs/<int:job_id>/toggle")
@login_required("employer")
def job_toggle(job_id):
    job = my_job(job_id)
    db.execute("UPDATE jobs SET is_open = %s WHERE id = %s", (0 if job["is_open"] else 1, job_id))
    flash("Job closed. Seekers no longer see it." if job["is_open"] else "Job reopened.")
    return redirect(url_for("employer.jobs"))


@bp.route("/company", methods=["GET", "POST"])
@login_required("employer")
def company():
    c = my_company()
    if request.method == "POST":
        name = request.form.get("name", "").strip()[:120]
        if not name:
            flash("Company name is required.")
            return redirect(url_for("employer.company"))
        db.execute("UPDATE companies SET name = %s, description = %s, contact_email = %s, website = %s WHERE id = %s",
                   (name, request.form.get("description", "").strip(),
                    request.form.get("contact_email", "").strip()[:255],
                    request.form.get("website", "").strip()[:255], c["id"]))
        flash("Company profile saved.")
        return redirect(url_for("employer.company"))
    return render_template("employer/company.html", c=c)


@bp.get("/matches")
@login_required("employer")
def matches():
    company = my_company()
    q = request.args.get("q", "").strip()
    sql = """SELECT p.*, j.title AS job_title, j.id AS job_id, es.created_at AS matched_at
             FROM employer_swipes es
             JOIN jobs j ON j.id = es.job_id
             JOIN seeker_profiles p ON p.user_id = es.seeker_id
             WHERE j.company_id = %s AND es.liked = 1"""
    params = [company["id"]]
    if q:
        sql += " AND (p.full_name LIKE %s OR j.title LIKE %s)"
        params += [like_param(q)] * 2
    rows = db.fetch_all(sql + " ORDER BY es.created_at DESC", params)
    return render_template("employer/matches.html", matches=rows, q=q)
