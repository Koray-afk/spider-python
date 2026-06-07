from playwright.sync_api import sync_playwright
import os

os.makedirs("pages", exist_ok=True)
start_url = "https://stripe.com"
queue = [start_url]
visited = set()
max_pages = 5


with sync_playwright() as p:

    browser = p.chromium.launch()

    page = browser.new_page()

    page_number = 1

    while queue and len(visited) < max_pages:
        current_url = queue.pop(0)

        if current_url in visited:
            continue 
        
        print(f"\nVisiting: {current_url}")

        try:
            page.goto(
            current_url,
            wait_until="domcontentloaded"
            )

            visited.add(current_url)

            #now we have to take the screenshot
            page.screenshot(
                path=f"pages/page-{page_number}.png",
                full_page=True
            )

            # HTML
            html = page.content()

            with open(
                f"pages/page-{page_number}.html",
                "w",
                encoding="utf-8"
            ) as f:
                f.write(html)

            # text 
            text = page.locator("body").inner_text()

            with open(
                f"pages/page-{page_number}.txt",
                "w",
                encoding="utf-8"
            ) as f:
                f.write(text)

            
            # now we have to extract the links from the page
            links = page.eval_on_selector_all(
                "a",
                """
                elements => elements.map(
                    el => el.href
                )
                """) 
               
            # we have to add the links to the queue
            for link in links:
                if(
                    link.startswith("http")
                    and link not in visited
                ):
                    queue.append(link)
            
            print( f"Visited: {len(visited)} | Queue: {len(queue)}")

            page_number += 1
        except Exception as e:
            print(
                f"Error visiting {current_url}"
            )

            print(e)
    browser.close()

