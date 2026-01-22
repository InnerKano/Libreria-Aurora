from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .retrieval import RetrievalResult, search_catalog


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    data: Optional[dict[str, Any]]
    error: Optional[str]
    warnings: list[str]


def _serialize_libro(libro: Any) -> dict[str, Any]:
    return {
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


def tool_search_catalog(
    query: Optional[str],
    *,
    k: int = 5,
    prefer_vector: bool = True,
    search_fn: Optional[Callable[..., RetrievalResult]] = None,
) -> ToolResult:
    warnings: list[str] = []
    try:
        k_int = int(k)
    except Exception:
        k_int = 5
        warnings.append("Invalid 'k' value; defaulted to 5")

    if k_int <= 0:
        k_int = 5
        warnings.append("Non-positive 'k' value; defaulted to 5")

    search_fn = search_fn or search_catalog
    try:
        res = search_fn(query, k=k_int, prefer_vector=prefer_vector)
        data = {
            "query": res.query,
            "k": res.k,
            "source": res.source,
            "degraded": res.degraded,
            "results": res.results,
            "warnings": res.warnings + warnings,
        }
        return ToolResult(ok=True, data=data, error=None, warnings=warnings)
    except Exception as e:
        return ToolResult(ok=False, data=None, error=str(e), warnings=warnings)


def tool_lookup_book(*, book_id: Optional[int] = None, isbn: Optional[str] = None) -> ToolResult:
    warnings: list[str] = []

    if book_id is None and (isbn is None or str(isbn).strip() == ""):
        return ToolResult(ok=False, data=None, error="missing_identifier", warnings=["book_id or isbn required"])

    try:
        from apps.libros.models import Libro
    except Exception as e:
        return ToolResult(ok=False, data=None, error="django_unavailable", warnings=[str(e)])

    qs = Libro.objects.all()
    if book_id is not None:
        qs = qs.filter(id=book_id)
    if isbn is not None and str(isbn).strip() != "":
        cleaned_isbn = re.sub(r"[^0-9Xx]", "", str(isbn))
        if cleaned_isbn:
            qs = qs.filter(isbn=cleaned_isbn)
        else:
            warnings.append("Invalid ISBN format")

    libro = qs.first()
    if not libro:
        return ToolResult(ok=False, data={"results": []}, error="not_found", warnings=warnings)

    return ToolResult(ok=True, data={"results": [_serialize_libro(libro)]}, error=None, warnings=warnings)


def tool_filter_catalog(filters: dict[str, Any], *, k: int = 5) -> ToolResult:
    warnings: list[str] = []
    try:
        k_int = int(k)
    except Exception:
        k_int = 5
        warnings.append("Invalid 'k' value; defaulted to 5")

    if k_int <= 0:
        k_int = 5
        warnings.append("Non-positive 'k' value; defaulted to 5")

    try:
        from django.db.models import Q
        from apps.libros.models import Libro
    except Exception as e:
        return ToolResult(ok=False, data=None, error="django_unavailable", warnings=[str(e)])

    qs = Libro.objects.all()

    categoria = filters.get("categoria")
    if categoria:
        if isinstance(categoria, int) or str(categoria).isdigit():
            qs = qs.filter(categoria__id=int(categoria))
        else:
            qs = qs.filter(categoria__nombre__icontains=str(categoria))

    autor = filters.get("autor")
    if autor:
        qs = qs.filter(autor__icontains=str(autor))

    editorial = filters.get("editorial")
    if editorial:
        qs = qs.filter(editorial__icontains=str(editorial))

    disponible = filters.get("disponible")
    if disponible is True:
        qs = qs.filter(stock__gt=0)
    elif disponible is False:
        qs = qs.filter(stock__lte=0)

    precio_min = filters.get("precio_min")
    if precio_min is not None and str(precio_min).strip() != "":
        try:
            qs = qs.filter(precio__gte=float(precio_min))
        except Exception:
            warnings.append("Invalid precio_min")

    precio_max = filters.get("precio_max")
    if precio_max is not None and str(precio_max).strip() != "":
        try:
            qs = qs.filter(precio__lte=float(precio_max))
        except Exception:
            warnings.append("Invalid precio_max")

    query = filters.get("q")
    if query:
        qs = qs.filter(
            Q(titulo__icontains=query)
            | Q(autor__icontains=query)
            | Q(isbn__icontains=query)
            | Q(descripcion__icontains=query)
            | Q(editorial__icontains=query)
        )

    results = [_serialize_libro(libro) for libro in qs[:k_int]]
    return ToolResult(ok=True, data={"results": results, "warnings": warnings}, error=None, warnings=warnings)


def tool_recommend_similar(
    *,
    book_id: int,
    k: int = 5,
    search_fn: Optional[Callable[..., RetrievalResult]] = None,
) -> ToolResult:
    lookup = tool_lookup_book(book_id=book_id)
    if not lookup.ok or not (lookup.data or {}).get("results"):
        return ToolResult(ok=False, data={"results": []}, error=lookup.error, warnings=lookup.warnings)

    base = (lookup.data or {}).get("results", [])[0]
    query = " ".join(
        [
            str(base.get("titulo") or ""),
            str(base.get("autor") or ""),
            str(base.get("categoria") or ""),
            str(base.get("editorial") or ""),
            str(base.get("descripcion") or ""),
        ]
    ).strip()

    search_fn = search_fn or search_catalog
    res = search_fn(query, k=k + 1, prefer_vector=True)

    filtered: list[dict[str, Any]] = []
    for item in res.results:
        libro_id = item.get("libro_id")
        if libro_id is None:
            metadata = item.get("metadata") or {}
            libro_id = metadata.get("libro_id")
        if libro_id == book_id:
            continue
        filtered.append(item)
        if len(filtered) >= k:
            break

    data = {
        "query": res.query,
        "k": k,
        "source": res.source,
        "degraded": res.degraded,
        "results": filtered,
        "warnings": res.warnings,
    }
    return ToolResult(ok=True, data=data, error=None, warnings=res.warnings)


__all__ = [
    "ToolResult",
    "tool_search_catalog",
    "tool_lookup_book",
    "tool_filter_catalog",
    "tool_recommend_similar",
]
