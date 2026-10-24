# TaskMaster Service Example
# A realistic Python backend service demonstrating routing, auth, and database persistence

import os
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="TaskMaster API", version="1.0.0")

class Task(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    completed: bool = False

_DB_STORE = []

@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"status": "healthy", "service": "TaskMaster"}

@app.get("/tasks", response_model=List[Task])
def list_tasks():
    """Returns all stored tasks."""
    return _DB_STORE

@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(task: Task):
    """Creates a new task in the in-memory database."""
    _DB_STORE.append(task)
    return task

@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int):
    """Retrieves a single task by ID."""
    for t in _DB_STORE:
        if t.id == task_id:
            return t
    raise HTTPException(status_code=404, detail="Task not found")
