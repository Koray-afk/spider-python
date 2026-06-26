import argparse

from stitcher import stitch_app


def parse_args():
    parser = argparse.ArgumentParser(description="Stitch captured pages into a static site")
    parser.add_argument("--app-name", required=True, help="App name (storage/<app-name>/crawl)")
    return parser.parse_args()


def main():
    args = parse_args()
    stitch_app(args.app_name)


if __name__ == "__main__":
    main()
