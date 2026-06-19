import os
import sys
import json
from pathlib import Path
from celery import Celery

# Add backend folder to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

app = Celery(
    "tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)

@app.task(bind=True)
def generate_video_task(self, pdf_path, job_id):
    output_dir = Path(__file__).parent / "jobs" / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        self.update_state(state="PROGRESS", meta={"step": 1, "message": "Building RAG pipeline..."})
        from script_generator import generate_full_script
        script = generate_full_script(pdf_path)

        script_path = output_dir / "script.json"
        with open(script_path, "w") as f:
            json.dump(script, f, indent=2)

        self.update_state(state="PROGRESS", meta={"step": 2, "message": "Generating audio..."})
        from tts_generator import generate_audio
        audio_dir = output_dir / "audio"
        audio_dir.mkdir(exist_ok=True)
        generate_audio(script_file=str(script_path), output_dir=str(audio_dir))

        self.update_state(state="PROGRESS", meta={"step": 3, "message": "Assembling video..."})
        from video_assembler import assemble_video
        video_path = assemble_video(
            script_file=str(script_path),
            audio_dir=str(audio_dir),
            output_dir=str(output_dir)
        )

        return {
            "step": 4,
            "message": "Done!",
            "video_path": str(video_path),
            "title": script["paper_title"]
        }

    except Exception as e:
        # Return error as plain dict — avoids Celery Redis serialization bug
        return {
            "step": 0,
            "state": "FAILURE",
            "message": str(e)
        }