import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
AUTH_DIR = ROOT_DIR / "auth"
STORAGE_DIR = ROOT_DIR / "storage"
ENGINE_DIR = ROOT_DIR / "engine"
ENGINE_DIST_DIR = ENGINE_DIR / "dist"

CRAWL_WORKERS = 1

CHROME_MAC_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEBUG_PORT = 9222
USER_DATA_DIR = os.path.expanduser("~/.saas_crawler_chrome_profile")
 
 
BROWSER_ARGS = [
    "--disable-web-security",
    "--allow-running-insecure-content",
]

EXTRA_WAIT_SECONDS = 2
NAVIGATION_TIMEOUT_MS = 60_000

SKIP_URL_KEYWORDS = (
    "logout",
    "signout",
    "privacy",
    "terms",
    "support",
    "help",
    "documentation",
    "docs",
)

APPS = {
    "zoho": {
        "pre_auth_home": "https://www.zoho.com/in/books/",
        "login_url": (
            "https://accounts.zoho.com/signin?servicename=ZohoBooks"
            "&signupurl=https://www.zoho.com%2fin%2fbooks%2fsignup%2f"
        ),
        "post_auth_home": "https://books.zoho.in/app/60073668069#/home/dashboard",
        "use_singlefile": False,
    },
    "hubspot": {
        "pre_auth_home": "https://www.hubspot.com/",
        "login_url": (
            "https://app.hubspot.com/login/"
            "?loginRedirectUrl=https%3A%2F%2Fapp-na2.hubspot.com%2Fglobal-home%2F246511976"
        ),
        "post_auth_home": "https://app-na2.hubspot.com/global-home/246511976",
        "use_singlefile": True,
    },
    "monday": {
        "pre_auth_home": "https://monday.com/",
        "login_url": (
            "https://auth.monday.com/auth/login_monday"
        ),
        "post_auth_home": "https://abhijain3002s-team-company.monday.com/workspaces/3168366",
        "use_singlefile": False,
    },
    "zoho_crm": {
        "pre_auth_home": "https://www.zoho.com/en-in/crm",
        "login_url": (
            "https://accounts.zoho.in/signin?servicename=ZohoCRM&signupurl=https://www.zoho.com/crm/signup.html&serviceurl=https://crm.zoho.in/crm/ShowHomePage.do?ref_value%3Ddirect%253Acrm%257Cdirect%253Acrm%257Cdirect%253Acrm%252Chttps%253A%252F%252Fwww.zoho.com%252Fen-in%252Fcrm%252F%252C%252CDesktop%252Chttps%253A%252F%252Fwww.zoho.com%252Fen-in%252Fcrm%252F"
        ),
        "post_auth_home": "https://crm.zoho.in/crm/org60075161245/tab/Home/begin",
        "use_singlefile": False,
    },
    "salesforce": {
        "pre_auth_home": "https://www.salesforce.com/in/",
        "login_url": (
            "https://login.salesforce.com/?locale=in"
        ),
        "use_singlefile": True,
        "post_auth_home": "https://inspiration-momentum-6695.lightning.force.com/lightning/page/home",
    }
}


def get_app_config(app_name: str) -> dict:
    if app_name not in APPS:
        known = ", ".join(sorted(APPS))
        raise ValueError(f"Unknown app '{app_name}'. Known apps: {known}")
    return APPS[app_name]
