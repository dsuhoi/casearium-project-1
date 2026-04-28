from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


TOKEN_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9]{3,}")


@dataclass(frozen=True)
class RagDocument:
    doc_id: str
    title: str
    tags: list[str]
    content: str
    source: str

    @property
    def text(self) -> str:
        return f"{self.title}\n{' '.join(self.tags)}\n{self.content}"


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text)}


class KnowledgeBase:
    def __init__(self, docs_dir: Path | str) -> None:
        self.docs_dir = Path(docs_dir)
        self.documents = self._load_documents()

    def search(self, query: str, limit: int = 4, tags_any: list[str] | None = None) -> list[dict]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        tags_filter = {tag.lower() for tag in tags_any or []}
        scored: list[tuple[float, RagDocument]] = []
        for doc in self.documents:
            tag_tokens = tokenize(" ".join(doc.tags))
            title_tokens = tokenize(doc.title)
            if tags_filter and not tags_filter.intersection({tag.lower() for tag in doc.tags}).union(tag_tokens):
                continue
            doc_tokens = tokenize(doc.text)
            overlap = query_tokens.intersection(doc_tokens)
            if not overlap:
                continue
            tag_bonus = len(overlap.intersection(tag_tokens)) * 0.4
            title_bonus = len(overlap.intersection(title_tokens)) * 0.25
            score = len(overlap) / max(len(query_tokens), 1) + tag_bonus
            score += title_bonus
            if any(token.startswith("комисс") for token in query_tokens) and any(token.startswith("комисс") for token in tag_tokens.union(title_tokens)):
                score += 1.0
            scored.append((score, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "doc_id": doc.doc_id,
                "title": doc.title,
                "tags": doc.tags,
                "content": doc.content[:900],
                "source": doc.source,
                "score": round(score, 3),
            }
            for score, doc in scored[:limit]
        ]

    def _load_documents(self) -> list[RagDocument]:
        documents: list[RagDocument] = []
        kb_file = self.docs_dir / "fintech_support_knowledge_base_rag.txt"
        if kb_file.exists():
            documents.extend(self._parse_kb(kb_file))

        complaints_file = self.docs_dir / "customer_complaints_200.txt"
        if complaints_file.exists():
            documents.extend(self._parse_complaints(complaints_file))

        return documents

    @staticmethod
    def _parse_kb(path: Path) -> list[RagDocument]:
        raw = path.read_text(encoding="utf-8")
        chunks = [chunk.strip() for chunk in raw.split("---") if "СТАТЬЯ" in chunk]
        docs: list[RagDocument] = []
        for chunk in chunks:
            number = re.search(r"СТАТЬЯ\s+(\d+)", chunk)
            tags = re.search(r"ТЕГИ:\s*(.+)", chunk)
            title = re.search(r"ТЕМА:\s*(.+)", chunk)
            content = re.search(r"СОДЕРЖАНИЕ:\s*([\s\S]+)", chunk)
            doc_id = f"article_{number.group(1)}" if number else f"article_{len(docs) + 1}"
            docs.append(
                RagDocument(
                    doc_id=doc_id,
                    title=title.group(1).strip() if title else doc_id,
                    tags=[tag.strip() for tag in tags.group(1).split(",")] if tags else [],
                    content=content.group(1).strip() if content else chunk,
                    source=path.name,
                )
            )
        return docs

    @staticmethod
    def _parse_complaints(path: Path) -> list[RagDocument]:
        raw = path.read_text(encoding="utf-8")
        chunks = [chunk.strip() for chunk in raw.split("---") if "ЖАЛОБА" in chunk]
        docs: list[RagDocument] = []
        for chunk in chunks:
            number = re.search(r"ЖАЛОБА\s+(\d+)", chunk)
            body = re.sub(r"^ЖАЛОБА\s+\d+", "", chunk).strip()
            doc_id = f"complaint_{number.group(1)}" if number else f"complaint_{len(docs) + 1}"
            docs.append(
                RagDocument(
                    doc_id=doc_id,
                    title=f"Синтетическая жалоба {number.group(1) if number else len(docs) + 1}",
                    tags=["complaint", "synthetic"],
                    content=body,
                    source=path.name,
                )
            )
        return docs
