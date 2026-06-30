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
    "hubspot": {
        # Use the login page itself as pre_auth_home so the crawler opens it,
        # waits for the user to log in, and does NOT mark any real app page as
        # visited before the authenticated post-auth phase begins.
        "pre_auth_home": "https://app-na2.hubspot.com/login",
        "login_url": "https://app-na2.hubspot.com/login",
        # Update the portal ID (246549280) if your account uses a different one.
        "post_auth_home": "https://app-na2.hubspot.com/contacts/246549280/contacts/list/view/all",
        "max_pages_pre_auth": 1,
        "max_pages_post_auth": 100,
        "max_interactions_per_page": 12,
        "max_ranked_interactions": 15,
        "max_interaction_depth": None,
        "crawl_skip_screenshots": True,
        # HubSpot's React SPA + styled-components need time to finish rendering.
        # 7 s gives the CSSOM polling in _inline_hubspot_styled_css a head start.
        "crawl_wait_after_load_ms": 7000,
        # HubSpot never fully reaches networkidle — use domcontentloaded + wait.
        "crawl_use_networkidle": False,
        # Sidebar lives in a cross-origin iframe Playwright can't read; use seeds.
        "crawl_sidebar_first": False,
        "crawl_resume": True,
        # NEW: tells routing helpers to treat paths (not #fragments) as distinct pages.
        "crawl_hash_routes": False,
        "priority_url_patterns": [
            "/global-home/",
            "/contacts/246549280/contacts/list/view/all",
            "/contacts/246549280/deals/board/view/all",
        ],
        "seed_url_patterns": [
            "/global-home/246549280",
            "/contacts/246549280/contacts/list/view/all",
            "/contacts/246549280/companies/list/view/all",
            "/contacts/246549280/deals/board/view/all",
            "/marketing/246549280/email/manage",
            "/forms/246549280",
            "/reports/246549280/dashboards",
        ],
        "list_detail_link_limits": [
            {"pattern": "/contacts/246549280/contact/", "max_from_page": 2},
            {"pattern": "/contacts/246549280/company/", "max_from_page": 2},
            {"pattern": "/contacts/246549280/deal/", "max_from_page": 2},
        ],
        "global_link_limits": [
            {"pattern": "/contacts/246549280/contact/", "max_total": 3},
            {"pattern": "/contacts/246549280/company/", "max_total": 3},
            {"pattern": "/contacts/246549280/deal/", "max_total": 3},
        ],
        "link_cross_page_rules": [],
        "skip_url_patterns": [
            "/pricing",
            "/upgrade",
            "/oauth/",
            "/integrations/",
            "/academy/",
            "/marketplace/",
            "/help/",
            "/notifications",
            "/user-preferences/",
            "/feedback/",
            "/logout",
            "/login",
            "/legal/",
            "/go-to/",
            "/user-guide/",
            "/sales-products-settings/",
            "/settings/",
        ],
        "mandatory_tab_labels": ["All", "Contacts", "Companies", "Deals"],
    },
    "stripe": {
        "pre_auth_home": "https://dashboard.stripe.com/login",
        "login_url": "https://dashboard.stripe.com/login",
        # Sandbox home — update /test/ → live paths if not using test mode.
        "post_auth_home": "https://dashboard.stripe.com/test/dashboard",
        "max_pages_pre_auth": 1,
        "max_pages_post_auth": 80,
        "max_interactions_per_page": 12,
        "max_ranked_interactions": 15,
        "max_interaction_depth": None,
        "crawl_skip_screenshots": True,
        # Stripe Sail SPA (db-NewChrome) needs time for CSSOM + sidebar render.
        # 8 s gives the React app enough time to finish API calls and fill content areas.
        "crawl_wait_after_load_ms": 8000,
        "crawl_use_networkidle": False,
        # Seed routes up front (HubSpot-style) — sidebar discovery alone misses Payments sub-nav.
        "crawl_sidebar_first": False,
        "crawl_resume": True,
        # Login is handled in post-auth ensure_auth(); skip crawling the login page.
        "crawl_pre_auth": False,
        "crawl_hash_routes": False,
        "priority_url_patterns": [
            "/test/dashboard",
            "/test/payments",
            "/test/customers",
            "/test/payments/analytics",
        ],
        "seed_url_patterns": [
            # Primary nav
            "/test/dashboard",
            "/test/balance/overview",
            "/test/payments",
            "/test/payouts",
            "/test/customers",
            "/test/products",
            # Products → Payments sub-sidebar
            "/test/payments/analytics",
            "/test/disputes",
            "/test/radar",
            "/test/payment-links",
            "/test/terminal",
            # Other Products sections (common routes)
            "/test/billing",
            "/test/reporting",
            "/test/apps",
        ],
        "list_detail_link_limits": [
            {"pattern": "/test/customers/", "max_from_page": 3, "exclude_pattern": "/test/customers"},
            {"pattern": "/test/payments/", "max_from_page": 2, "exclude_pattern": "/test/payments/analytics"},
        ],
        "global_link_limits": [
            {"pattern": "/test/customers/cus_", "max_total": 5},
            {"pattern": "/test/payments/pi_", "max_total": 5},
        ],
        "link_cross_page_rules": [],
        "skip_url_patterns": [
            "/settings",
            "/support",
            "/docs",
            "stripe.com/docs",
            "/developers",
            "/logout",
            "/login",
            "/register",
            "/reset",
            "/account/onboarding",
            "/identity",
            "/legal",
            "/privacy",
            "/connect/accounts",
        ],
        "mandatory_tab_labels": [
            "Payments",
            "Payouts",
            "Top-ups",
            "All activity",
        ],
        # Force-include the global `+` create button and any top-nav CTA
        # regardless of what the LLM picks — classified as interaction type.
        "mandatory_interaction_labels": ["+", "Create"],
        # Workbench is a heavy developer panel — depth-1 only even in non-hybrid mode.
        "url_interaction_depth_overrides": [
            {"pattern": "/workbench", "max_depth": 1},
        ],
        # Hybrid two-phase crawl: BFS discovers all URLs first, then a separate
        # interaction pass runs with per-URL depth control.
        "crawl_hybrid": True,
        # Important pages get depth-2 interactions (page interactions + nav-target interactions).
        # Everything else gets depth-1 (page interactions only).
        "interaction_depth_2_patterns": [
            "/test/dashboard",
            "/test/payments",
            "/test/customers",
            "/test/balance",
            "/test/radar",
            "/test/disputes",
        ],
    },
}


def get_app_config(app_name: str) -> dict:
    if app_name not in APPS:
        raise ValueError(f"Unknown app '{app_name}'. Add it to config.py")
    return APPS[app_name]
