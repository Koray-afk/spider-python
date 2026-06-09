# pyrefly: ignore [missing-import]
import os
import time
import subprocess
from pathlib import Path
import json
# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright, Playwright
# pyrefly: ignore [missing-import]
from playwright_stealth import Stealth

AUTH_FILE = "auth.json"

# Standard path for Google Chrome on macOS
CHROME_MAC_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEBUG_PORT = 9222
USER_DATA_DIR = "/tmp/chrome_dev_profile"

def setup_environment():
    os.makedirs("auth_pages", exist_ok=True)
    os.makedirs("auth_analysis", exist_ok=True)

def launch_real_chrome():
    """Launches the actual OS-installed Chrome browser with debugging enabled."""
    print("[*] Launching real Google Chrome for secure login...")
    cmd = [
        CHROME_MAC_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={USER_DATA_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized"
    ]
    # Launch Chrome as a separate process
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def ensure_authenticated(p: Playwright, auth_file: str = AUTH_FILE) -> str:
    if Path(auth_file).exists():
        print(f"[*] Found existing authentication state at '{auth_file}'. Skipping manual login.")
        return auth_file

    print(f"[*] No existing '{auth_file}' found. Initiating secure manual login sequence...")
    
    # 1. Start the real Chrome application
    chrome_process = launch_real_chrome()
    time.sleep(3)  # Give Chrome a few seconds to fully open
    
    # 2. Connect Playwright to the real Chrome browser via CDP
    browser = p.chromium.connect_over_cdp(f"http://localhost:{DEBUG_PORT}")
    
    # 3. Grab the default window that Chrome just opened
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()

    print("[*] Navigating to Zoho...")
    page.goto("https://accounts.zoho.com/signin?servicename=ZohoBooks&signupurl=https://www.zoho.com%2fin%2fbooks%2fsignup%2f")

    # 4. Pause execution until the user manually authenticates
    input("\n[!] ACTION REQUIRED: Please login manually in the Chrome window.\n[!] Once you are fully logged in and the dashboard loads, press Enter here...")

    # 5. Save the session cookies and local storage
    context.storage_state(path=auth_file)
    print(f"[*] Authentication state successfully saved to '{auth_file}'!")

    # 6. Disconnect and kill the temporary Chrome instance
    browser.disconnect()
    chrome_process.terminate()
    
    return auth_file

def crawl_authenticated_pages(p: Playwright, auth_file: str):
    """
    Core crawling logic that uses the established authentication state.
    """
    print("\n[*] Starting crawler with authenticated session...")
    
    # For crawling, Playwright's built-in browser is usually fine 
    # since we already have the valid authentication cookies.
    browser = p.chromium.launch(headless=False, channel="chrome")
    
    context = browser.new_context(
        storage_state=auth_file,
        viewport={'width': 1920, 'height': 1080},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    
    page = context.new_page()
    Stealth().apply_stealth_sync(page)

    # read the auth.json file to get workspaceconf
    workspace_id = None
    with open(auth_file, 'r') as f:
        json_data = json.load(f)

        origins = json_data['origins']

        for origin in origins:
            if origin['origin'] == "https://books.zoho.in":
                localStorage = origin['localStorage']
                
                # get workspace id
                for item in localStorage:
                    if item['name'] == 'workspaceconf':
                        workspaceconf = json.loads(item['value'])
                        keys = list(workspaceconf.keys())
                        workspace_id = keys[0] if len(keys)>0 else ""
                        print(f"[*] Workspace ID: {workspace_id}")
                        break
                break

    print(f"[*] Workspace Conf: {workspace_id}")

                
    
    target_url = f"https://books.zoho.in/app/{workspace_id}#/home/dashboard" 
    
    print(f"[*] Navigating to target: {target_url}")
    page.goto(target_url)
    
    # Wait for the page to load
    page.wait_for_load_state("networkidle")
    
    print("[*] Crawl routine complete. Closing browser.")
    browser.close()

def main():
    setup_environment()
    
    with sync_playwright() as p:
        auth_state_path = ensure_authenticated(p, AUTH_FILE)
        crawl_authenticated_pages(p, auth_state_path)

if __name__ == "__main__":
    main()