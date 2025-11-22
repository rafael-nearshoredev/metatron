from __future__ import annotations

from pathlib import Path
from typing import Literal

ContextName = Literal["salesman", "lead", "product"]

_FILES_DIR = Path(__file__).resolve().parent.parent / "files"
_CONTEXT_FILES = {
    "salesman": _FILES_DIR / "salesman_context.txt",
    "lead": _FILES_DIR / "lead_context.txt",
    "product": _FILES_DIR / "product_context.txt",
}


def _resolve_context_path(context: ContextName) -> Path:
    try:
        return _CONTEXT_FILES[context]
    except KeyError as exc:
        raise ValueError(f"Unknown context name: {context}") from exc


def _read_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Context file not found: {path}")
    return path.read_text(encoding="utf-8")


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def read_context(context: ContextName) -> str:
    """Read the full contents of one of the context files."""
    return _read_file(_resolve_context_path(context))


def write_context(context: ContextName, content: str) -> None:
    """Persist content to the requested context file."""
    _write_file(_resolve_context_path(context), content)


def get_salesman_context() -> str:
    """Return the salesman context text."""
    return read_context("salesman")


def get_lead_context() -> str:
    """Return the lead context text."""
    return read_context("lead")


def get_product_context() -> str:
    """Return the product context text."""
    return read_context("product")


def set_salesman_context(content: str) -> None:
    """Overwrite the salesman context file."""
    write_context("salesman", content)


def set_lead_context(content: str) -> None:
    """Overwrite the lead context file."""
    write_context("lead", content)


def set_product_context(content: str) -> None:
    """Overwrite the product context file."""
    write_context("product", content)
