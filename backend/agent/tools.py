from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .retrieval import RetrievalResult, search_catalog

MAX_ACTION_QTY = 10


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


def _serialize_reserva(reserva: Any) -> dict[str, Any]:
    return {
        "reserva_id": reserva.id,
        "libro_id": reserva.libro_id,
        "usuario_id": reserva.usuario_id,
        "cantidad": reserva.cantidad,
        "estado": reserva.estado,
        "fecha_reserva": reserva.fecha_reserva.isoformat() if reserva.fecha_reserva else None,
        "fecha_expiracion": reserva.fecha_expiracion.isoformat() if reserva.fecha_expiracion else None,
    }


def _serialize_pedido(pedido: Any, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "pedido_id": pedido.id,
        "usuario_id": pedido.usuario_id,
        "estado": pedido.estado,
        "fecha": pedido.fecha.isoformat() if pedido.fecha else None,
        "items": items,
    }


def _normalize_quantity(value: Any, warnings: list[str]) -> int:
    try:
        qty = int(value)
    except Exception:
        warnings.append("Invalid 'cantidad' value; defaulted to 1")
        return 1
    if qty <= 0:
        warnings.append("Non-positive 'cantidad' value; defaulted to 1")
        return 1
    if qty > MAX_ACTION_QTY:
        warnings.append(f"Cantidad too large; clamped to {MAX_ACTION_QTY}")
        return MAX_ACTION_QTY
    return qty


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


def tool_add_to_cart(*, user_id: int, book_id: int, cantidad: Any = 1) -> ToolResult:
    warnings: list[str] = []
    qty = _normalize_quantity(cantidad, warnings)

    try:
        from apps.usuarios.models import Usuario
        from apps.libros.models import Libro
        from apps.compras.models import Carrito
    except Exception as e:
        return ToolResult(ok=False, data=None, error="django_unavailable", warnings=[str(e)])

    usuario = Usuario.objects.filter(id=user_id).first()
    if not usuario:
        return ToolResult(ok=False, data=None, error="user_not_found", warnings=warnings)

    libro = Libro.objects.filter(id=book_id).first()
    if not libro:
        return ToolResult(ok=False, data=None, error="book_not_found", warnings=warnings)

    if libro.stock is not None and libro.stock < qty:
        return ToolResult(ok=False, data=None, error="insufficient_stock", warnings=warnings)

    carrito, _ = Carrito.objects.get_or_create(usuario=usuario)
    carrito.agregar_libro(libro, qty)

    data = {
        "message": f"Libro '{libro.titulo}' agregado al carrito.",
        "result": {
            "carrito_id": carrito.id,
            "libro": _serialize_libro(libro),
            "cantidad": qty,
        },
    }
    return ToolResult(ok=True, data=data, error=None, warnings=warnings)


def tool_reserve_book(*, user_id: int, book_id: int, cantidad: Any = 1) -> ToolResult:
    warnings: list[str] = []
    qty = _normalize_quantity(cantidad, warnings)

    try:
        from apps.usuarios.models import Usuario
        from apps.libros.models import Libro
        from apps.compras.models import Reserva
    except Exception as e:
        return ToolResult(ok=False, data=None, error="django_unavailable", warnings=[str(e)])

    usuario = Usuario.objects.filter(id=user_id).first()
    if not usuario:
        return ToolResult(ok=False, data=None, error="user_not_found", warnings=warnings)

    libro = Libro.objects.filter(id=book_id).first()
    if not libro:
        return ToolResult(ok=False, data=None, error="book_not_found", warnings=warnings)

    result = Reserva().reservar_libro(libro, usuario, qty)
    if result.get("estado") != "exito":
        return ToolResult(ok=False, data=None, error="reservation_failed", warnings=warnings + [result.get("mensaje")])

    reserva = result.get("reserva")
    data = {
        "message": result.get("mensaje") or "Reserva creada.",
        "result": _serialize_reserva(reserva),
    }
    return ToolResult(ok=True, data=data, error=None, warnings=warnings)


def tool_order_status(*, user_id: int, order_id: int) -> ToolResult:
    warnings: list[str] = []

    try:
        from apps.usuarios.models import Usuario
        from apps.compras.models import Pedidos, PedidoLibro
    except Exception as e:
        return ToolResult(ok=False, data=None, error="django_unavailable", warnings=[str(e)])

    usuario = Usuario.objects.filter(id=user_id).first()
    if not usuario:
        return ToolResult(ok=False, data=None, error="user_not_found", warnings=warnings)

    pedido = Pedidos.objects.filter(id=order_id, usuario=usuario).first()
    if not pedido:
        return ToolResult(ok=False, data=None, error="order_not_found", warnings=warnings)

    items = [
        {
            "libro_id": item.libro_id,
            "titulo": getattr(item.libro, "titulo", None),
            "cantidad": item.cantidad,
        }
        for item in PedidoLibro.objects.filter(pedido=pedido).select_related("libro")
    ]
    data = {
        "message": f"Estado del pedido #{pedido.id}: {pedido.estado}.",
        "result": _serialize_pedido(pedido, items),
    }
    return ToolResult(ok=True, data=data, error=None, warnings=warnings)


__all__ = [
    "ToolResult",
    "tool_search_catalog",
    "tool_lookup_book",
    "tool_filter_catalog",
    "tool_recommend_similar",
    "tool_add_to_cart",
    "tool_reserve_book",
    "tool_order_status",
]
