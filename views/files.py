"""Resume and profile-photo uploads.

Files live in UPLOAD_DIR (a Docker volume) under random names. They are only
served to the seeker who owns them and to employers the seeker swiped right on.
"""
import os
import secrets
from pathlib import Path

from flask import Blueprint, abort, send_from_directory

import db
from views.common import current_user

bp = Blueprint("files", __name__)

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", Path(__file__).resolve().parent.parent / "uploads"))
ALLOWED = {
    "resume": {".pdf", ".doc", ".docx"},
    "photo": {".png", ".jpg", ".jpeg", ".webp", ".gif"},
}


def save_upload(storage, kind):
    """Save an uploaded file; return (stored_name, original_name) or None if nothing was sent."""
    if not storage or not storage.filename:
        return None
    ext = Path(storage.filename).suffix.lower()
    if ext not in ALLOWED[kind]:
        raise ValueError(f"{kind.title()} must be one of: {', '.join(sorted(ALLOWED[kind]))}")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored = f"{kind}-{secrets.token_hex(12)}{ext}"
    storage.save(UPLOAD_DIR / stored)
    return stored, Path(storage.filename).name[:255]


def can_view(viewer, seeker_id):
    if viewer["role"] == "seeker":
        return viewer["id"] == seeker_id
    # Employers see files of seekers who liked one of their jobs.
    return db.fetch_one(
        """SELECT 1 FROM seeker_swipes ss JOIN jobs j ON j.id = ss.job_id
           JOIN companies c ON c.id = j.company_id
           WHERE ss.seeker_id = %s AND ss.liked = 1 AND c.user_id = %s LIMIT 1""",
        (seeker_id, viewer["id"])) is not None


@bp.get("/files/<kind>/<int:seeker_id>")
def serve(kind, seeker_id):
    viewer = current_user()
    if kind not in ALLOWED or not viewer or not can_view(viewer, seeker_id):
        abort(404)
    p = db.fetch_one("SELECT resume_file, resume_name, photo_file FROM seeker_profiles WHERE user_id = %s",
                     (seeker_id,))
    name = p and (p["resume_file"] if kind == "resume" else p["photo_file"])
    if not name:
        abort(404)
    download = p["resume_name"] if kind == "resume" else None
    return send_from_directory(UPLOAD_DIR, name, download_name=download, as_attachment=False)
