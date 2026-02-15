import io
import os
import zipfile

from backend.models import Project
from backend.services.srt_service import generate_srt


def build_export_zip(project: Project) -> bytes:
    """Build a ZIP with all content organized by language."""
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        slug = f"{project.artist}_{project.work}".replace(" ", "_")

        # Original content (hook language)
        _write_language_folder(
            zf,
            folder=f"{slug}/original",
            overlay_json=project.overlay_json,
            post_text=project.post_text,
            youtube_title=project.youtube_title,
            youtube_tags=project.youtube_tags,
            cut_end=project.cut_end,
        )

        # Translations
        for t in project.translations:
            _write_language_folder(
                zf,
                folder=f"{slug}/{t.language}",
                overlay_json=t.overlay_json,
                post_text=t.post_text,
                youtube_title=t.youtube_title,
                youtube_tags=t.youtube_tags,
                cut_end=project.cut_end,
            )

    return buffer.getvalue()


def _write_language_folder(
    zf: zipfile.ZipFile,
    folder: str,
    overlay_json,
    post_text,
    youtube_title,
    youtube_tags,
    cut_end=None,
):
    if overlay_json:
        srt_content = generate_srt(overlay_json, cut_end)
        zf.writestr(f"{folder}/subtitles.srt", srt_content)

    if post_text:
        zf.writestr(f"{folder}/post.txt", post_text)

    yt_content = ""
    if youtube_title:
        yt_content += f"Title: {youtube_title}\n"
    if youtube_tags:
        yt_content += f"Tags: {youtube_tags}\n"
    if yt_content:
        zf.writestr(f"{folder}/youtube.txt", yt_content)


def export_to_folder(project: Project, export_path: str) -> str:
    """Export all content to a folder on disk (e.g. iCloud).

    Structure: {export_path}/{Artist} - {Work}/{language}/post.txt, youtube.txt, subtitles.srt
    Returns the project folder path.
    """
    slug = f"{project.artist} - {project.work}"
    project_dir = os.path.join(export_path, slug)

    # Write translations (which now include the source language)
    for t in project.translations:
        lang_dir = os.path.join(project_dir, t.language)
        os.makedirs(lang_dir, exist_ok=True)
        _write_language_to_disk(
            folder=lang_dir,
            overlay_json=t.overlay_json,
            post_text=t.post_text,
            youtube_title=t.youtube_title,
            youtube_tags=t.youtube_tags,
            cut_end=project.cut_end,
        )

    return project_dir


def _write_language_to_disk(
    folder: str,
    overlay_json,
    post_text,
    youtube_title,
    youtube_tags,
    cut_end=None,
):
    if overlay_json:
        srt_content = generate_srt(overlay_json, cut_end)
        with open(os.path.join(folder, "subtitles.srt"), "w", encoding="utf-8") as f:
            f.write(srt_content)

    if post_text:
        with open(os.path.join(folder, "post.txt"), "w", encoding="utf-8") as f:
            f.write(post_text)

    yt_content = ""
    if youtube_title:
        yt_content += f"Title: {youtube_title}\n"
    if youtube_tags:
        yt_content += f"Tags: {youtube_tags}\n"
    if yt_content:
        with open(os.path.join(folder, "youtube.txt"), "w", encoding="utf-8") as f:
            f.write(yt_content)
