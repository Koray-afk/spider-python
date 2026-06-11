"""CLI entrypoint and FastAPI server."""

import sys

from fastapi import FastAPI

from api.routes import router
from config.apps import APPS
from pipeline import (
    run_analyze_pipeline,
    run_clean_pipeline,
    run_crawl_pipeline,
    run_full_pipeline,
    run_preview_pipeline,
    run_stitch_pipeline,
)

app = FastAPI(title="Spider Python", version="0.1.0")
app.include_router(router)

COMMANDS = frozenset({"crawl", "stitch", "clean", "analyze", "pipeline", "preview"})


def usage() -> None:
    apps = ", ".join(sorted(APPS))
    print("Usage: python main.py <command> <app>")
    print()
    print("Commands:")
    print("  pipeline   Crawl → stitch → clean")
    print("  crawl        Crawl only (writes raw_html)")
    print("  stitch       Stitch only (raw_html → stitched_html)")
    print("  clean        Clean only (stitched_html → cleaned_html)")
    print("  analyze      Analyze only (cleaned_html → business_json, needs GEMINI_API_KEY)")
    print("  preview      Serve stitched_html via http.server")
    print("  serve        Start FastAPI on :8000")
    print()
    print(f"Apps: {apps}")
    print()
    print("Examples:")
    print("  python main.py pipeline zoho")
    print("  python main.py preview zoho")
    print("  python main.py serve")


def main() -> None:
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    command = sys.argv[1]

    if command == "serve":
        import uvicorn

        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
        return

    if command not in COMMANDS:
        usage()
        sys.exit(1)

    if len(sys.argv) < 3:
        print(f"Error: app name required.\n")
        print(f"  python main.py {command} <app>")
        sys.exit(1)

    app_name = sys.argv[2]

    if command == "pipeline":
        run_full_pipeline(app_name)
    elif command == "crawl":
        run_crawl_pipeline(app_name, auto_stitch=False)
    elif command == "stitch":
        run_stitch_pipeline(app_name)
    elif command == "clean":
        run_clean_pipeline(app_name)
    elif command == "analyze":
        run_analyze_pipeline(app_name)
    elif command == "preview":
        run_preview_pipeline(app_name)


if __name__ == "__main__":
    main()
