import io
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
