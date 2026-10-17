"""HTTP endpoints. They only READ code and return a report."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from app.pipeline import MAX_DIFF_CHARS, review_diff
from app.reports.review_report import render_markdown

router = APIRouter(prefix="/reviews", tags=["reviews"])
Format = Literal["json", "markdown"]


class DiffRequest(BaseModel):
    diff: str


def _decode(raw: bytes) -> str:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):  # UTF-16 from PowerShell
        return raw.decode("utf-16")
    return raw.decode("utf-8-sig", errors="replace")


def _respond(diff: str, fmt: Format):
    try:
        result = review_diff(diff)
    except ValueError as exc:  # diff too large
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    if fmt == "markdown":
        return PlainTextResponse(render_markdown(result))
    return JSONResponse(result.model_dump(mode="json"))


@router.post("")
def review_from_text(body: DiffRequest, format: Format = Query("json")):
    return _respond(body.diff, format)


@router.post("/upload")
async def review_from_upload(file: UploadFile = File(...), format: Format = Query("json")):
    raw = await file.read(MAX_DIFF_CHARS + 1)
    return _respond(_decode(raw), format)