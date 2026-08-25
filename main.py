"""
Task API — a small to-do list served over HTTP.

Stage 5: the API documents itself. FastAPI reads the type hints, the models and
the docstrings below and builds an OpenAPI description from them, which Swagger
UI renders as a live, clickable page at http://localhost:8000/docs — no
hand-written docs to fall out of date.

Run it with:
    .venv\\Scripts\\python -m uvicorn main:app --reload
"""

from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Task API",
    version="1.0",
    description=(
        "A tiny to-do list API, built as an exercise in CRUD over HTTP.\n\n"
        "Tasks are held in a plain Python list inside the running process, so "
        "**everything is lost when the server restarts**. That is intentional: "
        "it is what 'no database' actually means."
    ),
    openapi_tags=[
        {"name": "meta", "description": "What this API is, and whether it is alive."},
        {"name": "tasks", "description": "Create, read, update and delete tasks."},
    ],
)


# Reusable Swagger documentation for the two error shapes this API returns.
NOT_FOUND = {
    "description": "No task has that id",
    "content": {"application/json": {"example": {"error": "Task 99 not found"}}},
}
BAD_REQUEST = {
    "description": "The request body was missing or malformed",
    "content": {
        "application/json": {
            "example": {"error": "Field 'title' is required and cannot be empty"}
        }
    },
}


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
    """What a client sends to create a task: a title, and nothing else."""

    title: Optional[str] = Field(default=None, examples=["Buy milk"])


class TaskUpdate(BaseModel):
    """An update may carry a new title, a new `done` value, or both. Sending
    neither is a mistake worth reporting rather than a no-op to shrug at."""

    title: Optional[str] = Field(default=None, examples=["Buy oat milk"])
    done: Optional[bool] = Field(default=None, examples=[True])


class Task(BaseModel):
    """What the API sends back. Declaring it gives Swagger a real schema to
    show instead of an anonymous blob."""

    id: int = Field(examples=[1])
    title: str = Field(examples=["Buy milk"])
    done: bool = Field(examples=[False])


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


@app.get(
    "/tasks",
    response_model=list[Task],
    summary="List every task",
    tags=["tasks"],
)
def list_tasks():
    """Return the whole list. An empty list is a valid answer here — it means
    'there are no tasks', which is different from 'that task doesn't exist'."""
    return tasks


@app.get(
    "/tasks/{task_id}",
    response_model=Task,
    responses={404: NOT_FOUND},
    summary="Get one task by id",
    tags=["tasks"],
)
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


@app.post(
    "/tasks",
    status_code=201,
    response_model=Task,
    responses={400: BAD_REQUEST},
    summary="Create a task",
    tags=["tasks"],
)
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


# --------------------------------------------------------------------------
# Stage 4 — update and delete
# --------------------------------------------------------------------------


@app.put(
    "/tasks/{task_id}",
    response_model=Task,
    responses={400: BAD_REQUEST, 404: NOT_FOUND},
    summary="Update a task",
    tags=["tasks"],
)
def update_task(task_id: int, payload: TaskUpdate):
    """Update a task's title, its done flag, or both, and return the result.

    Order matters: check that the task exists *before* judging the body, so a
    request for task 99 gets told the task is missing rather than being
    lectured about its fields."""
    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if payload.title is None and payload.done is None:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of 'title' or 'done'",
        )

    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="Field 'title' cannot be empty")
        task["title"] = title

    if payload.done is not None:
        task["done"] = payload.done

    return task


@app.delete(
    "/tasks/{task_id}",
    status_code=204,
    response_class=Response,
    responses={204: {"description": "Deleted. No content."}, 404: NOT_FOUND},
    summary="Delete a task",
    tags=["tasks"],
)
def delete_task(task_id: int):
    """Delete a task and return 204 No Content — success, nothing to say.

    204 means the body must be genuinely empty, so we hand back a bare Response
    rather than returning None and letting FastAPI serialise `null` into a body
    the status code promised wouldn't be there."""
    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    tasks.remove(task)
    return Response(status_code=204)
