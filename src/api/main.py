"""FastAPI app entrypoint. Read endpoints are added starting Stage 7."""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="Options Research & Evaluation Agent")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
