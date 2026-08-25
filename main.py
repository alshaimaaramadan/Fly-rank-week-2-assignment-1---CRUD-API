"""
Task API — a small to-do list served over HTTP.

Stage 3: the API now accepts new tasks. The client sends a title; the server
decides everything else — the id, the starting `done` value, and whether the
request was acceptable at all. The server never trusts the client.

Run it with:
    .venv\\Scripts\\python -m uvicorn main:app --reload
"""

from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

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


def next_id() -> int:
    """Pick the next free id.

    Deliberately max(existing) + 1 rather than len(tasks) + 1. After deleting a
    task the length drops, so len()+1 would hand out an id that is already in
    use — two tasks with the same id, and the bug shows up much later."""
    return max((task["id"] for task in tasks), default=0) + 1


# --------------------------------------------------------------------------
# Request bodies
# --------------------------------------------------------------------------
# `title` is declared Optional on purpose. If Pydantic enforced it, a missing
# title would come back as HTTP 422; this API is specified to answer 400. So
# the field is optional to Pydantic and checked by hand in the handler below,
# where we control the status code and the message.


class TaskCreate(BaseModel):
    title: Optional[str] = None


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


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Catch bodies so malformed that Pydantic rejects them before our code
    runs — a JSON syntax error, or `title` sent as a list. FastAPI's default is
    422; a bad request from the client is a 400 as far as this API is
    concerned, and it should look like every other error it returns."""
    return JSONResponse(status_code=400, content={"error": "Invalid request body"})


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


# --------------------------------------------------------------------------
# Stage 3 — create
# --------------------------------------------------------------------------


@app.post("/tasks", status_code=201, summary="Create a task", tags=["tasks"])
def create_task(payload: TaskCreate):
    """Create a task from a title and return it with 201 Created.

    The client supplies only the title. The id and the starting `done` value
    are the server's to decide — letting a client choose its own id is how you
    end up with collisions and overwritten data."""
    title = (payload.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Field 'title' is required and cannot be empty")

    task = {"id": next_id(), "title": title, "done": False}
    tasks.append(task)
    return task
