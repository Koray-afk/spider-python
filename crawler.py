from playwright.sync_api import sync_playwright
import os

os.makedirs("pages", exist_ok=True)

with sync_playwright() as p:

    start_url = "https://google.com"
    queue = [start_url]
    visited = set()
    max_pages = 5

    print(queue)
    print(visited)

    current_url = queue.pop(0)
    print("current_url")
    print(current_url)

    visited.add(current_url)
    print("visited->", visited)
    print("queue->", queue)



    browser = p.chromium.launch()

    page = browser.new_page()

    page.goto(
        start_url,
        wait_until="domcontentloaded"
    )

    links = page.eval_on_selector_all(
    "a",
    """
    elements => elements.map(
        el => el.href
    )
    """)

    for link in links:
        if link not in visited:
            queue.append(link)

    print(len(links))

    for link in links[:5]:
        print(link)

    print("Queue After Adding Links:")
    print(queue[:5])

    print("Queue Size:")
    print(len(queue))

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
