from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class VectorStoreConfig:
    db_dir: Path
    collection: str
    manifest_path: Optional[Path] = None
    embedding_model: Optional[str] = None
    embedding_device: str = "cpu"
    normalize_embeddings: bool = True


class VectorStoreUnavailable(RuntimeError):
    pass


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    with manifest_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_vector_store_config() -> VectorStoreConfig:
    db_dir = Path(os.getenv("VECTOR_DB_DIR", "./backend/agent/vector_db")).resolve()

    # Manifest is the source of truth when present; env vars are optional overrides.
    manifest_env = os.getenv("VECTOR_DB_MANIFEST", "").strip()
    if manifest_env:
        manifest_path = Path(manifest_env).resolve()
    else:
        default_manifest = db_dir / "manifest.json"
        manifest_path = default_manifest if default_manifest.exists() else None

    manifest: dict[str, Any] | None = None
    if manifest_path is not None and manifest_path.exists():
        try:
            manifest = _load_manifest(manifest_path)
        except Exception:
            manifest = None

    collection_env = os.getenv("VECTOR_COLLECTION", "").strip()
    if collection_env:
        collection = collection_env
    else:
        collection = (manifest or {}).get("collection") or "book_catalog"

    embedding_model_env = os.getenv("VECTOR_EMBEDDING_MODEL", "").strip()
    if embedding_model_env:
        embedding_model = embedding_model_env
    else:
        embedding_model = ((manifest or {}).get("embeddings", {}) or {}).get("model")

    embedding_device = os.getenv("VECTOR_EMBEDDING_DEVICE", "cpu").strip() or "cpu"

    normalize_env = os.getenv("VECTOR_EMBEDDING_NORMALIZE", "").strip().lower()
    if normalize_env:
        normalize_embeddings = normalize_env not in {"0", "false", "no"}
    else:
        normalize_embeddings = bool(((manifest or {}).get("embeddings", {}) or {}).get("normalize", True))

    return VectorStoreConfig(
        db_dir=db_dir,
        collection=collection,
        manifest_path=manifest_path,
        embedding_model=embedding_model,
        embedding_device=embedding_device,
        normalize_embeddings=normalize_embeddings,
    )


_cached_collection = None
_cached_collection_key: tuple[str, str, str, str, bool] | None = None


def get_chroma_collection(*, force_reload: bool = False):
    """Return a Chroma collection if available, else raise VectorStoreUnavailable.

    This function is intentionally dependency-optional: if chromadb (and its embedding
    deps) are not installed, it raises VectorStoreUnavailable.
    """

    global _cached_collection, _cached_collection_key

    cfg = load_vector_store_config()

    # Basic artifact presence check.
    if not cfg.db_dir.exists():
        raise VectorStoreUnavailable(
            f"Vector DB directory not found: {cfg.db_dir}. "
            "Build or unzip the Chroma artifact under backend/agent/vector_db."  # noqa: E501
        )

    model_name = cfg.embedding_model
    if not model_name:
        raise VectorStoreUnavailable(
            "VECTOR_EMBEDDING_MODEL not set and manifest missing/invalid. "
            "Cannot determine embedding model for querying."  # noqa: E501
        )

    key = (str(cfg.db_dir), cfg.collection, str(cfg.manifest_path or ""), model_name, cfg.normalize_embeddings)

    if not force_reload and _cached_collection is not None and _cached_collection_key == key:
        return _cached_collection

    try:
        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    except Exception as e:  # pragma: no cover
        raise VectorStoreUnavailable(
            "Vector search unavailable (missing dependencies). "
            "Install 'chromadb' and 'sentence-transformers' to enable it."
        ) from e

    try:
        client = chromadb.PersistentClient(path=str(cfg.db_dir))
        embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name=model_name,
            device=cfg.embedding_device,
            normalize_embeddings=cfg.normalize_embeddings,
        )
        collection = client.get_collection(name=cfg.collection, embedding_function=embedding_fn)
    except Exception as e:
        raise VectorStoreUnavailable(
            "Failed to open Chroma collection. Check VECTOR_DB_DIR/VECTOR_COLLECTION "
            "and that the artifact matches the expected embedding model."  # noqa: E501
        ) from e

    _cached_collection = collection
    _cached_collection_key = key
    return collection
