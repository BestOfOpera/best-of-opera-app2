from __future__ import annotations
import datetime
from typing import Optional
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    # Project info
    artist: Mapped[str] = mapped_column(String(255))
    work: Mapped[str] = mapped_column(String(255))
    composer: Mapped[str] = mapped_column(String(255))
    composition_year: Mapped[str] = mapped_column(String(50), default="")
    nationality: Mapped[str] = mapped_column(String(100), default="")
    nationality_flag: Mapped[str] = mapped_column(String(10), default="")
    voice_type: Mapped[str] = mapped_column(String(100), default="")
    birth_date: Mapped[str] = mapped_column(String(50), default="")
    death_date: Mapped[str] = mapped_column(String(50), default="")
    album_opera: Mapped[str] = mapped_column(String(255), default="")
    category: Mapped[str] = mapped_column(String(100), default="")
    hook: Mapped[str] = mapped_column(Text, default="")
    highlights: Mapped[str] = mapped_column(Text, default="")
    original_duration: Mapped[str] = mapped_column(String(20), default="")
    cut_start: Mapped[str] = mapped_column(String(20), default="")
    cut_end: Mapped[str] = mapped_column(String(20), default="")

    # Status machine
    status: Mapped[str] = mapped_column(
        String(50), default="input_complete"
    )  # input_complete | generating | awaiting_approval | translating | export_ready

    # Generated content
    overlay_json: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    post_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    youtube_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    youtube_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Approval flags
    overlay_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    post_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    youtube_approved: Mapped[bool] = mapped_column(Boolean, default=False)

    translations: Mapped[list["Translation"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class Translation(Base):
    __tablename__ = "translations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    language: Mapped[str] = mapped_column(String(10))  # pt, es, de, fr, it, pl

    overlay_json: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    post_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    youtube_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    youtube_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="translations")
