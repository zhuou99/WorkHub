"""翻译术语表。"""

from __future__ import annotations

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import EntityBaseMixin


class WhGlossary(EntityBaseMixin, Base):
    """源词与约定译法。"""

    __tablename__ = "wh_glossary"

    Term: Mapped[str] = mapped_column("Term", Text, nullable=False)
    Translation: Mapped[str] = mapped_column("Translation", Text, nullable=False)
    Lang: Mapped[str] = mapped_column("Lang", Text, nullable=False)
    Note: Mapped[str | None] = mapped_column("Note", Text, nullable=True)
