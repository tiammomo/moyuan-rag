"""
Text splitting utilities for RAG ingestion.
"""

import re
from typing import Dict, List, Optional

from app.core.config import settings


DEFAULT_SEPARATORS = [
    "\n\n",
    "\n",
    "\u3002",
    "\uff01",
    "\uff1f",
    "\uff1b",
    " ",
    "",
]

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")
PAGE_MARKER_PATTERN = re.compile(r"^<<<PAGE:(\d+)>>>$")


class RecursiveCharacterTextSplitter:
    """
    Lightweight recursive character text splitter.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None,
        length_function=len,
        is_separator_regex: bool = False,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.length_function = length_function
        self.separators = separators or DEFAULT_SEPARATORS
        self.is_separator_regex = is_separator_regex

    def split_text(self, text: str) -> List[str]:
        """
        Split text into plain string chunks.
        """
        separator = self.separators[-1]
        next_separators: List[str] = []

        for index, candidate in enumerate(self.separators):
            if self._is_separator_present(text, candidate):
                separator = candidate
                next_separators = self.separators[index + 1 :]
                break

        splits = self._split_text_with_separator(text, separator)
        good_splits: List[str] = []

        for split in splits:
            if self.length_function(split) < self.chunk_size:
                good_splits.append(split)
                continue

            if next_separators:
                child_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                    separators=next_separators,
                    length_function=self.length_function,
                    is_separator_regex=self.is_separator_regex,
                )
                good_splits.extend(child_splitter.split_text(split))
            else:
                good_splits.append(split)

        return self._merge_splits(good_splits, separator)

    def _is_separator_present(self, text: str, separator: str) -> bool:
        if self.is_separator_regex:
            return bool(re.search(separator, text))
        return separator in text

    def _split_text_with_separator(self, text: str, separator: str) -> List[str]:
        if self.is_separator_regex:
            return re.split(separator, text)
        if separator:
            return text.split(separator)
        return list(text)

    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        final_chunks: List[str] = []
        current_chunk: List[str] = []
        current_length = 0
        separator_len = self.length_function(separator) if separator else 0

        for split in splits:
            if not split:
                continue

            split_len = self.length_function(split)
            projected_len = current_length + split_len + (separator_len if current_chunk else 0)
            if projected_len > self.chunk_size and current_chunk:
                final_chunks.append(self._join_docs(current_chunk, separator))
                current_chunk, current_length = self._build_overlap_window(current_chunk, separator)

            current_chunk.append(split)
            current_length += split_len + (separator_len if len(current_chunk) > 1 else 0)

        if current_chunk:
            final_chunks.append(self._join_docs(current_chunk, separator))

        return final_chunks

    def _build_overlap_window(self, current_chunk: List[str], separator: str) -> tuple[List[str], int]:
        if self.chunk_overlap <= 0:
            return [], 0

        separator_len = self.length_function(separator) if separator else 0
        overlap_chunk: List[str] = []
        overlap_length = 0

        for item in reversed(current_chunk):
            item_len = self.length_function(item)
            item_cost = item_len + (separator_len if overlap_chunk else 0)
            overlap_chunk.insert(0, item)
            overlap_length += item_cost
            if overlap_length >= self.chunk_overlap:
                break

        return overlap_chunk, overlap_length

    def _join_docs(self, docs: List[str], separator: str) -> str:
        return separator.join(docs).strip()


class TextSplitter:
    """
    Structured text splitter that preserves lightweight metadata.
    """

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.DEFAULT_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.DEFAULT_CHUNK_OVERLAP
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=DEFAULT_SEPARATORS,
            length_function=len,
        )
        self.block_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=0,
            separators=DEFAULT_SEPARATORS,
            length_function=len,
        )

    def split_text(self, text: str) -> List[str]:
        return self.splitter.split_text(text)

    def split_documents(self, text: str) -> List[dict]:
        logical_blocks = self._extract_logical_blocks(text)
        normalized_blocks = self._normalize_blocks(logical_blocks)
        documents = self._merge_blocks(normalized_blocks)

        for index, document in enumerate(documents):
            document["chunk_index"] = index

        return documents

    def _extract_logical_blocks(self, text: str) -> List[Dict[str, Optional[str]]]:
        blocks: List[Dict[str, Optional[str]]] = []
        current_lines: List[str] = []
        current_page: Optional[int] = None
        current_heading = ""
        heading_stack: List[str] = []
        block_heading = ""

        def flush_block() -> None:
            nonlocal current_lines, block_heading
            content = "\n".join(current_lines).strip()
            if content:
                blocks.append(
                    {
                        "content": content,
                        "page_number": current_page,
                        "heading": block_heading or current_heading,
                    }
                )
            current_lines = []
            block_heading = current_heading

        for raw_line in text.splitlines():
            stripped = raw_line.strip()

            if not stripped:
                flush_block()
                continue

            page_match = PAGE_MARKER_PATTERN.match(stripped)
            if page_match:
                flush_block()
                current_page = int(page_match.group(1))
                continue

            heading_match = HEADING_PATTERN.match(stripped)
            if heading_match:
                flush_block()
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()
                heading_stack = heading_stack[: level - 1]
                heading_stack.append(heading_text)
                current_heading = " > ".join(heading_stack)
                block_heading = current_heading
                current_lines = [stripped]
                continue

            if not current_lines:
                block_heading = current_heading
            current_lines.append(raw_line.rstrip())

        flush_block()
        return blocks

    def _normalize_blocks(self, blocks: List[Dict[str, Optional[str]]]) -> List[Dict[str, Optional[str]]]:
        normalized: List[Dict[str, Optional[str]]] = []

        for block in blocks:
            content = (block.get("content") or "").strip()
            if not content:
                continue

            if len(content) <= self.chunk_size:
                normalized.append(dict(block))
                continue

            for part in self.block_splitter.split_text(content):
                normalized.append(
                    {
                        "content": part,
                        "page_number": block.get("page_number"),
                        "heading": block.get("heading"),
                    }
                )

        return normalized

    def _merge_blocks(self, blocks: List[Dict[str, Optional[str]]]) -> List[dict]:
        documents: List[dict] = []
        current_blocks: List[Dict[str, Optional[str]]] = []

        for block in blocks:
            candidate_blocks = current_blocks + [block]
            candidate_content = self._join_block_contents(candidate_blocks)

            if current_blocks and len(candidate_content) > self.chunk_size:
                documents.append(self._build_document(current_blocks))
                current_blocks = self._build_overlap_blocks(current_blocks)

                candidate_blocks = current_blocks + [block]
                candidate_content = self._join_block_contents(candidate_blocks)
                if current_blocks and len(candidate_content) > self.chunk_size:
                    current_blocks = []

            current_blocks.append(block)

        if current_blocks:
            documents.append(self._build_document(current_blocks))

        return documents

    def _build_overlap_blocks(self, blocks: List[Dict[str, Optional[str]]]) -> List[Dict[str, Optional[str]]]:
        if self.chunk_overlap <= 0:
            return []

        overlap_blocks: List[Dict[str, Optional[str]]] = []
        overlap_length = 0

        for block in reversed(blocks):
            content = (block.get("content") or "").strip()
            if not content:
                continue

            overlap_blocks.insert(0, dict(block))
            overlap_length = len(self._join_block_contents(overlap_blocks))
            if overlap_length >= self.chunk_overlap:
                break

        return overlap_blocks

    def _build_document(self, blocks: List[Dict[str, Optional[str]]]) -> dict:
        content = self._join_block_contents(blocks)
        page_number = next(
            (block.get("page_number") for block in blocks if block.get("page_number") is not None),
            None,
        )
        heading = next((block.get("heading") for block in blocks if block.get("heading")), "")

        metadata = {}
        if page_number is not None:
            metadata["page_number"] = page_number
        if heading:
            metadata["heading"] = heading

        return {
            "content": content,
            "char_count": len(content),
            "metadata": metadata,
        }

    def _join_block_contents(self, blocks: List[Dict[str, Optional[str]]]) -> str:
        return "\n\n".join(
            (block.get("content") or "").strip()
            for block in blocks
            if (block.get("content") or "").strip()
        ).strip()


text_splitter = TextSplitter()
