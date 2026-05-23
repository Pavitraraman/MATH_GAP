import json
import logging
import math
import re
from collections import Counter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from google import genai

from app.core.config import settings
from app.models.learning_platform import Material, MaterialChunk

logger = logging.getLogger("math_gap.rag_service")


class RAGService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.client = genai.Client(api_key=settings.gemini_api_key) if settings.gemini_api_key else None

    async def get_embedding(self, text: str) -> list[float] | None:
        """Fetches vector embedding using Gemini's text-embedding-004 API."""
        if not self.client:
            return None
        try:
            # Under new google-genai, models.embed_content is correct
            response = await self.client.aio.models.embed_content(
                model="text-embedding-004",
                contents=text,
            )
            if response and response.embeddings:
                return response.embeddings[0].values
        except Exception as exc:
            logger.warning("Failed to generate embedding from Gemini: %s", exc)
        return None

    def _tokenize(self, text: str) -> list[str]:
        """Utility to tokenize and normalize text blocks."""
        return re.findall(r"\w+", text.lower())

    def _compute_keyword_similarity(self, query: str, document: str) -> float:
        """Fallback Cosine Similarity of Term Frequencies for lightweight offline RAG."""
        q_words = self._tokenize(query)
        doc_words = self._tokenize(document)
        if not q_words or not doc_words:
            return 0.0

        q_cnt = Counter(q_words)
        doc_cnt = Counter(doc_words)

        all_words = set(q_cnt.keys()).union(set(doc_cnt.keys()))
        dot_product = sum(q_cnt[w] * doc_cnt[w] for w in all_words)
        q_norm = math.sqrt(sum(v ** 2 for v in q_cnt.values()))
        doc_norm = math.sqrt(sum(v ** 2 for v in doc_cnt.values()))

        if not q_norm or not doc_norm:
            return 0.0
        return dot_product / (q_norm * doc_norm)

    async def search_relevant_context(self, student_id: str, query: str, limit: int = 3) -> list[dict]:
        """Retrieves most contextually matching chunks for a student's query using Dual-Mode RAG."""
        student_id = str(student_id)
        
        # 1. Fetch chunks belonging to the student's uploaded materials
        stmt = (
            select(MaterialChunk)
            .join(Material)
            .where(Material.student_id == student_id)
        )
        result = await self.db.scalars(stmt)
        chunks = list(result.all())

        if not chunks:
            return []

        # 2. Try Vector Cosine similarity first if embedding client and chunk embeddings exist
        query_vector = await self.get_embedding(query)
        scored_chunks = []

        if query_vector and any(c.embedding is not None for c in chunks):
            logger.info("Performing Semantic Vector RAG Search via Gemini Embeddings...")
            for c in chunks:
                if c.embedding:
                    # Compute dot product (since embedding-004 vectors are normalized, dot product is cosine similarity)
                    similarity = sum(q_v * c_v for q_v, c_v in zip(query_vector, c.embedding))
                    scored_chunks.append((c, similarity))
            scored_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # 3. Fallback to high-speed Term-Frequency Cosine similarity
        if not scored_chunks:
            logger.info("Performing Local High-Speed Keyword-Matching Cosine RAG Search...")
            for c in chunks:
                similarity = self._compute_compute_keyword_similarity(query, c.text) if hasattr(self, "_compute_compute_keyword_similarity") else self._compute_keyword_similarity(query, c.text)
                scored_chunks.append((c, similarity))
            scored_chunks.sort(key=lambda x: x[1], reverse=True)

        # 4. Format and return top matches
        top_matches = scored_chunks[:limit]
        return [
            {
                "chunk_id": item[0].id,
                "material_id": item[0].material_id,
                "text": item[0].text,
                "similarity_score": round(item[1], 4)
            }
            for item in top_matches
        ]
