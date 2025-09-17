from __future__ import annotations
from pathlib import Path
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
import json


class Artifact(BaseModel):
    artifact_id: str
    type: Literal["picture", "table"]
    ref_item: str                     # e.g., "#/table/0"
    file_ref: str                     # relative path to PNG
    caption: Optional[str] = None
    page_number: Optional[int] = None


class Chunk(BaseModel):
    chunk_id: str
    text: str
    page_number: Optional[int] = None
    headings: List[str] = Field(default_factory=list)
    ref_items: List[str] = Field(default_factory=list)  # links to artifacts


class FileInfo(BaseModel):
    filename: str
    size: Optional[int] = None
    format: str                       # e.g., "pdf", "docx"
    hash: str


class DocumentMetadata(BaseModel):
    page_count: int
    conversion_date: str              # ISO string
    pipeline_options: dict = Field(default_factory=dict)


class ConvertedDocument(BaseModel):
    doc_id: str
    file_info: FileInfo
    metadata: DocumentMetadata
    chunks: List[Chunk] = Field(default_factory=list)
    artifacts: List[Artifact] = Field(default_factory=list)

    # ---- Helpers ----
    def get_images(self) -> List[Artifact]:
        return [a for a in self.artifacts if a.type == "picture"]

    def get_tables(self) -> List[Artifact]:
        return [a for a in self.artifacts if a.type == "table"]

    # ---- Persistence ----
    def save_json(self, path: Path) -> None:
        """Save document.json"""
        path.write_text(self.model_dump_json(indent=2))

    @classmethod
    def load_json(cls, path: Path) -> ConvertedDocument:
        """Load from document.json"""
        data = json.loads(path.read_text())
        return cls.model_validate(data)
