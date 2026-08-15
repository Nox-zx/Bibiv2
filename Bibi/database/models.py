from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.engine import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discord_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ChannelState(Base):
    __tablename__ = "channel_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(Integer, index=True)
    channel_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    attention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MessageRecord(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discord_message_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    guild_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    channel_id: Mapped[int] = mapped_column(Integer, index=True)
    author_discord_id: Mapped[int] = mapped_column(Integer, index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
    is_reply: Mapped[bool] = mapped_column(Boolean, default=False)
    mentioned_bibi: Mapped[bool] = mapped_column(Boolean, default=False)


class Experience(Base):
    __tablename__ = "experiences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    channel_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    summary: Mapped[str] = mapped_column(Text)
    significance: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_discord_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    guild_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    channel_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    scope: Mapped[str] = mapped_column(String(30), index=True)
    content: Mapped[str] = mapped_column(Text)
    importance: Mapped[str] = mapped_column(String(20), default="normal", index=True)
    confidence: Mapped[str] = mapped_column(String(20), default="medium")
    source: Mapped[str] = mapped_column(String(30), default="conversation")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    last_recalled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Relationship(Base):
    __tablename__ = "relationships"
    __table_args__ = (UniqueConstraint("guild_id", "user_discord_id", name="uq_relationship_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(Integer, index=True)
    user_discord_id: Mapped[int] = mapped_column(Integer, index=True)
    familiarity: Mapped[float] = mapped_column(Float, default=0.0)
    trust: Mapped[float] = mapped_column(Float, default=0.0)
    closeness: Mapped[float] = mapped_column(Float, default=0.0)
    impression: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class SelfModel(Base):
    __tablename__ = "self_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    base_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    evolved_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class DiaryEntry(Base):
    __tablename__ = "diary_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    summary: Mapped[str] = mapped_column(Text)
    significance: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
