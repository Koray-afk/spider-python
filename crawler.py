from playwright.sync_api import sync_playwright
import os

os.makedirs("pages", exist_ok=True)

with sync_playwright() as p:

    browser = p.chromium.launch()

    page = browser.new_page()

    page.goto(
        "https://google.com",
        wait_until="domcontentloaded"
    )

    # Screenshot
    page.screenshot(
        path="pages/page-1.png",
        full_page=True
    )

    # HTML
    html = page.content()

    with open(
        "pages/page-1.html",
        "w",
        encoding="utf-8"
    ) as f:
        f.write(html)

    # Visible Text
    text = page.locator("body").inner_text()

    with open(
        "pages/page-1.txt",
        "w",
        encoding="utf-8"
    ) as f:
        f.write(text)

    browser.close()