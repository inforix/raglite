from typing import List, Tuple


def sliding_window(text: str, chunk_size: int = 512, overlap: int = 128) -> List[Tuple[int, int, str]]:
    """
    Token-based sliding window using whitespace tokens. Returns char offsets for provenance.
    """
    tokens = text.split()
    chunks: List[Tuple[int, int, str]] = []
    start_idx = 0
    while start_idx < len(tokens):
        end_idx = min(start_idx + chunk_size, len(tokens))
        chunk_tokens = tokens[start_idx:end_idx]
        chunk_text = " ".join(chunk_tokens)
        # approximate char offsets by re-finding substring
        if chunk_text:
            char_start = text.find(chunk_tokens[0], 0 if not chunks else chunks[-1][1])
            char_end = char_start + len(chunk_text)
        else:
            char_start = 0
            char_end = 0
        chunks.append((char_start, char_end, chunk_text))
        if end_idx == len(tokens):
            break
        start_idx = max(end_idx - overlap, 0)
    return chunks
