# tts_generator.py
import json
from pathlib import Path
from gtts import gTTS


def generate_audio(script_file="video_script.json", output_dir="audio"):
    print("Loading video script...")
    with open(script_file, "r", encoding="utf-8") as f:
        script = json.load(f)

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    print(f"Generating audio for {len(script['sections'])} sections...\n")

    audio_files = []

    for i, section in enumerate(script["sections"]):
        filename = f"{i+1:02d}_{section['title'].lower().replace(' ', '_')}.mp3"
        filepath = output_path / filename

        print(f"Section {i+1}: {section['title']}")

        tts = gTTS(text=section["script"], lang="en", slow=False)
        tts.save(str(filepath))

        audio_files.append(str(filepath))
        print(f"Saved: {filename}")

    print("\nALL AUDIO GENERATED!")
    return audio_files


if __name__ == "__main__":
    generate_audio()