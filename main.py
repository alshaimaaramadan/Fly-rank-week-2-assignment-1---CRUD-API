"""
Task API — a small to-do list served over HTTP.

Stage 0: the smallest thing that can possibly work — a server that starts,
listens on a port, and answers one request. Nothing else yet.

Run it with:
    .venv\\Scripts\\python -m uvicorn main:app --reload
"""

from fastapi import FastAPI

# `app` is the application object. Uvicorn (the web server) is pointed at it
# by name: "main:app" means "the variable `app` inside the file main.py".
app = FastAPI()


@app.get("/")
def hello():
    """Proof of life. If this answers, the server is running."""
    return {"message": "Hello from the Task API"}
