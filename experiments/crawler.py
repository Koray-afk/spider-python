# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright
import os
from urllib.parse import urlparse
import re # <-- 1. ADDED IMPORT

os.makedirs("pages", exist_ok=True)
os.makedirs("analysis", exist_ok=True)

with sync_playwright() as p:

    start_url = "https://www.zoho.com/in/books/"
    queue = [start_url]
    visited = set()
    max_pages = 5                  # tune as needed
    page_count = 0
    base_domain = urlparse(start_url).netloc

    browser = p.chromium.launch()

    # ✅ LINE 43 ONWARDS — the crawl loop
    while queue and page_count < max_pages:
        current_url = queue.pop(0)

        if current_url in visited:
            continue
        visited.add(current_url)

        print(f"[{page_count+1}] Crawling: {current_url}")

        try:
            page = browser.new_page()
            page.goto(current_url, wait_until="domcontentloaded", timeout=15000)

            # --- Collect same-domain links ---
            links = page.eval_on_selector_all("a", "els => els.map(el => el.href)")
            for link in links:
                parsed = urlparse(link)
                # Stay on same domain, skip anchors/mailto/tel
                if (parsed.netloc == base_domain
                        and parsed.scheme in ("http", "https")
                        and link not in visited):
                    queue.append(link)

            # --- Save screenshot, HTML, text ---
            slug = f"page-{page_count + 1}"
            page.screenshot(path=f"pages/{slug}.png", full_page=True)

            html = page.content()
            
            # --- 2. THE FIX: Inject <base> tag to fix broken CSS ---
            base_tag = f'<base href="{current_url}">'
            html = re.sub(r'(<head[^>]*>)', f'\\1\n{base_tag}', html, count=1, flags=re.IGNORECASE)
            # -------------------------------------------------------

            with open(f"pages/{slug}.html", "w", encoding="utf-8") as f:
                f.write(html)

            text = page.locator("body").inner_text()
            with open(f"pages/{slug}.txt", "w", encoding="utf-8") as f:
                f.write(text)

            # --- Store metadata for next step ---
            with open(f"pages/{slug}.meta", "w") as f:
                f.write(current_url)

            page_count += 1
            page.close()

        except Exception as e:
            print(f"  ⚠ Failed: {current_url} → {e}")
            page.close()
            continue

    browser.close()
    print(f"\n✅ Done. Crawled {page_count} pages.")