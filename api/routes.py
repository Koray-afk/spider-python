"""FastAPI routes — delegate to pipeline only."""

from fastapi import APIRouter

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
