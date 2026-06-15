"""CLI for the crawler."""

import sys

from config import get_app_config
from crawler_v2 import crawl_application, crawl_postauth, crawl_preauth
from reconciler import reconcile_app
from src.runtime.server import DEFAULT_PORT, serve_app
from stitcher_v1 import stitch_app
from storage.storage_manager import clean_crawl, crawl_stats, get_crawl_dir


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} TB"


def cmd_status(app_name: str) -> None:
    stats = crawl_stats(app_name)
    root = get_crawl_dir(app_name)
    print(f"App: {app_name}")
    print(f"Storage: {root.resolve()}")
    print(f"Pages crawled: {stats['pages']}")
    print(f"Interaction captures: {stats['interactions']}")
    print(f"Storage size: {_fmt_bytes(stats['bytes'])}")


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
    print("Usage:")
    print("  python main.py crawl <app>           Pre-auth + post-auth crawl")
    print("  python main.py crawl-preauth <app>   Marketing pages only")
    print("  python main.py crawl-postauth <app>  Authenticated app only")
    print("  python main.py reconcile <app>       Extract per-interaction UI (reconciliation.json)")
    print("  python main.py stitch <app> [--no-expand-sidebars]")
    print("                                       Build navigable static clone")
    print("  python main.py serve <app> [--port N] [--watch] [--no-open]")
    print("                                       Serve the stitched clone locally")
    print("  python main.py status <app>          Show crawl stats")
    print("  python main.py clean <app>           Delete crawl output")


def main() -> None:
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    command = sys.argv[1]
    if command in ("-h", "--help"):
        usage()
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
    elif command == "reconcile":
        cmd_reconcile(app_name)
    elif command == "stitch":
        cmd_stitch(app_name, sys.argv[3:])
    elif command == "serve":
        cmd_serve(app_name, sys.argv[3:])
    elif command == "status":
        cmd_status(app_name)
    elif command == "clean":
        cmd_clean(app_name)
    else:
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
