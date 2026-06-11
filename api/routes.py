"""FastAPI routes — delegate to pipeline only."""

from fastapi import APIRouter

from pipeline import (
    run_business_analysis_pipeline,
    run_clean_pipeline,
    run_crawl_pipeline,
    run_full_pipeline,
    run_stitch_pipeline,
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
    return run_business_analysis_pipeline(app_name)


@router.post("/pipeline/{app_name}")
def pipeline_endpoint(app_name: str):
    return run_full_pipeline(app_name)
