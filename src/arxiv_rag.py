#!/usr/bin/env python3
"""
Lightweight RAG over local markdown files (arxiv-abstracts/*.md).

Design goals:
- Works with existing project deps (stdlib + requests already in repo)
- Uses SQLite FTS5 BM25 for keyword retrieval (always available on most Python builds)
- Optionally adds semantic retrieval using OpenRouter embeddings (cached in SQLite)

Typical usage (from PostWorkflow):
    rag = ArxivAbstractRAG(project_root=PROJECT_ROOT, openrouter_api_key=OPENROUTER_API_KEY)
    rag.ensure_index()
    context, results = rag.retrieve(query="your query")
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _now_s() -> int:
    return int(time.time())


def _safe_fts_query(query: str) -> str:
    """
    Best-effort escape for FTS5 MATCH queries.
    We keep it simple: tokenize into words and join with OR.
    This avoids many syntax pitfalls with punctuation.
    """
    terms = re.findall(r"[A-Za-z0-9_]+", query or "")
    if not terms:
        return ""
    # OR is usually better for short keyword lists in abstracts.
    return " OR ".join(terms[:25])


def chunk_markdown_by_h2(content: str, filename: str) -> List[Dict]:
    """
    Chunk markdown by '## ' headers (keeps semantic sections together).
    If no sections, returns one chunk with the whole document.
    """
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    doc_title = title_match.group(1).strip() if title_match else filename

    sections = re.split(r"(?=^##\s+)", content, flags=re.MULTILINE)
    chunks: List[Dict] = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        section_title_match = re.search(r"^##\s+(.+)$", section, re.MULTILINE)
        section_title = (
            section_title_match.group(1).strip() if section_title_match else "Introduction"
        )

        chunk_content = f"[From: {filename}]\n# {doc_title}\n\n{section}".strip()
        chunks.append(
            {
                "content": chunk_content,
                "metadata": {
                    "source_file": filename,
                    "doc_title": doc_title,
                    "section_title": section_title,
                },
            }
        )

    if chunks:
        return chunks
    return [
        {
            "content": f"[From: {filename}]\n# {doc_title}\n\n{content}".strip(),
            "metadata": {"source_file": filename, "doc_title": doc_title, "section_title": "Full"},
        }
    ]


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = math.fsum(x * y for x, y in zip(a, b))
    na = math.sqrt(math.fsum(x * x for x in a))
    nb = math.sqrt(math.fsum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _pack_f32(vec: Sequence[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _unpack_f32(blob: bytes, dim: int) -> List[float]:
    if not blob or dim <= 0:
        return []
    return list(struct.unpack(f"{dim}f", blob))


@dataclass
class RAGHit:
    chunk_id: int
    source_file: str
    section_title: str
    content: str
    bm25_score: float = 0.0
    semantic_score: float = 0.0
    final_score: float = 0.0


class ArxivAbstractRAG:
    """
    RAG retriever over local `arxiv-abstracts/*.md`.

    - Always: keyword BM25 via SQLite FTS5.
    - Optional: semantic via OpenRouter embeddings (cached).
    """

    def __init__(
        self,
        project_root: Path,
        docs_dir: Optional[Path] = None,
        db_path: Optional[Path] = None,
        openrouter_api_key: Optional[str] = None,
        enable_semantic: bool = False,
        embedding_model: str = "openai/text-embedding-3-small",
        keyword_weight: float = 0.6,
        semantic_weight: float = 0.4,
    ) -> None:
        self.project_root = Path(project_root)
        self.docs_dir = Path(docs_dir) if docs_dir else (self.project_root / "arxiv-abstracts")

        rag_dir = self.project_root / ".rag"
        self.db_path = Path(db_path) if db_path else (rag_dir / "arxiv_abstracts_rag.sqlite3")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.openrouter_api_key = openrouter_api_key
        self.enable_semantic = bool(enable_semantic)
        self.embedding_model = embedding_model
        self.keyword_weight = float(keyword_weight)
        self.semantic_weight = float(semantic_weight)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def ensure_index(self) -> None:
        """
        Ensure tables exist and docs are indexed.
        Safe to call repeatedly.
        """
        if not self.docs_dir.exists():
            return

        with self._connect() as conn:
            cur = conn.cursor()

            # Core chunk storage
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file TEXT NOT NULL,
                    section_title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    indexed_at INTEGER NOT NULL
                )
                """
            )

            # Source tracking for incremental indexing
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_sources (
                    source_file TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    indexed_at INTEGER NOT NULL
                )
                """
            )

            # FTS5 index (BM25)
            cur.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks_fts USING fts5(
                    content,
                    source_file,
                    section_title,
                    content='rag_chunks',
                    content_rowid='id'
                )
                """
            )

            # Keep FTS in sync
            cur.execute(
                """
                CREATE TRIGGER IF NOT EXISTS rag_chunks_ai AFTER INSERT ON rag_chunks BEGIN
                    INSERT INTO rag_chunks_fts(rowid, content, source_file, section_title)
                    VALUES (new.id, new.content, new.source_file, new.section_title);
                END
                """
            )
            cur.execute(
                """
                CREATE TRIGGER IF NOT EXISTS rag_chunks_ad AFTER DELETE ON rag_chunks BEGIN
                    INSERT INTO rag_chunks_fts(rag_chunks_fts, rowid, content, source_file, section_title)
                    VALUES ('delete', old.id, old.content, old.source_file, old.section_title);
                END
                """
            )

            # Optional semantic cache
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_embeddings (
                    chunk_id INTEGER PRIMARY KEY,
                    model TEXT NOT NULL,
                    dim INTEGER NOT NULL,
                    embedding BLOB NOT NULL,
                    content_hash TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )

            conn.commit()

        self._index_docs_incremental()

        # Only precompute embeddings if explicitly enabled
        if self.enable_semantic:
            self._ensure_embeddings_cached()

    def _index_docs_incremental(self) -> None:
        md_files = sorted(self.docs_dir.glob("*.md"))
        if not md_files:
            return

        with self._connect() as conn:
            cur = conn.cursor()

            for md_path in md_files:
                try:
                    text = md_path.read_text(encoding="utf-8")
                except Exception:
                    # Skip unreadable files
                    continue

                file_hash = _sha256_text(text)
                row = cur.execute(
                    "SELECT file_hash FROM rag_sources WHERE source_file = ?",
                    (md_path.name,),
                ).fetchone()
                if row and row["file_hash"] == file_hash:
                    continue  # unchanged

                # Re-index by deleting old chunks for that file then inserting fresh.
                cur.execute("DELETE FROM rag_chunks WHERE source_file = ?", (md_path.name,))

                chunks = chunk_markdown_by_h2(text, md_path.name)
                indexed_at = _now_s()
                for ch in chunks:
                    content = ch["content"]
                    meta = ch.get("metadata") or {}
                    section_title = str(meta.get("section_title") or "Section")
                    content_hash = _sha256_text(content)
                    cur.execute(
                        """
                        INSERT INTO rag_chunks (source_file, section_title, content, content_hash, indexed_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (md_path.name, section_title, content, content_hash, indexed_at),
                    )

                cur.execute(
                    """
                    INSERT INTO rag_sources (source_file, file_hash, indexed_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(source_file) DO UPDATE SET
                        file_hash=excluded.file_hash,
                        indexed_at=excluded.indexed_at
                    """,
                    (md_path.name, file_hash, indexed_at),
                )

            conn.commit()

    def _openrouter_embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if requests is None:
            raise RuntimeError("requests is required for OpenRouter embeddings")
        if not self.openrouter_api_key:
            raise RuntimeError("OpenRouter API key missing (needed for embeddings)")

        resp = requests.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/dailytoparxiv/post_generation",
                "X-Title": "Post Generation Tool",
            },
            json={"model": self.embedding_model, "input": texts},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        # OpenAI-compatible: {"data":[{"embedding":[...], "index":0}, ...]}
        items = data.get("data") or []
        out: List[List[float]] = []
        for item in items:
            emb = item.get("embedding") or []
            out.append([float(x) for x in emb])
        return out

    def _ensure_embeddings_cached(self, batch_size: int = 64) -> None:
        """
        Ensure we have cached embeddings for all chunks (for current model + content_hash).
        Safe to call repeatedly; only embeds missing/outdated chunks.
        """
        if not self.enable_semantic:
            return
        if not self.openrouter_api_key:
            # Semantic mode requested but no key available; silently skip.
            return

        with self._connect() as conn:
            cur = conn.cursor()
            rows = cur.execute(
                """
                SELECT c.id, c.content, c.content_hash
                FROM rag_chunks c
                LEFT JOIN rag_embeddings e
                  ON e.chunk_id = c.id AND e.model = ?
                WHERE e.chunk_id IS NULL OR e.content_hash != c.content_hash
                """,
                (self.embedding_model,),
            ).fetchall()

            if not rows:
                return

            pending: List[Tuple[int, str, str]] = [
                (int(r["id"]), str(r["content"]), str(r["content_hash"])) for r in rows
            ]

            for i in range(0, len(pending), batch_size):
                batch = pending[i : i + batch_size]
                texts = [b[1] for b in batch]
                try:
                    embeddings = self._openrouter_embed(texts)
                except Exception:
                    # If embeddings fail (model unsupported, quota, etc.), don't break workflow.
                    return

                created_at = _now_s()
                for (chunk_id, _content, content_hash), emb in zip(batch, embeddings):
                    dim = len(emb)
                    if dim <= 0:
                        continue
                    blob = _pack_f32(emb)
                    cur.execute(
                        """
                        INSERT INTO rag_embeddings (chunk_id, model, dim, embedding, content_hash, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(chunk_id) DO UPDATE SET
                            model=excluded.model,
                            dim=excluded.dim,
                            embedding=excluded.embedding,
                            content_hash=excluded.content_hash,
                            created_at=excluded.created_at
                        """,
                        (chunk_id, self.embedding_model, dim, blob, content_hash, created_at),
                    )

            conn.commit()

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 8,
        max_chars: int = 4000,
        bm25_limit: int = 100,
        semantic_limit: int = 100,
    ) -> Tuple[str, List[RAGHit]]:
        """
        Retrieve relevant chunks and return formatted prompt context + structured hits.
        """
        query = (query or "").strip()
        if not query:
            return "", []

        if not self.db_path.exists():
            self.ensure_index()

        bm25_hits: Dict[int, float] = {}
        semantic_hits: Dict[int, float] = {}

        with self._connect() as conn:
            cur = conn.cursor()

            # BM25 keyword search
            safe_query = _safe_fts_query(query)
            if safe_query:
                try:
                    rows = cur.execute(
                        """
                        SELECT rowid, bm25(rag_chunks_fts) AS score
                        FROM rag_chunks_fts
                        WHERE rag_chunks_fts MATCH ?
                        LIMIT ?
                        """,
                        (safe_query, bm25_limit),
                    ).fetchall()
                    bm25_hits = {int(r["rowid"]): float(r["score"]) for r in rows}
                except sqlite3.OperationalError:
                    bm25_hits = {}

            # Optional semantic search
            if self.enable_semantic and self.openrouter_api_key:
                # Lazily ensure embeddings exist.
                self._ensure_embeddings_cached()
                try:
                    q_emb = self._openrouter_embed([query])[0]
                except Exception:
                    q_emb = []

                if q_emb:
                    # Compute cosine sim against cached embeddings (small corpus -> OK in Python).
                    emb_rows = cur.execute(
                        """
                        SELECT e.chunk_id, e.dim, e.embedding
                        FROM rag_embeddings e
                        WHERE e.model = ?
                        """,
                        (self.embedding_model,),
                    ).fetchall()

                    scored: List[Tuple[int, float]] = []
                    for r in emb_rows:
                        dim = int(r["dim"])
                        vec = _unpack_f32(r["embedding"], dim)
                        sim = _cosine_similarity(q_emb, vec)
                        scored.append((int(r["chunk_id"]), float(sim)))

                    scored.sort(key=lambda x: x[1], reverse=True)
                    semantic_hits = dict(scored[:semantic_limit])

            # Merge candidates
            candidate_ids = set(bm25_hits.keys()) | set(semantic_hits.keys())
            if not candidate_ids:
                return "", []

            # Fetch chunk content
            placeholders = ",".join(["?"] * len(candidate_ids))
            chunk_rows = cur.execute(
                f"""
                SELECT id, source_file, section_title, content
                FROM rag_chunks
                WHERE id IN ({placeholders})
                """,
                list(candidate_ids),
            ).fetchall()

        # Normalize scores
        bm25_norm = self._normalize_bm25(bm25_hits)
        sem_norm = self._normalize_01(semantic_hits)

        hits: List[RAGHit] = []
        for r in chunk_rows:
            cid = int(r["id"])
            b = float(bm25_norm.get(cid, 0.0))
            s = float(sem_norm.get(cid, 0.0))
            # If semantic is disabled/unavailable, fall back to pure keyword.
            if not sem_norm:
                final = b
            elif not bm25_norm:
                final = s
            else:
                final = (self.keyword_weight * b) + (self.semantic_weight * s)

            hits.append(
                RAGHit(
                    chunk_id=cid,
                    source_file=str(r["source_file"]),
                    section_title=str(r["section_title"]),
                    content=str(r["content"]),
                    bm25_score=b,
                    semantic_score=s,
                    final_score=float(final),
                )
            )

        hits.sort(key=lambda h: h.final_score, reverse=True)
        hits = hits[:top_k]

        context = self.format_context(hits, max_chars=max_chars)
        return context, hits

    @staticmethod
    def _normalize_bm25(scores: Dict[int, float]) -> Dict[int, float]:
        """
        FTS5 bm25() returns negative numbers (more negative = better).
        Convert to [0, 1] where 1 is best.
        """
        if not scores:
            return {}
        vals = list(scores.values())
        mn = min(vals)  # most negative (best)
        mx = max(vals)  # least negative (worst)
        if mn == mx:
            return {k: 1.0 for k in scores}
        rng = mx - mn
        return {k: (mx - v) / rng for k, v in scores.items()}

    @staticmethod
    def _normalize_01(scores: Dict[int, float]) -> Dict[int, float]:
        if not scores:
            return {}
        vals = list(scores.values())
        mn = min(vals)
        mx = max(vals)
        if mn == mx:
            return {k: 1.0 for k in scores}
        rng = mx - mn
        return {k: (v - mn) / rng for k, v in scores.items()}

    @staticmethod
    def format_context(hits: Sequence[RAGHit], max_chars: int = 4000) -> str:
        if not hits:
            return ""

        parts: List[str] = []
        used = 0
        for i, h in enumerate(hits, 1):
            header = f"[{i}] {h.source_file} :: {h.section_title} (score={h.final_score:.2f})"
            body = h.content.strip()

            avail = max_chars - used - len(header) - 5
            if avail <= 200:
                break
            if len(body) > avail:
                body = body[: avail - 3] + "..."

            entry = f"{header}\n{body}\n"
            parts.append(entry)
            used += len(entry)

        return "\n".join(parts).strip()

