"""Local testing entrypoint and FastAPI server."""

import sys

from fastapi import FastAPI

from api.routes import router
from pipeline import run_full_pipeline

app = FastAPI(title="Spider Python", version="0.1.0")
app.include_router(router)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        import uvicorn

        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    else:
        app_name = sys.argv[1] if len(sys.argv) > 1 else "zoho"
        run_full_pipeline(app_name)
