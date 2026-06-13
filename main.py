"""CLI entrypoint and FastAPI server."""

import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes import router
from config.apps import APPS
from pipeline import (
    run_analyze_pipeline,
    run_catalog_pipeline,
    run_clean_pipeline,
    run_crawl_pipeline,
    run_full_pipeline,
    run_preview_pipeline,
    run_semantic_tree_pipeline,
    run_component_tree_pipeline,
    run_stitch_pipeline,
    run_workflows_pipeline,
    run_modules_pipeline,
)

app = FastAPI(title="Spider Python", version="0.1.0")

# CORS — allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount stitched HTML as static files
STORAGE = "storage/apps"
for app_name in os.listdir(STORAGE):
    stitched = f"{STORAGE}/{app_name}/stitched_html"
    if os.path.isdir(stitched):
        app.mount(
            f"/static/{app_name}",
            StaticFiles(directory=stitched),
            name=f"static_{app_name}",
        )

app.include_router(router)

COMMANDS = frozenset({
    "crawl",
    "stitch",
    "clean",
    "analyze",
    "semantic_tree",
    "component_tree",
    "catalog",
    "workflows",
    "modules",
    "pipeline",
    "preview",
})


def usage() -> None:
    apps = ", ".join(sorted(APPS))
    print("Usage: python main.py <command> <app>")
    print()
    print("Commands:")
    print("  pipeline   Crawl → stitch → clean")
    print("  crawl        Crawl only (writes raw_html)")
    print("  stitch       Stitch only (raw_html → stitched_html)")
    print("  clean        Clean only (stitched_html → cleaned_html)")
    print("  analyze        Analyze only (cleaned_html → business_json, needs GEMINI_API_KEY)")
    print(
        "  semantic_tree  Semantic UI tree "
        "(cleaned_html + business_json → semantic_tree, needs GEMINI_API_KEY)"
    )
    print(
        "  component_tree React component tree "
        "(semantic_tree → component_tree, needs GEMINI_API_KEY)"
    )
    print(
        "  catalog        Application catalog "
        "(business_json + semantic_tree → app_catalog/catalog.json, needs GEMINI_API_KEY)"
    )
    print(
        "  workflows      Business workflows "
        "(catalog → app_catalog/workflows.json, needs GEMINI_API_KEY)"
    )
    print(
        "  modules        Business modules "
        "(catalog + workflows → app_catalog/modules.json, needs GEMINI_API_KEY)"
    )
    print("  preview        Serve stitched_html via http.server")
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
    elif command == "semantic_tree":
        run_semantic_tree_pipeline(app_name)
    elif command == "component_tree":
        run_component_tree_pipeline(app_name)
    elif command == "catalog":
        run_catalog_pipeline(app_name)
    elif command == "workflows":
        run_workflows_pipeline(app_name)
    elif command == "modules":
        run_modules_pipeline(app_name)
    elif command == "preview":
        run_preview_pipeline(app_name)


if __name__ == "__main__":
    main()
