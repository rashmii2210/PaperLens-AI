# video_assembler.py
import os
import json
import textwrap
import requests
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    ImageClip, AudioFileClip,
    concatenate_videoclips, CompositeVideoClip
)

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)


PEXELS_KEY = os.getenv("PEXELS_API_KEY")
VIDEO_SIZE = (640, 360)
CROSSFADE_DURATION = 0.3   # seconds between image transitions
IMAGES_PER_SECTION = 2     # how many images to cycle per section

def download_images(query, images_dir, prefix, count=IMAGES_PER_SECTION):
    """Download `count` landscape images from Pexels for a given query."""
    headers = {"Authorization": PEXELS_KEY}
    params = {"query": query, "per_page": count, "orientation": "landscape"}

    try:
        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers=headers, params=params, timeout=10
        )
        data = response.json()
    except Exception as e:
        print(f"Pexels fetch failed: {e}")
        return []

    photos = data.get("photos", [])
    if not photos:
        return []

    paths = []
    for i, photo in enumerate(photos[:count]):
        img_url = photo["src"]["large2x"]
        dest = Path(images_dir) / f"{prefix}_{i}.jpg"
        try:
            img_data = requests.get(img_url, timeout=15).content
            with open(dest, "wb") as f:
                f.write(img_data)
            paths.append(str(dest))
        except Exception as e:
            print(f"Image {i} download failed: {e}")

    return paths


def make_fallback_image(images_dir, prefix, color=(20, 24, 60)):
    """Solid-color fallback when Pexels returns nothing."""
    img = Image.new("RGB", VIDEO_SIZE, color=color)
    path = str(Path(images_dir) / f"{prefix}_fallback.jpg")
    img.save(path)
    return [path]


def make_styled_frame(image_path, title, caption_text, output_path):
    """
    Composite one video frame:
      - source image resized to VIDEO_SIZE
      - dark gradient overlay at bottom 40 %
      - section TITLE at top-left (small pill label)
      - CAPTION (word-wrapped) centred near bottom
    """
    img = Image.open(image_path).convert("RGB")
    img = img.resize(VIDEO_SIZE, Image.LANCZOS)

    gradient_h = int(VIDEO_SIZE[1] * 0.45)
    gradient = Image.new("RGBA", (VIDEO_SIZE[0], gradient_h), (0, 0, 0, 0))
    draw_g = ImageDraw.Draw(gradient)
    for y in range(gradient_h):
        alpha = int(200 * (y / gradient_h))   # 0 → 200 top to bottom
        draw_g.line([(0, y), (VIDEO_SIZE[0], y)], fill=(0, 0, 0, alpha))

    img_rgba = img.convert("RGBA")
    img_rgba.paste(gradient, (0, VIDEO_SIZE[1] - gradient_h), gradient)

    draw = ImageDraw.Draw(img_rgba)

    try:
        font_title  = ImageFont.truetype("arialbd.ttf", 18)
        font_caption = ImageFont.truetype("arial.ttf",  16)
    except:
        try:
            font_title  = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
            font_caption = ImageFont.truetype("DejaVuSans.ttf",     16)
        except:
            font_title  = ImageFont.load_default()
            font_caption = ImageFont.load_default()

    pill_padding = (16, 8)
    pill_x, pill_y = 32, 32
    bbox = draw.textbbox((0, 0), title, font=font_title)
    pill_w = bbox[2] - bbox[0] + pill_padding[0] * 2
    pill_h = bbox[3] - bbox[1] + pill_padding[1] * 2
    draw.rounded_rectangle(
        [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
        radius=8, fill=(108, 99, 255, 210)
    )
    draw.text(
        (pill_x + pill_padding[0], pill_y + pill_padding[1]),
        title, font=font_title, fill=(255, 255, 255, 255)
    )

    MAX_CHARS = 60
    wrapped = textwrap.fill(caption_text, width=MAX_CHARS)
    lines = wrapped.split("\n")

    line_height = 28
    total_text_h = len(lines) * line_height
    text_y = VIDEO_SIZE[1] - total_text_h - 20   # 48 px from bottom

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_caption)
        line_w = bbox[2] - bbox[0]
        x = (VIDEO_SIZE[0] - line_w) // 2

        # shadow
        draw.text((x + 2, text_y + 2), line, font=font_caption, fill=(0, 0, 0, 200))
        # text
        draw.text((x, text_y), line, font=font_caption, fill=(255, 255, 255, 255))
        text_y += line_height

    final = img_rgba.convert("RGB")
    final.save(output_path, quality=92)
    return output_path


def split_script_into_chunks(script_text, n_images):
    """
    Divide the script text into `n_images` roughly equal chunks,
    one per image slide.
    """
    words = script_text.split()
    chunk_size = max(1, len(words) // n_images)
    chunks = []
    for i in range(n_images):
        start = i * chunk_size
        end = start + chunk_size if i < n_images - 1 else len(words)
        chunks.append(" ".join(words[start:end]))
    return chunks

def create_section_clip(section, index, audio_dir, images_dir):
    title        = section["title"]
    visual_hint  = section.get("visual_hint", title)
    script_text  = section.get("script", title)

    print(f"\nSection {index+1}: {title}")

    # ── audio ─────────────────────────────────────────────────────────────
    audio_filename = f"{index+1:02d}_{title.lower().replace(' ', '_')}.mp3"
    audio_path = Path(audio_dir) / audio_filename

    if not audio_path.exists():
        print(f"Audio not found: {audio_path}")
        return None

    audio_clip = AudioFileClip(str(audio_path))
    total_duration = audio_clip.duration
    print(f"Audio duration: {total_duration:.1f}s")

    section_images_dir = Path(images_dir) / f"sec_{index+1:02d}"
    section_images_dir.mkdir(parents=True, exist_ok=True)

    raw_paths = download_images(visual_hint, str(section_images_dir), "img", IMAGES_PER_SECTION)
    if not raw_paths:
        print("No images from Pexels, using fallback colour")
        raw_paths = make_fallback_image(str(section_images_dir), "img")

    n = len(raw_paths)
    print(f"{n} image(s) fetched")

    caption_chunks = split_script_into_chunks(script_text, n)

    clip_dur = (total_duration + (n - 1) * CROSSFADE_DURATION) / n
    clip_dur = max(clip_dur, 1.5)   # never shorter than 1.5 s

    sub_clips = []
    for i, (img_path, caption) in enumerate(zip(raw_paths, caption_chunks)):
        styled_path = str(section_images_dir / f"styled_{i}.jpg")
        make_styled_frame(img_path, title, caption, styled_path)

        sub = ImageClip(styled_path).set_duration(clip_dur)

        if i > 0:
            sub = sub.crossfadein(CROSSFADE_DURATION)

        sub_clips.append(sub)

    if len(sub_clips) == 1:
        section_video = sub_clips[0]
    else:
        section_video = concatenate_videoclips(
            sub_clips, method="compose", padding=-CROSSFADE_DURATION
        )

    if section_video.duration > total_duration:
        section_video = section_video.subclip(0, total_duration)
    elif section_video.duration < total_duration:
        # extend last frame
        last_frame = sub_clips[-1].set_duration(
            total_duration - section_video.duration + sub_clips[-1].duration
        )
        sub_clips[-1] = last_frame
        section_video = concatenate_videoclips(
            sub_clips, method="compose", padding=-CROSSFADE_DURATION
        )
        section_video = section_video.subclip(0, total_duration)

    section_video = section_video.set_audio(audio_clip)
    print(f"Clip ready ({section_video.duration:.1f}s, {n} images, captions on)")
    return section_video

def assemble_video(
    script_file="video_script.json",
    audio_dir="audio",
    output_dir="output"
):
    print("Loading script...")
    with open(script_file, "r", encoding="utf-8") as f:
        script = json.load(f)

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    images_dir = output_path / "images"
    images_dir.mkdir(exist_ok=True)

    print(f"\nAssembling: {script['paper_title']}")
    print(f"   Sections: {len(script['sections'])}")
    print(f"   Images per section: {IMAGES_PER_SECTION}")
    print(f"   Captions: ON\n")

    clips = []
    for i, section in enumerate(script["sections"]):
        clip = create_section_clip(section, i, audio_dir, str(images_dir))
        if clip:
            clips.append(clip)

    if not clips:
        raise Exception("No clips created!")

    print(f"\nJoining {len(clips)} section clips...")
    final_video = concatenate_videoclips(clips, method="compose")

    video_path = output_path / "final_video.mp4"

    print("Rendering final video (this takes a few minutes)...")
    final_video.write_videofile(
        str(video_path),
        fps=24,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="ultrafast",      
        logger="bar"
    )

    total_seconds = final_video.duration
    print(f"\nVideo saved: {video_path}")
    print(f"   Total duration: {int(total_seconds // 60)}m {int(total_seconds % 60)}s")
    return str(video_path)


if __name__ == "__main__":
    assemble_video()