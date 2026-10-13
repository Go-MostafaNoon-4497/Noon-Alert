import os, json, urllib.request
from playwright.sync_api import sync_playwright

URL = "https://minutes.noon.com/egypt-en/search/?f[discount_min]=80"
TOPIC = os.environ["NTFY_TOPIC"]
TEST = os.environ.get("TEST") == "1"

def notify(title, msg):
    req = urllib.request.Request(
        "https://ntfy.sh/" + TOPIC,
        data=msg.encode("utf-8"),
        headers={"Title": title, "Priority": "high"},
    )
    urllib.request.urlopen(req, timeout=30)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(locale="en-EG")
    pg.goto(URL, wait_until="networkidle", timeout=90000)
    pg.wait_for_timeout(5000)
    items = pg.eval_on_selector_all(
        'a[href*="/now-product/"]',
        "els => els.map(e => [e.href, e.innerText])",
    )
    page_title = pg.title()
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
    notify("Noon test", "products found: %d | page: %s" % (len(found), page_title))

json.dump(sorted(seen | set(found)), open("seen.json", "w"))
