import argparse
import asyncio

from crawler import crawl_app


def parse_args():
    parser = argparse.ArgumentParser(description="Simple authenticated SaaS crawler")
    parser.add_argument("--app-name", required=True, help="App key from config.APPS")
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run crawl browser in headed mode (default: headless)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    asyncio.run(crawl_app(args.app_name, headless=not args.headed))


if __name__ == "__main__":
    main()
