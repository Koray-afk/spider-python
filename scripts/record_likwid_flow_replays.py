#!/usr/bin/env python3
"""Optional: record success toasts from live Likwid for flow replay defaults."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from storage.storage_manager import get_metadata_dir

DEFAULTS = {
    "toasts": {
        "add_customer": "{{cust_comname}} added successfully.",
        "add_order": "Order {{order_id}} created successfully.",
        "add_sale_order": "Sale order created successfully.",
        "add_vendor": "{{vend_comname}} added successfully.",
        "add_item": "{{item_name}} added successfully.",
        "apply_filters": "Filters applied.",
    },
    "redirects": {
        "after_vendor": "../flow-ai-vendors-vendor-list/page.html",
        "after_sale_order": "../flow-ai-orders-orders-list/page.html",
    },
}


def main() -> int:
    out = get_metadata_dir("likwid") / "flow_replays.json"
    out.write_text(json.dumps(DEFAULTS, indent=2), encoding="utf-8")
    print(f"[RECORD] Wrote defaults to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
