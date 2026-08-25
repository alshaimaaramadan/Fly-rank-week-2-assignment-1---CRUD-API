"""
Task API — a small to-do list served over HTTP.

Stage 1: the server now describes itself. `GET /` is the front door (what am I,
what version, what can I do) and `GET /health` is the one-line "am I alive?"
check that monitoring tools poll.

Run it with:
    .venv\\Scripts\\python -m uvicorn main:app --reload
"""

from fastapi import FastAPI

app = FastAPI(
    title="Task API",
    version="1.0",
    description="A tiny to-do list API. Data lives in memory and dies on restart.",
)


@app.get("/", summary="API information")
def root():
    """Describe this API: its name, its version, and where to go next."""
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health", summary="Health check")
def health():
    """Return 200 with a fixed body so uptime checks have something to poll."""
    return {"status": "ok"}
