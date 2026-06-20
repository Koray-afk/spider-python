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
        "max_pages_post_auth": 120,
        "max_interactions_per_page": 15,
        "max_ranked_interactions": 18,
        "max_interaction_depth": None,
        "crawl_skip_screenshots": True,
        # Let fonts/CSS settle — 1s was making pages look blurry/incomplete.
        "crawl_wait_after_load_ms": 2000,
        "crawl_use_networkidle": True,
        "priority_url_patterns": [
            "#/home/dashboard",
            "#/invoices",
            "#/quotes",
            "#/contacts",
            "#/inventory/product/index",
            "/new",
        ],
        "seed_url_patterns": [
            "#/home/dashboard",
            "#/inventory/product/index",
            "#/contacts",
            "#/invoices",
            "#/quotes",
            "#/expenses",
            "#/salesorders",
            "#/purchaseorders",
            "#/bills",
            "#/paymentsreceived",
            "#/paymentsmade",
            "#/creditnotes",
            "#/recurringinvoices",
            "#/deliverychallans",
            "#/vendors",
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
        "list_detail_link_limits": [
            {"pattern": "/variantslist/", "max_from_page": 2},
            {"pattern": "#/contacts/", "max_from_page": 2, "exclude_pattern": "/new"},
            {"pattern": "#/vendors/", "max_from_page": 2, "exclude_pattern": "/new"},
        ],
        "global_link_limits": [
            {"pattern": "/variantslist/", "max_total": 2},
            {"pattern": "#/quotes/", "max_total": 1, "exclude_pattern": "/new"},
            {"pattern": "#/invoices/", "max_total": 1, "exclude_pattern": "/new"},
            {"pattern": "#/salesorders/", "max_total": 1, "exclude_pattern": "/new"},
            {"pattern": "#/paymentsreceived/", "max_total": 1, "exclude_pattern": "/new"},
            {"pattern": "#/purchaseorders/", "max_total": 1, "exclude_pattern": "/new"},
            {"pattern": "#/bills/", "max_total": 1, "exclude_pattern": "/new"},
        ],
        "link_cross_page_rules": [
            {
                "link_pattern": "/variantslist/",
                "source_pattern": "/variantslist/",
                "source_allow": "inventory/product/index",
            },
            {
                "link_pattern": "#/contacts/",
                "source_pattern": "#/contacts/",
                "source_allow_regex": r"#/contacts/?$",
            },
            {
                "link_pattern": "#/quotes/",
                "source_pattern": "#/quotes/",
                "source_allow_regex": r"#/quotes/?$",
            },
            {
                "link_pattern": "#/invoices/",
                "source_pattern": "#/invoices/",
                "source_allow_regex": r"#/invoices/?$",
            },
            {
                "link_pattern": "#/salesorders/",
                "source_pattern": "#/salesorders/",
                "source_allow_regex": r"#/salesorders/?$",
            },
            {
                "link_pattern": "#/paymentsreceived/",
                "source_pattern": "#/paymentsreceived/",
                "source_allow_regex": r"#/paymentsreceived/?$",
            },
        ],
        # Skip low-value routes that ate the last crawl's page budget.
        "skip_url_patterns": [
            "/settings/",
            "productedit",
            "bulkadd",
            "emailhistory-filter",
            "statement-filter",
            "comments-filter",
            "sales-filter-by",
            "customerpayment",
            "timesheet-projects-new",
            "reports-",
            "pricelists/386",
            "recurringbills",
            "recurringexpenses",
            "accountant/",
        ],
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
        # Walk left sidebar top-to-bottom; finish each page before the next module.
        "crawl_sidebar_first": True,
        # Resume from crawl_checkpoint.json after interrupt (use `clean` to reset).
        "crawl_resume": True,
    },
}


def get_app_config(app_name: str) -> dict:
    if app_name not in APPS:
        raise ValueError(f"Unknown app '{app_name}'. Add it to config.py")
    return APPS[app_name]
