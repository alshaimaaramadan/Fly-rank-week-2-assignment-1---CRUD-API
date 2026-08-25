"""
Task API — a small to-do list served over HTTP.

Stage 2: the API now has data. Three example tasks live in a plain Python list,
and two endpoints read from it: one for the whole list, one for a single task
by id. Asking for a task that doesn't exist is an error, not an empty answer.

Run it with:
    .venv\\Scripts\\python -m uvicorn main:app --reload
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Task API",
    version="1.0",
    description="A tiny to-do list API. Data lives in memory and dies on restart.",
)


# --------------------------------------------------------------------------
# Storage
# --------------------------------------------------------------------------
# This list IS the database. It lives in the server process's memory, which
# means every task is lost the moment the process stops. That is deliberate
# for this exercise — see the "mortality experiment" in the README.

tasks = [
    {"id": 1, "title": "Read the assignment", "done": True},
    {"id": 2, "title": "Build the API", "done": False},
    {"id": 3, "title": "Write the README", "done": False},
]


def find_task(task_id: int):
    """Return the task with this id, or None if there isn't one."""
    for task in tasks:
        if task["id"] == task_id:
            return task
    return None


# --------------------------------------------------------------------------
# Error shape
# --------------------------------------------------------------------------
# By default FastAPI reports errors as {"detail": "..."}. This API is specified
# to use {"error": "..."} instead, so we intercept HTTPException and re-render
# it. Raising HTTPException(404, "Task 99 not found") anywhere in this file now
# produces exactly {"error": "Task 99 not found"}.


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


# --------------------------------------------------------------------------
# Stage 1 — information endpoints
# --------------------------------------------------------------------------


@app.get("/", summary="API information", tags=["meta"])
def root():
    """Describe this API: its name, its version, and where to go next."""
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health", summary="Health check", tags=["meta"])
def health():
    """Return 200 with a fixed body so uptime checks have something to poll."""
    return {"status": "ok"}


# --------------------------------------------------------------------------
# Stage 2 — read endpoints
# --------------------------------------------------------------------------


@app.get("/tasks", summary="List every task", tags=["tasks"])
def list_tasks():
    """Return the whole list. An empty list is a valid answer here — it means
    'there are no tasks', which is different from 'that task doesn't exist'."""
    return tasks


@app.get("/tasks/{task_id}", summary="Get one task by id", tags=["tasks"])
def get_task(task_id: int):
    """Return a single task, or 404 if no task has that id.

    Never answer 200 with an empty body for something that doesn't exist —
    that tells the client "here you go" about nothing at all."""
    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task
