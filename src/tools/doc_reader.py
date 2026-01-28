from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, Optional


def _truncate(text: str, max_chars: Optional[int]) -> str:
    if not max_chars or max_chars <= 0:
        return text
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[TRUNCATED]"


def _read_docx(path: str) -> str:
    try:
        from docx import Document  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "Missing dependency 'python-docx'. Install it with: pip install python-docx"
        ) from exc

    doc = Document(path)
    parts = []
    for p in doc.paragraphs:
        if p.text:
            parts.append(p.text)
    return "\n".join(parts).strip()


def _read_doc_via_antiword(path: str) -> str:
    # antiword outputs text to stdout
    try:
        proc = subprocess.run(
            ["antiword", path],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Reading .doc requires 'antiword' on your system. "
            "Install it (macOS: brew install antiword), or convert the file to .docx."
        ) from exc

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(f"antiword failed (code={proc.returncode}): {stderr}")
    return (proc.stdout or "").strip()


def read_doc_tool(args: Dict[str, Any]) -> str:
    """
    Tool: read_doc
    Read a Microsoft Word document (.doc or .docx) and return extracted plain text.

    Args:
      - path: string, required. File path to .doc/.docx
      - max_chars: int, optional. Truncate output to at most this many chars.
    """
    path = args.get("path") or args.get("file_path") or args.get("input")
    if not path:
        return "Error: missing 'path'"

    path = os.path.expanduser(str(path))
    if not os.path.isfile(path):
        return f"Error: file not found: {path}"

    max_chars = args.get("max_chars")
    try:
        max_chars_int = int(max_chars) if max_chars is not None else None
    except Exception:
        max_chars_int = None

    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".docx":
            text = _read_docx(path)
        elif ext == ".doc":
            text = _read_doc_via_antiword(path)
        else:
            return "Error: unsupported file type (expected .doc or .docx)"
    except Exception as exc:
        return f"Error: {exc}"

    if not text:
        return ""
    return _truncate(text, max_chars_int)

