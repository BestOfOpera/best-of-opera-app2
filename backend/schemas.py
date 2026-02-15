import datetime
from typing import Optional, List
from pydantic import BaseModel


class DetectMetadataResponse(BaseModel):
    artist: str = ""
    work: str = ""
    composer: str = ""
    composition_year: str = ""
    nationality: str = ""
    nationality_flag: str = ""
    voice_type: str = ""
    birth_date: str = ""
    death_date: str = ""
    album_opera: str = ""
    confidence: str = "high"


class ProjectCreate(BaseModel):
    youtube_url: str = ""
    artist: str
    work: str
    composer: str
    composition_year: str = ""
    nationality: str = ""
    nationality_flag: str = ""
    voice_type: str = ""
    birth_date: str = ""
    death_date: str = ""
    album_opera: str = ""
    category: str = ""
    hook: str = ""
    hook_category: str = ""
    highlights: str = ""
    original_duration: str = ""
    cut_start: str = ""
    cut_end: str = ""


class ProjectUpdate(BaseModel):
    youtube_url: Optional[str] = None
    artist: Optional[str] = None
    work: Optional[str] = None
    composer: Optional[str] = None
    composition_year: Optional[str] = None
    nationality: Optional[str] = None
    nationality_flag: Optional[str] = None
    voice_type: Optional[str] = None
    birth_date: Optional[str] = None
    death_date: Optional[str] = None
    album_opera: Optional[str] = None
    category: Optional[str] = None
    hook: Optional[str] = None
    hook_category: Optional[str] = None
    highlights: Optional[str] = None
    original_duration: Optional[str] = None
    cut_start: Optional[str] = None
    cut_end: Optional[str] = None


class TranslationOut(BaseModel):
    id: int
    project_id: int
    language: str
    overlay_json: Optional[list] = None
    post_text: Optional[str] = None
    youtube_title: Optional[str] = None
    youtube_tags: Optional[str] = None

    model_config = {"from_attributes": True}


class ProjectOut(BaseModel):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    youtube_url: str
    artist: str
    work: str
    composer: str
    composition_year: str
    nationality: str
    nationality_flag: str
    voice_type: str
    birth_date: str
    death_date: str
    album_opera: str
    category: str
    hook: str
    hook_category: str
    highlights: str
    original_duration: str
    cut_start: str
    cut_end: str
    status: str
    overlay_json: Optional[list] = None
    post_text: Optional[str] = None
    youtube_title: Optional[str] = None
    youtube_tags: Optional[str] = None
    overlay_approved: bool
    post_approved: bool
    youtube_approved: bool
    translations: List[TranslationOut] = []

    model_config = {"from_attributes": True}


class RegenerateRequest(BaseModel):
    custom_prompt: Optional[str] = None


class ApproveOverlayRequest(BaseModel):
    overlay_json: list


class ApprovePostRequest(BaseModel):
    post_text: str


class ApproveYoutubeRequest(BaseModel):
    youtube_title: str
    youtube_tags: str
