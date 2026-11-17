"""Job recommendations: decide the ORDER of job cards on a seeker's Homepage.

Every candidate job gets a score from three parts, and the highest scores are
shown first:

1. Profile fit (what the seeker set on their Profile)
   - words shared with the preferred job title         up to +3.0
   - job type / schedule matches the preference         +1.0 / +0.5
   - pay vs. the minimum (only matters with "Show all", because the normal
     feed already hides jobs under the minimum)          +0.5 / -2.0

2. Learned taste (what the seeker swiped on before)
   Each past swipe teaches weights for simple "features" of that job:
   title words, company, job type, schedule, pay range and city.
   Right swipe = +1 to each feature, left swipe = -0.6.
   Newer swipes count more (each older swipe is worth 5% less).
   A new job's learned score = sum of the weights of its features,
   scaled down by sqrt(number of swipes) so it never drowns out the profile.

3. Freshness: jobs posted in the last 7 days get +0.3.

Small and explainable on purpose: every card shows "why" (the top reasons).
"""
import math
import re
from collections import Counter
from datetime import datetime, timedelta

HISTORY_LIMIT = 200
STOP_WORDS = {"and", "the", "of", "for", "to", "in", "with", "new", "grad", "senior", "junior", "associate", "i", "ii"}
# How much each kind of feature matters in the learned score.
FEATURE_WEIGHT = {"w": 1.0, "co": 0.6, "type": 0.4, "sched": 0.3, "pay": 0.4, "loc": 0.3}
LIKE, PASS, DECAY = 1.0, -0.6, 0.95


def title_words(title):
    return {w for w in re.findall(r"[a-z0-9+#]+", (title or "").lower()) if len(w) > 1 and w not in STOP_WORDS}


def annual_pay(job):
    return job["pay_max"] * 2080 if job["pay_period"] == "hour" else job["pay_max"]


def pay_band(job):
    pay = annual_pay(job)
    return "<40k" if pay < 40000 else "40-70k" if pay < 70000 else "70-100k" if pay < 100000 else "100k+"


def features(job):
    city = (job.get("location") or "").split(",")[0].strip().lower()
    f = {f"w:{w}" for w in title_words(job["title"])}
    f |= {f"co:{job['company_id']}", f"type:{job['job_type']}", f"sched:{job['schedule']}", f"pay:{pay_band(job)}"}
    if city:
        f.add(f"loc:{city}")
    return f


def learn(history):
    """history = past swipes, newest first, each a job row plus 'liked'. Returns feature weights."""
    weights = Counter()
    for i, job in enumerate(history):
        amount = (LIKE if job["liked"] else PASS) * (DECAY ** i)
        for feat in features(job):
            weights[feat] += amount
    return weights


def score_job(job, profile, weights, n_history, now):
    reasons = []  # (points, text)
    score = 0.0

    if profile:
        wanted = title_words(profile.get("preferred_title"))
        if wanted:
            overlap = len(wanted & title_words(job["title"])) / len(wanted)
            if overlap:
                score += 3.0 * overlap
                reasons.append((3.0 * overlap, "Matches your preferred title"))
        if profile.get("job_type") not in (None, "any") and job["job_type"] == profile["job_type"]:
            score += 1.0
            reasons.append((1.0, f"{job['job_type'].replace('_', ' ').capitalize()}, like you asked"))
        if profile.get("schedule") not in (None, "any") and job["schedule"] == profile["schedule"]:
            score += 0.5
        minimum = profile.get("min_compensation")
        if minimum:
            if annual_pay(job) >= minimum:
                score += 0.5
                reasons.append((0.5, "Pays above your minimum"))
            else:
                score -= 2.0

    if n_history:
        learned = sum(weights.get(f, 0) * FEATURE_WEIGHT[f.split(":")[0]] for f in features(job))
        learned /= math.sqrt(n_history)
        score += learned
        if learned > 0.4:
            reasons.append((learned, "Similar to jobs you liked"))
        elif learned < -0.4:
            reasons.append((learned, "Less like what you usually pick"))

    created = job.get("created_at")
    if created and now - created < timedelta(days=7):
        score += 0.3
        reasons.append((0.3, "Posted this week"))

    reasons.sort(key=lambda r: -abs(r[0]))
    return score, [text for pts, text in reasons if pts > 0][:2]


def rank(jobs, profile, history, limit=25):
    """Return the top `limit` jobs, best first. Adds job['score'] and job['why']."""
    weights = learn(history)
    now = datetime.utcnow()
    for job in jobs:
        job["score"], job["why"] = score_job(job, profile, weights, len(history), now)
    # Newest wins ties, so a brand-new account still gets a sensible order.
    jobs.sort(key=lambda j: (j["score"], j.get("created_at") or now, j["id"]), reverse=True)
    return jobs[:limit]
