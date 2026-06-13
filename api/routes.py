"""FastAPI routes — delegate to pipeline only."""

import json
import os
import re

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from pipeline import (
    run_analyze_pipeline,
    run_catalog_pipeline,
    run_clean_pipeline,
    run_crawl_pipeline,
    run_full_pipeline,
    run_semantic_tree_pipeline,
    run_component_tree_pipeline,
    run_stitch_pipeline,
    run_workflows_pipeline,
    run_modules_pipeline,
)

router = APIRouter()

BASE = "storage/apps"


def _flat_slug(slug: str) -> str:
    return re.sub(r"^app-\d+-", "", slug)


def resolve_stitched_slug(app_name: str, page_id: str) -> str | None:
    """Map catalog page id (e.g. home-dashboard) to stitched_html folder name."""
    stitched_dir = os.path.join(BASE, app_name, "stitched_html")
    if not os.path.isdir(stitched_dir):
        return None

    direct = os.path.join(stitched_dir, page_id)
    if os.path.isdir(direct) and os.path.exists(os.path.join(direct, "index.html")):
        return page_id

    pattern = re.compile(rf"^app-\d+-{re.escape(page_id)}$")
    for name in os.listdir(stitched_dir):
        if pattern.match(name) and os.path.exists(os.path.join(stitched_dir, name, "index.html")):
            return name

    sitemap_path = os.path.join(BASE, app_name, "metadata", "sitemap.json")
    if os.path.exists(sitemap_path):
        with open(sitemap_path) as f:
            sitemap = json.load(f)
        for item in sitemap:
            if _flat_slug(item["slug"]) == page_id:
                slug = item["slug"]
                if os.path.exists(os.path.join(stitched_dir, slug, "index.html")):
                    return slug

    return None


@router.get("/apps/{app_name}/page_url/{page_id}")
def get_page_url(app_name: str, page_id: str):
    slug = resolve_stitched_slug(app_name, page_id)
    if not slug:
        return JSONResponse({"error": "page not found"}, status_code=404)
    return JSONResponse({"url": f"/static/{app_name}/{slug}/index.html"})


@router.get("/apps/{app_name}/catalog")
def get_catalog(app_name: str):
    path = f"{BASE}/{app_name}/app_catalog/catalog.json"
    if not os.path.exists(path):
        return JSONResponse({"error": "catalog not found"}, status_code=404)
    with open(path) as f:
        return JSONResponse(json.load(f))


@router.get("/apps/{app_name}/business/{page_id}")
def get_business_json(app_name: str, page_id: str):
    path = f"{BASE}/{app_name}/business_json/{page_id}.json"
    if not os.path.exists(path):
        return JSONResponse({}, status_code=404)
    with open(path) as f:
        return JSONResponse(json.load(f))


@router.get("/apps/{app_name}/component_tree/{page_id}")
def get_component_tree(app_name: str, page_id: str):
    path = f"{BASE}/{app_name}/component_tree/{page_id}.json"
    if not os.path.exists(path):
        return JSONResponse({}, status_code=404)
    with open(path) as f:
        return JSONResponse(json.load(f))


@router.get("/apps/{app_name}/semantic_tree/{page_id}")
def get_semantic_tree(app_name: str, page_id: str):
    path = f"{BASE}/{app_name}/semantic_tree/{page_id}.json"
    if not os.path.exists(path):
        return JSONResponse({}, status_code=404)
    with open(path) as f:
        return JSONResponse(json.load(f))


@router.post("/crawl/{app_name}")
def crawl_endpoint(app_name: str):
    return run_crawl_pipeline(app_name)


@router.post("/stitch/{app_name}")
def stitch_endpoint(app_name: str):
    return run_stitch_pipeline(app_name)


@router.post("/clean/{app_name}")
def clean_endpoint(app_name: str):
    return run_clean_pipeline(app_name)


@router.post("/analyze/{app_name}")
def analyze_endpoint(app_name: str):
    return run_analyze_pipeline(app_name)


@router.post("/semantic_tree/{app_name}")
def semantic_tree_endpoint(app_name: str):
    return run_semantic_tree_pipeline(app_name)


@router.post("/component_tree/{app_name}")
def component_tree_endpoint(app_name: str):
    return run_component_tree_pipeline(app_name)


@router.post("/catalog/{app_name}")
def catalog_endpoint(app_name: str):
    return run_catalog_pipeline(app_name)


@router.post("/workflows/{app_name}")
def workflows_endpoint(app_name: str):
    return run_workflows_pipeline(app_name)


@router.post("/modules/{app_name}")
def modules_endpoint(app_name: str):
    return run_modules_pipeline(app_name)


@router.post("/pipeline/{app_name}")
def pipeline_endpoint(app_name: str):
    return run_full_pipeline(app_name)
