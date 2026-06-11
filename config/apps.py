"""Per-application crawl configuration."""

APPS = {
    "zoho": {
        "pre_auth_home": "https://www.zoho.com/in/books/",
        "login_url": (
            "https://accounts.zoho.com/signin?servicename=ZohoBooks"
            "&signupurl=https://www.zoho.com%2fin%2fbooks%2fsignup%2f"
        ),
        "post_auth_home": "https://books.zoho.in",
        "max_pages_pre_auth": 5,
        "max_pages_post_auth": 20,
    },
}


def get_app_config(app_name: str) -> dict:
    if app_name not in APPS:
        raise ValueError(f"Unknown app '{app_name}'. Add it to config/apps.py")
    return APPS[app_name]
