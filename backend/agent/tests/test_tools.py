import pytest

from agent.tools import tool_filter_catalog, tool_lookup_book, tool_recommend_similar, tool_search_catalog
from agent.retrieval import RetrievalResult


@pytest.mark.django_db
def test_tool_lookup_book_by_id():
    from apps.libros.models import Categoria, Libro

    categoria = Categoria.objects.create(nombre="Novela", descripcion="X")
    libro = Libro.objects.create(
        titulo="Cien años de soledad",
        autor="Gabriel García Márquez",
        isbn="9780307474728",
        categoria=categoria,
        editorial="Sudamericana",
        precio="19.99",
        stock=4,
        año_publicacion=1967,
        descripcion="...",
    )

    res = tool_lookup_book(book_id=libro.id)
    assert res.ok is True
    assert res.data["results"][0]["libro_id"] == libro.id


@pytest.mark.django_db
def test_tool_lookup_book_by_isbn():
    from apps.libros.models import Categoria, Libro

    categoria = Categoria.objects.create(nombre="Ficcion", descripcion="X")
    Libro.objects.create(
        titulo="El Aleph",
        autor="Borges",
        isbn="9789875666482",
        categoria=categoria,
        editorial="Emece",
        precio="15.00",
        stock=2,
        año_publicacion=1945,
        descripcion="...",
    )

    res = tool_lookup_book(isbn="9789875666482")
    assert res.ok is True
    assert res.data["results"][0]["isbn"] == "9789875666482"


@pytest.mark.django_db
def test_tool_filter_catalog_by_categoria_and_disponible():
    from apps.libros.models import Categoria, Libro

    cat_a = Categoria.objects.create(nombre="Fantasia", descripcion="X")
    cat_b = Categoria.objects.create(nombre="Historia", descripcion="X")

    Libro.objects.create(
        titulo="Libro A",
        autor="Autor A",
        isbn="1111111111111",
        categoria=cat_a,
        editorial="Ed A",
        precio="10.00",
        stock=3,
        año_publicacion=2000,
        descripcion="...",
    )
    Libro.objects.create(
        titulo="Libro B",
        autor="Autor B",
        isbn="2222222222222",
        categoria=cat_b,
        editorial="Ed B",
        precio="12.00",
        stock=0,
        año_publicacion=2001,
        descripcion="...",
    )

    res = tool_filter_catalog({"categoria": "Fantasia", "disponible": True}, k=5)
    assert res.ok is True
    assert len(res.data["results"]) == 1
    assert res.data["results"][0]["categoria"] == "Fantasia"


def test_tool_search_catalog_wraps_retrieval(monkeypatch):
    def fake_search(query, *, k=5, prefer_vector=True):
        return RetrievalResult(
            query=query,
            k=k,
            source="vector",
            degraded=False,
            results=[{"id": "x"}],
            warnings=[],
        )

    res = tool_search_catalog("harry", k=3, search_fn=fake_search)
    assert res.ok is True
    assert res.data["results"] == [{"id": "x"}]


def test_tool_recommend_similar_filters_same_book(monkeypatch):
    def fake_search(query, *, k=5, prefer_vector=True):
        return RetrievalResult(
            query=query,
            k=k,
            source="vector",
            degraded=False,
            results=[
                {"metadata": {"libro_id": 10}},
                {"metadata": {"libro_id": 11}},
            ],
            warnings=[],
        )

    def fake_lookup_book(*, book_id=None, isbn=None):
        class Resp:
            ok = True
            error = None
            warnings = []
            data = {"results": [{"libro_id": 10, "titulo": "A", "autor": "B"}]}

        return Resp()

    monkeypatch.setattr("agent.tools.tool_lookup_book", fake_lookup_book)
    res = tool_recommend_similar(book_id=10, k=1, search_fn=fake_search)
    assert res.ok is True
    assert len(res.data["results"]) == 1
    assert res.data["results"][0]["metadata"]["libro_id"] == 11
