# pyrefly: ignore [missing-import]
import os
# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright
# pyrefly: ignore [missing-import]
from playwright_stealth import Stealth

os.makedirs("auth_pages", exist_ok=True)
os.makedirs("auth_analysis", exist_ok=True)

def main():
    with sync_playwright() as p:
        # 1. Launch Chrome with flags that hide automation
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars"
            ]
        )
        
        # 2. Create a context with a standard user agent and viewport
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        # 3. Create the page and inject stealth scripts BEFORE navigating
        page = context.new_page()
        Stealth().apply_stealth_sync(page)

        # 4. Navigate to the login page
        print("Navigating to Zoho...")
        page.goto("https://accounts.zoho.com/signin")

        # 5. Pause script for manual login
        input("Please login manually in the browser. Once you are fully logged in, press Enter here...")

        # 6. Save the session state
        context.storage_state(path="auth.json")
        print("Authentication state successfully saved to auth.json!")

        browser.close()

if __name__ == "__main__":
    main()