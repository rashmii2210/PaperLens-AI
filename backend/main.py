# main.py
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from celery_worker import app as celery_app, generate_video_task

app = FastAPI(title="PaperLens AI - PDF to Video API")

# Allow all origins during development.
# Restrict to your frontend domain in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory where each job's files (PDF, audio, video) are stored.
JOBS_DIR = Path("jobs")
JOBS_DIR.mkdir(exist_ok=True)

# Base URL for serving generated videos.
# Override with the deployed backend URL in production via environment variable.
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Serve generated videos as static files at /videos/<job_id>/final_video.mp4
app.mount("/videos", StaticFiles(directory="jobs"), name="videos")


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Accept a PDF upload and start the video generation pipeline.
    Returns a job_id and task_id for status polling.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # Create a unique directory for this job
    job_id = str(uuid.uuid4())
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Save the uploaded PDF
    pdf_path = job_dir / "input.pdf"
    with open(pdf_path, "wb") as f:
        f.write(await file.read())

    # Dispatch the Celery background task
    task = generate_video_task.delay(str(pdf_path), job_id)

    return {
        "job_id": job_id,
        "task_id": task.id,
        "message": "Video generation started.",
    }


@app.get("/status/{task_id}")
def get_status(task_id: str):
    """
    Poll the status of a video generation task.
    Returns current step (0-4) and state: PENDING | PROGRESS | SUCCESS | FAILURE.
    """
    try:
        result = celery_app.AsyncResult(task_id)
        state = result.state
    except Exception:
        return {"state": "PENDING", "step": 0, "message": "Starting..."}

    if state == "PENDING":
        return {"state": "PENDING", "step": 0, "message": "Starting..."}

    if state == "PROGRESS":
        info = result.info or {}
        return {
            "state": "PROGRESS",
            "step": info.get("step", 0),
            "message": info.get("message", "Processing..."),
        }

    if state == "SUCCESS":
        info = result.result or {}

        # Handle cases where task returned a failure payload instead of raising
        if info.get("state") == "FAILURE":
            return {
                "state": "FAILURE",
                "step": 0,
                "message": info.get("message", "Unknown error"),
            }

        # Extract job_id from the saved video path
        video_path = Path(info.get("video_path", ""))
        job_id = video_path.parent.name

        return {
            "state": "SUCCESS",
            "step": 4,
            "message": "Video ready.",
            "video_url": f"{BASE_URL}/videos/{job_id}/final_video.mp4",
            "title": info.get("title", "Research Paper Video"),
        }

    if state == "FAILURE":
        try:
            message = str(result.info)
        except Exception:
            message = "An error occurred."
        return {"state": "FAILURE", "step": 0, "message": message}

    return {"state": state, "step": 0, "message": "Unknown state."}


@app.get("/health")
async def health():
    """Health check endpoint used by deployment platforms."""
    return {"status": "ok"}