import os, json, random, urllib.request
from playwright.sync_api import sync_playwright

URL = "https://minutes.noon.com/egypt-en/search/?f[discount_min]=80"
TOPIC = os.environ["NTFY_TOPIC"]
TEST = os.environ.get("TEST") == "1"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def notify(title, msg):
    req = urllib.request.Request(
        "https://ntfy.sh/" + TOPIC,
        data=msg.encode("utf-8"),
        headers={"Title": title, "Priority": "high"},
    )
    urllib.request.urlopen(req, timeout=30)


items = []
page_title = ""
body = ""
error = ""

with sync_playwright() as p:
    b = p.chromium.launch(
        args=["--disable-blink-features=AutomationControlled"]
    )
    ctx = b.new_context(
        user_agent=UA,
        locale="en-EG",
        timezone_id="Africa/Cairo",
        viewport={"width": 1366, "height": 768},
        extra_http_headers={"Accept-Language": "en-EG,en;q=0.9,ar;q=0.8"},
    )
    ctx.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    )
    pg = ctx.new_page()
    try:
        pg.goto(URL, wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(random.randint(3000, 6000))
        # حركة ماوس وسكرول بسيط زي الإنسان
        pg.mouse.move(random.randint(200, 800), random.randint(200, 500))
        for _ in range(3):
            pg.mouse.wheel(0, random.randint(300, 700))
            pg.wait_for_timeout(random.randint(800, 1800))
        pg.wait_for_selector('a[href*="/now-product/"]', timeout=15000)
    except Exception as e:
        error = str(e)[:150]
    try:
        items = pg.eval_on_selector_all(
            'a[href*="/now-product/"]',
            "els => els.map(e => [e.href, e.innerText])",
        )
        page_title = pg.title()
        body = " ".join(pg.inner_text("body").split())[:200]
    except Exception as e:
        error += " | " + str(e)[:100]
    b.close()

found = {}
for href, text in items:
    found[href] = " ".join(text.split())[:80]

try:
    seen = set(json.load(open("seen.json")))
except Exception:
    seen = set()

new = {h: t for h, t in found.items() if h not in seen}

if new:
    lines = [t + "\n" + h for h, t in list(new.items())[:10]]
    notify("Noon Minutes 80 percent off", "\n\n".join(lines))
elif TEST:
    notify(
        "Noon test",
        "products: %d | title: %s | error: %s | text: %s"
        % (len(found), page_title, error, body),
    )

json.dump(sorted(seen | set(found)), open("seen.json", "w"))
