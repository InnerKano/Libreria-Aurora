from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from .vector_store import VectorStoreUnavailable, get_chroma_collection


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    k: int
    source: str  # 'vector' | 'orm'
    degraded: bool
    results: list[dict[str, Any]]
    warnings: list[str]


def _clean_query(query: Optional[str]) -> str:
    return (query or "").strip()


def _search_vector(query: str, k: int) -> list[dict[str, Any]]:
    collection = get_chroma_collection()
    resp = collection.query(
        query_texts=[query],
        n_results=k,
        include=["documents", "metadatas", "distances", "ids"],
    )

    ids = (resp.get("ids") or [[]])[0]
    documents = (resp.get("documents") or [[]])[0]
    metadatas = (resp.get("metadatas") or [[]])[0]
    distances = (resp.get("distances") or [[]])[0]

    out: list[dict[str, Any]] = []
    for idx in range(len(ids)):
        out.append(
            {
                "id": ids[idx] if idx < len(ids) else None,
                "document": documents[idx] if idx < len(documents) else None,
                "metadata": metadatas[idx] if idx < len(metadatas) else None,
                # Chroma reports distance; smaller usually means more similar.
                "distance": distances[idx] if idx < len(distances) else None,
            }
        )
    return out


def _search_orm(query: str, k: int) -> list[dict[str, Any]]:
    # Lazy import so agent retrieval remains usable in unit tests without Django setup.
    from django.db.models import Q

    from apps.libros.models import Libro

    qs = (
        Libro.objects.all()
        .filter(
            Q(titulo__icontains=query)
            | Q(autor__icontains=query)
            | Q(isbn__icontains=query)
            | Q(descripcion__icontains=query)
            | Q(editorial__icontains=query)
        )
        .order_by("titulo")
    )

    results: list[dict[str, Any]] = []
    for libro in qs[:k]:
        results.append(
            {
                "libro_id": libro.id,
                "titulo": libro.titulo,
                "autor": libro.autor,
                "isbn": libro.isbn,
                "precio": str(libro.precio) if getattr(libro, "precio", None) is not None else None,
                "categoria": libro.categoria.nombre if getattr(libro, "categoria", None) else None,
                "stock": libro.stock,
                "editorial": getattr(libro, "editorial", None),
                "año_publicacion": getattr(libro, "año_publicacion", None),
                "descripcion": getattr(libro, "descripcion", None),
            }
        )

    return results


def search_catalog(
    query: Optional[str],
    *,
    k: int = 5,
    prefer_vector: bool = True,
    vector_search_fn: Optional[Callable[[str, int], list[dict[str, Any]]]] = None,
    orm_search_fn: Optional[Callable[[str, int], list[dict[str, Any]]]] = None,
) -> RetrievalResult:
    """Stable retrieval helper for the book catalog.

    - Tries vector search (Chroma) if available.
    - Falls back to ORM keyword search when vector search is unavailable.

    Returns a stable contract via RetrievalResult, including:
    - source: 'vector' or 'orm'
    - degraded: True when we had to fall back (or vector was intentionally skipped)
    - warnings: human-readable info useful for UI/debugging
    """

    cleaned = _clean_query(query)
    warnings: list[str] = []

    try:
        k_int = int(k)
    except Exception:
        k_int = 5
        warnings.append("Invalid 'k' value; defaulted to 5")

    if k_int <= 0:
        k_int = 5
        warnings.append("Non-positive 'k' value; defaulted to 5")

    if cleaned == "":
        return RetrievalResult(
            query="",
            k=k_int,
            source="orm" if not prefer_vector else "vector",
            degraded=True,
            results=[],
            warnings=["Empty query"],
        )

    vector_search_fn = vector_search_fn or _search_vector
    orm_search_fn = orm_search_fn or _search_orm

    if prefer_vector:
        try:
            results = vector_search_fn(cleaned, k_int)
            return RetrievalResult(
                query=cleaned,
                k=k_int,
                source="vector",
                degraded=False,
                results=results,
                warnings=warnings,
            )
        except VectorStoreUnavailable as e:
            warnings.append(str(e))
        except Exception as e:
            warnings.append(f"Vector search failed: {e}")

    # Fallback ORM
    try:
        results = orm_search_fn(cleaned, k_int)
        return RetrievalResult(
            query=cleaned,
            k=k_int,
            source="orm",
            degraded=True,
            results=results,
            warnings=warnings,
        )
    except Exception as e:
        warnings.append(f"ORM search failed: {e}")
        return RetrievalResult(
            query=cleaned,
            k=k_int,
            source="orm",
            degraded=True,
            results=[],
            warnings=warnings,
        )
