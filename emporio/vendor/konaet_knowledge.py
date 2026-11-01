from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, Iterator


class KnowledgeError(ValueError):
    """Raised when a local knowledge source cannot be indexed safely."""


@dataclass(frozen=True, slots=True)
class KnowledgeHit:
    document_id: int
    title: str
    source_name: str
    page: int
    excerpt: str
    score: float

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "source_name": self.source_name,
            "page": self.page,
            "excerpt": self.excerpt,
            "score": self.score,
        }


@dataclass(frozen=True, slots=True)
class IndexedDocument:
    id: int
    title: str
    source_name: str
    source_sha256: str
    rights: str
    pages: int
    chunks: int
    imported_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "source_name": self.source_name,
            "source_sha256": self.source_sha256,
            "rights": self.rights,
            "pages": self.pages,
            "chunks": self.chunks,
            "imported_at": self.imported_at,
        }


_STOPWORDS = {
    "a",
    "ao",
    "aos",
    "as",
    "com",
    "como",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "esse",
    "esta",
    "este",
    "isso",
    "meu",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "para",
    "por",
    "que",
    "sobre",
    "um",
    "uma",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    text = re.sub(r"[\t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def chunk_page(text: str, max_chars: int = 1_200, overlap_chars: int = 180) -> list[str]:
    clean = _clean_text(text)
    if not clean:
        return []
    if max_chars < 200 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise KnowledgeError("configuração de fragmentação inválida")
    paragraphs = [part.strip() for part in re.split(r"\n{2,}", clean) if part.strip()]
    if len(paragraphs) == 1:
        paragraphs = [part.strip() for part in re.split(r"(?<=[.!?])\s+", clean) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            start = 0
            while start < len(paragraph):
                end = min(start + max_chars, len(paragraph))
                chunks.append(paragraph[start:end].strip())
                if end == len(paragraph):
                    break
                start = end - overlap_chars
            continue
        candidate = f"{current} {paragraph}".strip()
        if current and len(candidate) > max_chars:
            chunks.append(current)
            prefix = current[-overlap_chars:].lstrip() if overlap_chars else ""
            current = f"{prefix} {paragraph}".strip()
        else:
            current = candidate
    if current:
        chunks.append(current)
    return [chunk for chunk in chunks if chunk]


def _fts_terms(query: str) -> list[str]:
    terms = [
        term.casefold()
        for term in re.findall(r"[^\W_]{2,}", query, flags=re.UNICODE)
        if term.casefold() not in _STOPWORDS
    ]
    unique = list(dict.fromkeys(terms))[:12]
    if not unique:
        raise KnowledgeError("consulta sem termos pesquisáveis")
    return unique


def _fts_query(terms: list[str], operator: str = "AND") -> str:
    if operator not in {"AND", "OR"}:
        raise KnowledgeError("operador de busca inválido")
    return f" {operator} ".join(f'"{term}"*' for term in terms)


class KnowledgeBase:
    def __init__(self, database_path: Path):
        self.database_path = Path(database_path).resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS knowledge_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL UNIQUE,
                    rights TEXT NOT NULL,
                    pages INTEGER NOT NULL,
                    chunks INTEGER NOT NULL,
                    imported_at TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                    document_id UNINDEXED,
                    source_name UNINDEXED,
                    page UNINDEXED,
                    position UNINDEXED,
                    title,
                    content,
                    tokenize = 'unicode61 remove_diacritics 2'
                );
                """
            )

    def import_pages(
        self,
        *,
        title: str,
        source_name: str,
        source_sha256: str,
        rights: str,
        pages: Iterable[tuple[int, str]],
    ) -> IndexedDocument:
        title = title.strip()
        source_name = Path(source_name).name.strip()
        rights = rights.strip()
        if not title or not source_name or not rights:
            raise KnowledgeError("título, origem e direitos são obrigatórios")
        if not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
            raise KnowledgeError("SHA-256 da origem inválido")

        prepared: list[tuple[int, int, str]] = []
        page_count = 0
        for page, text in pages:
            if page < 1:
                raise KnowledgeError("número de página inválido")
            page_count = max(page_count, page)
            for position, content in enumerate(chunk_page(text), start=1):
                prepared.append((page, position, content))
        if not prepared:
            raise KnowledgeError("o documento não possui texto extraível")

        with self._connect() as connection:
            previous = connection.execute(
                "SELECT id FROM knowledge_documents WHERE source_sha256 = ?",
                (source_sha256,),
            ).fetchone()
            if previous:
                document_id = int(previous["id"])
                connection.execute(
                    "DELETE FROM knowledge_fts WHERE document_id = ?", (document_id,)
                )
                connection.execute(
                    """
                    UPDATE knowledge_documents
                    SET title = ?, source_name = ?, rights = ?, pages = ?, chunks = ?, imported_at = ?
                    WHERE id = ?
                    """,
                    (title, source_name, rights, page_count, len(prepared), _now(), document_id),
                )
            else:
                cursor = connection.execute(
                    """
                    INSERT INTO knowledge_documents(
                        title, source_name, source_sha256, rights, pages, chunks, imported_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (title, source_name, source_sha256, rights, page_count, len(prepared), _now()),
                )
                document_id = int(cursor.lastrowid)
            connection.executemany(
                """
                INSERT INTO knowledge_fts(
                    document_id, source_name, page, position, title, content
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (document_id, source_name, page, position, title, content)
                    for page, position, content in prepared
                ],
            )
        return self.get_document(document_id)

    def get_document(self, document_id: int) -> IndexedDocument:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM knowledge_documents WHERE id = ?", (document_id,)
            ).fetchone()
        if not row:
            raise KnowledgeError("documento indexado não encontrado")
        return IndexedDocument(**dict(row))

    def list_documents(self) -> list[IndexedDocument]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM knowledge_documents ORDER BY imported_at DESC"
            ).fetchall()
        return [IndexedDocument(**dict(row)) for row in rows]

    def search(self, query: str, limit: int = 5) -> list[KnowledgeHit]:
        terms = _fts_terms(query)
        safe_limit = min(max(int(limit), 1), 10)
        statement = """
                SELECT
                    CAST(document_id AS INTEGER) AS document_id,
                    title,
                    source_name,
                    CAST(page AS INTEGER) AS page,
                    snippet(knowledge_fts, 5, '', '', ' … ', 32) AS excerpt,
                    bm25(knowledge_fts, 0.0, 0.0, 0.0, 0.0, 3.0, 1.0) AS score
                FROM knowledge_fts
                WHERE knowledge_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """
        with self._connect() as connection:
            rows = connection.execute(
                statement, (_fts_query(terms, "AND"), safe_limit)
            ).fetchall()
            if not rows and len(terms) > 1:
                rows = connection.execute(
                    statement, (_fts_query(terms, "OR"), safe_limit)
                ).fetchall()
        return [KnowledgeHit(**dict(row)) for row in rows]
