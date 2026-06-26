from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse


def normalize_crawl_url(url: str) -> str:
    """Canonical URL for crawl queue, dedup, and stitch lookup.

    - Lowercase scheme and host
    - Merge hash-router fragments into path (fragment removed from output)
    - Preserve query string (including query embedded in the fragment)
    - Sort query parameters for stable matching
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    query = parsed.query

    if parsed.fragment:
        fragment = parsed.fragment
        if "?" in fragment:
            fragment_path, fragment_query = fragment.split("?", 1)
            query = f"{query}&{fragment_query}" if query else fragment_query
            fragment = fragment_path
        route = fragment.lstrip("/")
        if route:
            path = f"{path}/{route}"

    if query:
        params = parse_qsl(query, keep_blank_values=True)
        query = urlencode(sorted(params))

    return urlunparse((scheme, netloc, path, "", query, ""))


def resolve_href(base_url: str, href: str) -> str | None:
    if not href or href.startswith(("javascript:", "mailto:", "tel:", "data:")):
        return None

    absolute = urljoin(base_url, href)
    parsed = urlparse(absolute)
    if parsed.scheme not in ("http", "https"):
        return None

    return absolute
