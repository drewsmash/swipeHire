"""Take the README screenshots (docs/screenshots/) at phone size.

Read-only: it never completes a swipe and never creates a guest account.
Needs the app running (docker compose up -d). Run from the repo root in Git Bash:

  DP=$(grep '^DEMO_PASSWORD=' .env | cut -d= -f2-)
  MSYS_NO_PATHCONV=1 docker run --rm --network swipehire_default -e DEMO_PASSWORD="$DP"     -v "$(pwd -W)/scripts:/work" -v "$(pwd -W)/docs/screenshots:/out"     mcr.microsoft.com/playwright/python:v1.49.0-noble     sh -c "pip install -q playwright==1.49.0 && python -I /work/take_screenshots.py"
"""
import os

from playwright.sync_api import sync_playwright

BASE = "http://web:8000"
OUT = "/out"
PW = os.environ["DEMO_PASSWORD"]


def login(page, email):
    page.context.clear_cookies()
    page.goto(BASE + "/login")
    page.fill("input[name=email]", email)
    page.fill("input[name=password]", PW)
    page.click("button.primary[type=submit]")
    page.wait_for_load_state("networkidle")


def shot(page, name, full=False):
    page.wait_for_timeout(400)
    page.screenshot(path=f"{OUT}/{name}.png", full_page=full)
    print("saved", name)


def drag_preview(page, name, dx):
    """Drag the top card part-way, screenshot, then drag it back so no swipe happens."""
    card = page.locator(".card").last
    box = card.bounding_box()
    if not box:
        print("no card for", name)
        return
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 3
    page.mouse.move(x, y)
    page.mouse.down()
    for i in range(1, 11):
        page.mouse.move(x + dx * i / 10, y + 6 * i / 10)
    shot(page, name)
    for i in range(9, -1, -1):
        page.mouse.move(x + dx * i / 10, y)
    page.mouse.up()


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 900}, device_scale_factor=2)
    page = ctx.new_page()

    page.goto(BASE + "/login")
    shot(page, "01-login")
    page.route("**/guest", lambda r: r.abort())  # never create a guest account
    page.goto(BASE + "/try")
    page.wait_for_timeout(1450)
    page.screenshot(path=f"{OUT}/02-try-splash.png")
    print("saved 02-try-splash")
    page.unroute("**/guest")
    ctx.clear_cookies()

    login(page, "seeker@swipehire.test")
    page.goto(BASE + "/home?all=1")
    shot(page, "03-seeker-home")
    drag_preview(page, "04-seeker-swipe-right", 120)
    page.goto(BASE + "/profile")
    page.evaluate("window.scrollTo(0, 520)"); shot(page, "05-seeker-profile")
    page.goto(BASE + "/matches")
    shot(page, "06-seeker-matches")

    login(page, "google@swipehire.test")
    page.goto(BASE + "/employer/applicants")
    shot(page, "07-employer-applicants")
    page.goto(BASE + "/employer/jobs")
    shot(page, "08-employer-jobs")
    page.goto(BASE + "/employer/matches")
    shot(page, "09-employer-matches")

    login(page, "admin@swipehire.test")
    ctx2 = b.new_context(viewport={"width": 1280, "height": 900}, device_scale_factor=1.5)
    ctx2.add_cookies(ctx.cookies())
    p2 = ctx2.new_page()
    p2.goto(BASE + "/admin")
    shot(p2, "10-admin-stats")
    b.close()
