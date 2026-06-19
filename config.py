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
        # Demo budget: enough for module lists + a few detail pages + /new forms.
        "max_pages_post_auth": 110,
        "max_interactions_per_page": 15,
        "max_ranked_interactions": 18,
        # None = click interactions on every crawled page regardless of BFS depth.
        "max_interaction_depth": None,
        # Faster crawl — HTML + interactions matter more than screenshots for stitch.
        "crawl_skip_screenshots": True,
        "crawl_wait_after_load_ms": 1000,
        "crawl_use_networkidle": False,
        "priority_url_patterns": [
            "#/home/",
            "#/inventory/product/index",
            "#/contacts",
            "/new",
            "variantslist",
        ],
        # Pre-queued at crawl start so demo-critical routes are captured early.
        "seed_url_patterns": [
            "#/inventory/product/index",
            "#/contacts",
            "#/invoices/new",
            "#/quotes/new",
            "#/expenses/new",
            "#/salesorders/new",
            "#/purchaseorders/new",
            "#/bills/new",
            "#/contacts/new",
            "#/vendors/new",
            "#/creditnotes/new",
            "#/paymentsreceived/new",
            "#/paymentsmade/new",
            "#/inventory/adjustments/new",
        ],
        # Cap row→detail links per list page (avoids 25+ identical item detail pages).
        "list_detail_link_limits": [
            {"pattern": "/variantslist/", "max_from_page": 3},
            {"pattern": "#/contacts/", "max_from_page": 3, "exclude_pattern": "/new"},
            {"pattern": "#/vendors/", "max_from_page": 2, "exclude_pattern": "/new"},
        ],
        # Don't crawl item detail URLs discovered from another item detail page.
        "link_cross_page_rules": [
            {
                "link_pattern": "/variantslist/",
                "source_pattern": "/variantslist/",
                "source_allow": "inventory/product/index",
            },
        ],
        "skip_url_patterns": [],
        # Always capture in-page tabs on detail views (Transactions, History, etc.).
        "mandatory_tab_labels": [
            "Overview",
            "Transactions",
            "History",
            "Comments",
            "Mails",
            "Statement",
            "Getting Started",
            "Recent Updates",
            "Dashboard",
        ],
    },
}


def get_app_config(app_name: str) -> dict:
    if app_name not in APPS:
        raise ValueError(f"Unknown app '{app_name}'. Add it to config.py")
    return APPS[app_name]
