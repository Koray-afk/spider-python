"""CLI for the crawler."""

import sys

from config import APPS, get_app_config
from crawler_v2 import crawl_application, crawl_interaction_pass, crawl_postauth, crawl_preauth
from reconciler import reconcile_app
from src.runtime.server import DEFAULT_PORT, serve_app
from stitcher_v1 import stitch_app
from storage.storage_manager import clean_crawl, crawl_stats, get_crawl_checkpoint_path, get_crawl_dir


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} TB"


def cmd_status(app_name: str) -> None:
    stats = crawl_stats(app_name)
    root = get_crawl_dir(app_name)
    ckpt = get_crawl_checkpoint_path(app_name)
    print(f"App: {app_name}")
    print(f"Storage: {root.resolve()}")
    print(f"Pages crawled: {stats['pages']}")
    print(f"Interaction captures: {stats['interactions']}")
    print(f"Storage size: {_fmt_bytes(stats['bytes'])}")
    if ckpt.is_file():
        import json
        data = json.loads(ckpt.read_text(encoding="utf-8"))
        sq = len(data.get("sidebar_queue") or [])
        dq = len(data.get("deferred_queue") or [])
        print(f"Checkpoint: yes ({sq} sidebar + {dq} deferred remaining)")
    else:
        print("Checkpoint: none (fresh crawl or finished)")


def cmd_clean(app_name: str) -> None:
    clean_crawl(app_name)
    print(f"Deleted crawl output for {app_name}")


def cmd_reconcile(app_name: str) -> None:
    result = reconcile_app(app_name)
    counts = ", ".join(f"{k}={v}" for k, v in sorted(result["type_counts"].items()))
    print(
        f"Reconciled: {result['interactions']} interactions"
        + (f" ({counts})" if counts else "")
    )


def cmd_stitch(app_name: str, args: list[str]) -> None:
    expand_sidebars = "--no-expand-sidebars" not in args
    result = stitch_app(app_name, expand_sidebars=expand_sidebars)
    print(
        f"Stitched: {result['pages']} pages, "
        f"{result['interactions_bound']}/{result['interactions_total']} interactions wired, "
        f"{result['accordions']} accordions"
    )
    print(f"Output: {result['output']}")


def cmd_serve(app_name: str, args: list[str]) -> None:
    port = DEFAULT_PORT
    watch = "--watch" in args
    open_browser = "--no-open" not in args
    if "--port" in args:
        i = args.index("--port")
        try:
            port = int(args[i + 1])
        except (IndexError, ValueError):
            print("Error: --port requires a number, e.g. --port 8000")
            sys.exit(1)
    try:
        serve_app(app_name, port, watch=watch, open_browser=open_browser)
    except (FileNotFoundError, OSError) as exc:
        print(f"Error: {exc}")
        sys.exit(1)


def usage() -> None:
    apps = ", ".join(sorted(APPS))
    print("Usage:")
    print("  python main.py crawl <app>           Pre-auth + post-auth crawl")
    print("  python main.py crawl-preauth <app>   Marketing pages only")
    print("  python main.py crawl-postauth <app>  Authenticated app only")
    print("  python main.py crawl-interactions <app>  Interaction pass on discovered pages (hybrid phase 2)")
    print("  python main.py capture-interactions <app> [--url URL]")
    print("                                       Manual interaction capture (interactive browser)")
    print("  python main.py reconcile <app>       Extract per-interaction UI (reconciliation.json)")
    print("  python main.py stitch <app> [--no-expand-sidebars]")
    print("                                       Build navigable static clone")
    print("  python main.py serve <app> [--port N] [--watch] [--no-open]")
    print("                                       Serve the stitched clone locally")
    print("  python main.py status <app>          Show crawl stats")
    print("  python main.py coverage <app>       Audit dead buttons / missing routes")
    print("  python main.py clean <app>           Delete crawl output + checkpoint")
    print("  python main.py html-clean <app>      stitched_html → cleaned_html (for LLM analysis)")
    print("  python main.py analyze <app>         cleaned_html → business_json (needs GEMINI_API_KEY)")
    print("  python main.py semantic_tree <app>   Semantic UI tree (needs GEMINI_API_KEY)")
    print("  python main.py component_tree <app>  React component tree (needs GEMINI_API_KEY)")
    print("  python main.py catalog <app>         Application catalog (needs GEMINI_API_KEY)")
    print("  python main.py workflows <app>       Business workflows (needs GEMINI_API_KEY)")
    print("  python main.py modules <app>         Business modules (needs GEMINI_API_KEY)")
    print("  python main.py preview <app>         Serve stitched_html via http.server")
    print("  python main.py api                   Start FastAPI on :8000")
    print()
    print(f"Apps: {apps}")


def main() -> None:
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    command = sys.argv[1]
    if command in ("-h", "--help"):
        usage()
        return

    if command == "api":
        import uvicorn

        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
        return

    if len(sys.argv) < 3:
        print(f"Error: app name required.\n  python main.py {command} <app>")
        sys.exit(1)

    app_name = sys.argv[2]
    try:
        cfg = get_app_config(app_name)
    except ValueError as exc:
        print(exc)
        sys.exit(1)

    if command == "crawl":
        result = crawl_application(app_name, cfg)
        print(f"Done: {result['pages_crawled']} pages, {result['interactions']} interactions saved")
    elif command == "crawl-preauth":
        result = crawl_preauth(app_name, cfg)
        print(f"Done: {result['pages']} pages, {result['interactions_saved']} interactions saved")
    elif command == "crawl-postauth":
        result = crawl_postauth(app_name, cfg)
        print(f"Done: {result['pages']} pages, {result['interactions_saved']} interactions saved")
    elif command == "crawl-interactions":
        result = crawl_interaction_pass(app_name, cfg)
        print(f"Done: {result['pages']} pages, {result['interactions_saved']} interactions saved")
    elif command == "capture-interactions":
        from manual_capture import run_manual_capture

        run_manual_capture(app_name, cfg, sys.argv[3:])
    elif command == "reconcile":
        cmd_reconcile(app_name)
    elif command == "stitch":
        cmd_stitch(app_name, sys.argv[3:])
    elif command == "serve":
        cmd_serve(app_name, sys.argv[3:])
    elif command == "status":
        cmd_status(app_name)
    elif command == "coverage":
        from coverage import print_audit

        print_audit(app_name)
    elif command == "clean":
        cmd_clean(app_name)
    elif command == "html-clean":
        from pipeline import run_clean_pipeline

        run_clean_pipeline(app_name)
    elif command == "analyze":
        from pipeline import run_analyze_pipeline

        run_analyze_pipeline(app_name)
    elif command == "semantic_tree":
        from pipeline import run_semantic_tree_pipeline

        run_semantic_tree_pipeline(app_name)
    elif command == "component_tree":
        from pipeline import run_component_tree_pipeline

        run_component_tree_pipeline(app_name)
    elif command == "catalog":
        from pipeline import run_catalog_pipeline

        run_catalog_pipeline(app_name)
    elif command == "workflows":
        from pipeline import run_workflows_pipeline

        run_workflows_pipeline(app_name)
    elif command == "modules":
        from pipeline import run_modules_pipeline

        run_modules_pipeline(app_name)
    elif command == "preview":
        from pipeline import run_preview_pipeline

        run_preview_pipeline(app_name)
    else:
        usage()
        sys.exit(1)


# FastAPI app (used by `python main.py api`)
try:
    from fastapi import FastAPI

    from api.routes import router

    app = FastAPI(title="Spider Python", version="0.1.0")
    app.include_router(router)
except ImportError:
    app = None  # type: ignore[assignment,misc]


if __name__ == "__main__":
    main()
