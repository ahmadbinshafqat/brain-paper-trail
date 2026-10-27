from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_type: str = Field(index=True)
    title: str = Field(default="Untitled")
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    sentences: list["Sentence"] = Relationship(back_populates="document")


class Sentence(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id", index=True)
    text: str
    score: float = Field(index=True)
    position: int
    is_selected: bool = Field(default=False, index=True)

    document: Optional[Document] = Relationship(back_populates="sentences")
