import os
from services.gemini_service import generate_replica
from dotenv import load_dotenv
load_dotenv()

os.makedirs("replicas", exist_ok=True)

for filename in sorted(os.listdir("pages")):
    if not filename.endswith(".png"):
        continue

    slug = filename.replace(".png", "")
    png_path  = f"pages/{filename}"
    meta_path = f"pages/{slug}.meta"
    out_path  = f"replicas/{slug}.html"

    if os.path.exists(out_path):
        print(f"⏩ Skipping {slug}")
        continue

    url = open(meta_path).read().strip() \
          if os.path.exists(meta_path) else "unknown"

    print(f"🏗 Generating replica for {slug} → {url}")

    try:
        html = generate_replica(png_path, url)   # ← calls gemini_service

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"  ✅ Saved → {out_path}")

    except Exception as e:
        print(f"  ⚠ Failed {slug}: {e}")

print("\n🎉 All replicas generated in replicas/")