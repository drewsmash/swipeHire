# SwipeHire – project guide (for Cursor, Claude Code and teammates)

This file is the handoff doc. Cursor and Claude Code both read `AGENTS.md`
automatically, so keep it up to date when you change how things work.

## What it is

SwipeHire is "Tinder for jobs", built for **Group 15's group project** (FIU).
The design comes from `Group Project - Part 1.docx` and three paper sketches
(Homepage, Profile, Matches).

- **Job seekers** fill out one profile, then swipe on job cards
  (title, company, responsibilities, requirements, compensation).
  Swipe right / ✓ = send profile to the employer. Swipe left / ✕ = pass.
- **Employers** see applicant cards only for seekers who swiped right on one
  of their jobs. Employer swipes right = **match**. The match then shows on
  both sides' Matches screen, and contact info (phone/email/resume) unlocks.
- Mobile-first, portrait phone layout. On a desktop it renders as a
  440px-wide phone column.

## Run it (Docker – same pattern as Group-12-Project1 on this PC)

```bash
cp .env.example .env        # then change the passwords (already done on Drew's PC)
docker compose up --build -d
```

Open **http://localhost:8095**. (Port 8095 because 8000/8080/8790/3000 are used
by the other Docker sites on this machine. Change `WEB_PORT` in `.env` if needed.)

| Command | What it does |
|---|---|
| `docker compose up --build -d` | Build + start (run again after any code change) |
| `docker compose logs -f web` | Watch the Flask/gunicorn logs |
| `docker compose down` | Stop (data kept) |
| `docker compose down -v` | Stop **and wipe** the database + uploads → re-seeds demo data next start |
| `docker compose exec db mysql -u swipehire_app -p swipehire` | SQL shell (password = `DB_PASSWORD` in `.env`) |

### Demo accounts

Seeded the first time the database is empty. Password for all of them is
`DEMO_PASSWORD` from `.env` (default `swipehire`).

| Email | Role | Notes |
|---|---|---|
| `seeker@swipehire.test` | Seeker (Alex Rivera) | Already matched with Google, Nvidia, Lockheed Martin (like the sketch) |
| `maria@`, `jordan@`, `sam@`, `taylor@swipehire.test` | Seekers | Have liked Google jobs |
| `google@swipehire.test` | Employer | Has applicants waiting to be swiped |
| `nvidia@`, `lockheed@`, `publix@`, `royal@`, `chewy@`, `baptist@`, `fpl@swipehire.test` | Employers | One company each |

You can also sign up new seekers or employers from the login page.

## Stack

- **Python 3.12 + Flask 3**, served by **gunicorn** in the `web` container
- **MySQL 8.0** in the `db` container (not published to the host; only `web` can reach it)
- Plain Jinja templates + one CSS file + one vanilla JS file. No build step, no npm.
- Uploads (resumes, profile photos) live in the `uploads` Docker volume.

## File map

```
main.py              Flask app: blueprints, CSRF check, / redirect, /health
db.py                MySQL helpers: fetch_all, fetch_one, execute, transaction
init_db.py           Runs on container start: waits for MySQL, creates tables, seeds demo data (edit demo data here)
sql/schema.sql       All tables (users, seeker_profiles, companies, jobs, seeker_swipes, employer_swipes)
views/common.py      current_user(), @login_required(role), pay/label formatting, LIKE escaping
views/auth.py        /login, /signup?role=seeker|employer, /logout
views/seeker.py      /home (job swipe), /jobs/<id>/swipe, /profile, /matches
views/employer.py    /employer/applicants, /employer/jobs (+ new/edit/toggle), /employer/company, /employer/matches
views/files.py       Upload saving + /files/<resume|photo>/<seeker_id> with access check
templates/base.html  Phone shell: top bar (Menu + account icon), search slot, page title, bottom tab bar
templates/_macros.html  search bar, bullet lines, ✕/✓ swipe buttons
templates/seeker/*   home.html (card stack), profile.html, matches.html
templates/employer/* applicants.html (card stack), jobs.html, job_form.html, company.html, matches.html
static/app.js        Swipe logic: drag gesture, ✕/✓ buttons, ←/→ keys, fetch POST, toast
static/style.css     All styles; colors are CSS variables at the top (light + dark mode)
```

## How the data works

- A **swipe** is a row in `seeker_swipes(seeker_id, job_id, liked)` or
  `employer_swipes(job_id, seeker_id, liked)`. Primary keys stop double swipes.
- A **match** = `seeker_swipes.liked = 1` AND `employer_swipes.liked = 1` for the same job + seeker.
  There is no matches table; it is a JOIN (see `matches()` in both view files).
- **Homepage feed** (`views/seeker.py: home`) = open jobs the seeker hasn't swiped,
  filtered by profile: minimum compensation (hourly pay × 2080 to compare with yearly),
  job type, full/part time. "Show all" (`?all=1`) ignores the filters.
  Jobs whose title matches the preferred job title are sorted first.
- **Applicants** feed = seekers who liked one of the employer's jobs and the
  employer hasn't swiped on yet.
- **Files**: a resume/photo is visible to its owner and to employers whose job the seeker liked.

## Conventions / gotchas

- Every POST needs the CSRF token: forms include
  `<input type="hidden" name="csrf_token" value="{{ csrf_token }}">`;
  `fetch` calls send header `X-CSRF-Token` (read from `<meta name="csrf-token">`).
- Swipe endpoints return JSON when the request has `X-Requested-With: fetch`,
  otherwise they redirect (so the ✕/✓ buttons still work without JS).
- Macros that use `csrf_token` must be imported `with context`:
  `{% import "_macros.html" as ui with context %}`.
- **Schema changes:** `init_db.py` only runs `CREATE TABLE IF NOT EXISTS`, so
  changing an existing table needs either `docker compose down -v` (wipes data –
  fine for this project) or a manual `ALTER TABLE`.
- `sql/schema.sql` is split on `;` + newline – don't put semicolons inside comments.
- `.env` is git-ignored. Never commit it. `.env.example` is the template.
- Keep `.sh`/`.py`/`.sql` files with LF line endings (`.gitattributes` handles it).
- Commute distance is stored and shown to employers but not used for filtering
  yet (jobs have no coordinates).

## Ideas / TODO (not done yet)

- [ ] Real distance filter (add lat/long or ZIP to jobs and profiles)
- [ ] "Undo last swipe" button
- [ ] Messaging between matched seeker and employer
- [ ] Employer view of a job's full applicant history (liked/passed)
- [ ] Notifications/badge when a new match happens
- [ ] Password reset, email verification
- [ ] Automated tests (pytest + Flask test client) – a manual end-to-end check passed on 2026-11-17:
      login, profile save + resume upload, bad file type rejected, search, swipe both sides,
      match appears, CSRF rejects missing token, role pages blocked, signup, file access control.
- [ ] Cloudflare tunnel for sharing a public demo link (see `whalenet-web/docker-compose.yml` for the pattern)

## Team

Group 15: Chantal Silva, Andrew Whalen, Lucas Porfirio, Caleb Holness, Frank Hernandez.
