"""Start the API with:  uvicorn app.main:app --reload"""
from fastapi import FastAPI

from app.api.reviews import router

app = FastAPI(
    title="AI Code Review Assistant",
    description="Advisory review of diffs: static analysis + hints. Never changes or runs code.",
    version="0.1.0",
)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}