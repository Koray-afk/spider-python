import os
import json
from services.gemini_service import analyze_page
from dotenv import load_dotenv
load_dotenv()

os.makedirs("analysis", exist_ok=True)

for filename in sorted(os.listdir("pages")):
    if not filename.endswith(".png"):
        continue

    slug = filename.replace(".png", "")       # page-1, page-2 ...
    png_path  = f"pages/{filename}"
    meta_path = f"pages/{slug}.meta"
    out_path  = f"analysis/{slug}.json"

    if os.path.exists(out_path):
        print(f"⏩ Skipping {slug}")
        continue

    url = open(meta_path).read().strip() \
          if os.path.exists(meta_path) else "unknown"

    print(f"🔍 Analyzing {slug} → {url}")

    try:
        raw_json = analyze_page(png_path, url)   # ← calls gemini_service

        # Clean and parse
        raw_json = raw_json.strip()
        if raw_json.startswith("```"):
            raw_json = raw_json.split("```")[1]
            if raw_json.startswith("json"):
                raw_json = raw_json[4:]
        raw_json = raw_json.strip()

        data = json.loads(raw_json)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"  ✅ Saved {out_path}")

    except Exception as e:
        print(f"  ⚠ Failed {slug}: {e}")