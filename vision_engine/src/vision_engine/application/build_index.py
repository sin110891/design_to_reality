from __future__ import annotations

from pathlib import Path

from vision_engine.domain.enums import ReviewStatus
from vision_engine.domain.models import DatasetRecord
from vision_engine.infrastructure.embedding_clients import build_embedding_client
from vision_engine.infrastructure.gold_adapter import load_gold_jsonl, load_metadata_csv
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.infrastructure.vector_store import NumpyVectorStore
from vision_engine.settings import AppSettings


def _resolve_record_image(settings: AppSettings, record: DatasetRecord) -> Path | None:
    path = Path(record.image_path)
    if path.is_absolute() and path.exists():
        return path
    resolved = settings.resolve(path)
    if resolved.exists():
        return resolved
    alt = settings.project_root.parent / "dataset_factory" / path
    if alt.exists():
        record.image_path = str(alt)
        return alt
    # Try curated images dir by basename
    candidate = settings.paths.curated_images / path.name
    if candidate.exists():
        record.image_path = str(candidate)
        return candidate
    return None


def load_curated_records(
    *,
    settings: AppSettings,
    metadata: Path | None = None,
    gold_jsonl: Path | None = None,
    images_dir: Path | None = None,
    approved_only: bool = True,
) -> list[DatasetRecord]:
    images_dir = images_dir or settings.paths.curated_images
    records: list[DatasetRecord] = []

    if gold_jsonl is not None:
        path = gold_jsonl if gold_jsonl.is_absolute() else settings.resolve(gold_jsonl)
        records.extend(
            load_gold_jsonl(path, image_root=images_dir, approved_only=approved_only)
        )
    elif metadata is not None:
        path = metadata if metadata.is_absolute() else settings.resolve(metadata)
        records.extend(load_metadata_csv(path, images_dir=images_dir))
    elif settings.paths.curated_metadata.exists():
        records.extend(
            load_metadata_csv(settings.paths.curated_metadata, images_dir=images_dir)
        )

    # Keep only records with resolvable images; optionally approved.
    usable: list[DatasetRecord] = []
    for record in records:
        if approved_only and record.review_status != ReviewStatus.APPROVED:
            continue
        if _resolve_record_image(settings, record) is None:
            continue
        usable.append(record)
    return usable


def build_index(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    metadata: Path | None = None,
    gold_jsonl: Path | None = None,
    images_dir: Path | None = None,
    output: Path | None = None,
) -> tuple[Path, int]:
    records = load_curated_records(
        settings=settings,
        metadata=metadata,
        gold_jsonl=gold_jsonl,
        images_dir=images_dir,
        approved_only=True,
    )
    if not records:
        raise FileNotFoundError(
            "No approved curated records with resolvable images. "
            "Pass --gold from dataset_factory exports or --metadata CSV."
        )

    repo.upsert_dataset_records(records)

    embedder = build_embedding_client(
        provider=settings.embedding_provider,
        api_key=settings.gemini_api_key,
        model_name=settings.embedding_model_name,
    )
    image_embeddings: dict[str, list[float]] = {}
    text_embeddings: dict[str, list[float]] = {}
    for record in records:
        img_path = _resolve_record_image(settings, record)
        assert img_path is not None
        image_embeddings[record.image_id] = embedder.embed_image(img_path)
        text_embeddings[record.image_id] = embedder.embed_text(record.text_blob or record.image_id)

    store = NumpyVectorStore()
    store.build(records, image_embeddings, text_embeddings)
    out = output or settings.paths.index_path
    if not out.is_absolute():
        out = settings.resolve(out)
    store.save(out)

    try:
        from vision_engine.application.build_retrieval_index import build_versioned_retrieval_index

        build_versioned_retrieval_index(
            repo=repo,
            settings=settings,
            metadata=metadata,
            gold_jsonl=gold_jsonl,
            images_dir=images_dir,
            snapshot_name=out.stem,
            promote=True,
        )
    except Exception:
        # Legacy npz index remains usable if versioned pipeline fails.
        pass

    return out, len(records)


def load_index(settings: AppSettings, path: Path | None = None) -> NumpyVectorStore:
    store = NumpyVectorStore()
    index_path = path or settings.paths.index_path
    if not index_path.is_absolute():
        index_path = settings.resolve(index_path)
    store.load(index_path)
    return store
