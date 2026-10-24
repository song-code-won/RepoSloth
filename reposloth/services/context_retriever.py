"""Context retriever service for chunking source files and retrieving relevant snippets for Q&A."""

from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
from reposloth.services.secret_filter import SecretFilter

# Maximum chunk size in lines and chars
CHUNK_SIZE_LINES = 60
CHUNK_OVERLAP_LINES = 10
MAX_SNIPPET_RESULTS = 5


class ContextRetriever:
    """Local, lightweight TF/IDF and keyword relevance retrieval for repository source files."""

    def __init__(self, repo_path: str | Path, file_list: List[str]):
        self.repo_path = Path(repo_path)
        self.file_list = file_list
        self._chunks: List[Dict[str, Any]] = []
        self._build_index()

    def _build_index(self):
        """Indexes source files into search chunks with line number ranges."""
        for rel_file in self.file_list:
            abs_path = self.repo_path / rel_file
            if not abs_path.is_file():
                continue

            try:
                content = abs_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # Sanitize content against secrets before chunking
            content, _ = SecretFilter.sanitize_text(content)
            lines = content.splitlines()
            if not lines:
                continue

            # Slide window
            total = len(lines)
            idx = 0
            while idx < total:
                end_idx = min(idx + CHUNK_SIZE_LINES, total)
                chunk_lines = lines[idx:end_idx]
                chunk_text = "\n".join(chunk_lines)

                # Tokenize for search
                tokens = set(re.findall(r'[a-zA-Z0-9_]{3,}', chunk_text.lower()))

                self._chunks.append({
                    "file": rel_file,
                    "start_line": idx + 1,
                    "end_line": end_idx,
                    "text": chunk_text,
                    "tokens": tokens
                })

                if end_idx >= total:
                    break
                idx += (CHUNK_SIZE_LINES - CHUNK_OVERLAP_LINES)

    def retrieve(self, query: str, top_k: int = MAX_SNIPPET_RESULTS) -> List[Dict[str, Any]]:
        """
        Retrieves top relevant code chunks based on query keywords,
        exact phrase matches, and file name relevance.
        """
        query_lower = query.lower()
        query_terms = set(re.findall(r'[a-zA-Z0-9_]{3,}', query_lower))

        if not query_terms:
            return []

        scored_chunks: List[Tuple[float, Dict[str, Any]]] = []

        for chunk in self._chunks:
            score = 0.0
            chunk_text_lower = chunk["text"].lower()

            # Exact query or multi-word phrase bonus
            if len(query_terms) > 1 and query_lower in chunk_text_lower:
                score += 10.0

            # Token overlap score
            matched_tokens = query_terms.intersection(chunk["tokens"])
            score += len(matched_tokens) * 2.0

            # File name relevance bonus
            file_name_lower = chunk["file"].lower()
            for term in query_terms:
                if term in file_name_lower:
                    score += 4.0

            # Important code pattern bonus (functions, classes, endpoints)
            for term in query_terms:
                if f"def {term}" in chunk_text_lower or f"class {term}" in chunk_text_lower:
                    score += 6.0
                if f"function {term}" in chunk_text_lower or f"const {term}" in chunk_text_lower:
                    score += 5.0
                if f"/{term}" in chunk_text_lower or f"'{term}'" in chunk_text_lower or f'"{term}"' in chunk_text_lower:
                    score += 3.0

            if score > 0:
                scored_chunks.append((score, chunk))

        # Sort descending by score
        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, chunk in scored_chunks[:top_k]:
            results.append({
                "file": chunk["file"],
                "start_line": chunk["start_line"],
                "end_line": chunk["end_line"],
                "text": chunk["text"],
                "score": round(score, 2)
            })

        return results
