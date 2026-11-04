from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from vision_engine.domain.models import DatasetRecord
from vision_engine.domain.retrieval_models import SnapshotReferenceRecord, VectorIndexVersion
from vision_engine.infrastructure.vector_store import NumpyVectorStore


@dataclass
class IndexedReference:
    index_position: int
    snapshot_reference_record_id: str
    reference_embedding_id: str
    image_id: str
    record: DatasetRecord


@dataclass
class VersionedVectorStore:
    """NumPy-backed index pinned to one vector index version."""

    index_version: VectorIndexVersion
    store: NumpyVectorStore
    references: list[IndexedReference] = field(default_factory=list)
    membership_by_image_id: dict[str, IndexedReference] = field(default_factory=dict)

    @property
    def records(self) -> list[DatasetRecord]:
        return [ref.record for ref in self.references]

    def build(
        self,
        *,
        snapshot_records: list[SnapshotReferenceRecord],
        image_embeddings: dict[str, list[float]],
        text_embeddings: dict[str, list[float]],
        memberships: list[tuple[str, str, str]],
    ) -> None:
        ordered_records: list[DatasetRecord] = []
        indexed: list[IndexedReference] = []
        for idx, (snapshot_id, embedding_id, image_id) in enumerate(memberships):
            snap = next(r for r in snapshot_records if r.snapshot_reference_record_id == snapshot_id)
            record = snap.record
            if record is None:
                raise ValueError(f"Missing dataset record for snapshot reference {snapshot_id}")
            ordered_records.append(record)
            ref = IndexedReference(
                index_position=idx,
                snapshot_reference_record_id=snapshot_id,
                reference_embedding_id=embedding_id,
                image_id=image_id,
                record=record,
            )
            indexed.append(ref)
        self.store.build(ordered_records, image_embeddings, text_embeddings)
        self.references = indexed
        self.membership_by_image_id = {r.image_id: r for r in indexed}

    def save(self, path: Path) -> None:
        self.store.save(path)
        manifest = {
            "vector_index_version_id": self.index_version.vector_index_version_id,
            "dataset_snapshot_id": self.index_version.dataset_snapshot_id,
            "embedding_space_id": self.index_version.embedding_space_id,
            "memberships": [
                {
                    "index_position": ref.index_position,
                    "snapshot_reference_record_id": ref.snapshot_reference_record_id,
                    "reference_embedding_id": ref.reference_embedding_id,
                    "image_id": ref.image_id,
                }
                for ref in self.references
            ],
        }
        path.with_suffix(".manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

    @classmethod
    def load(
        cls,
        *,
        index_version: VectorIndexVersion,
        index_path: Path,
        snapshot_records: list[SnapshotReferenceRecord],
    ) -> VersionedVectorStore:
        store = NumpyVectorStore()
        store.load(index_path)
        manifest_path = index_path.with_suffix(".manifest.json")
        if not manifest_path.exists():
            raise FileNotFoundError(f"Missing index manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        snap_by_id = {r.snapshot_reference_record_id: r for r in snapshot_records}
        indexed: list[IndexedReference] = []
        for item in manifest["memberships"]:
            snap = snap_by_id[item["snapshot_reference_record_id"]]
            record = snap.record
            if record is None:
                ds_id = item["image_id"]
                record = next((r.record for r in snapshot_records if r.image_id == ds_id and r.record), None)
            if record is None:
                raise ValueError(f"Cannot resolve record for membership {item}")
            indexed.append(
                IndexedReference(
                    index_position=item["index_position"],
                    snapshot_reference_record_id=item["snapshot_reference_record_id"],
                    reference_embedding_id=item["reference_embedding_id"],
                    image_id=item["image_id"],
                    record=record,
                )
            )
        indexed.sort(key=lambda r: r.index_position)
        versioned = cls(index_version=index_version, store=store, references=indexed)
        versioned.membership_by_image_id = {r.image_id: r for r in indexed}
        return versioned

    def search_image(self, query: list[float], top_k: int) -> list[tuple[IndexedReference, float]]:
        hits = self.store.search_image(query, top_k=top_k)
        return [(self.references[idx], score) for idx, score in hits]

    def search_text(self, query: list[float], top_k: int) -> list[tuple[IndexedReference, float]]:
        hits = self.store.search_text(query, top_k=top_k)
        return [(self.references[idx], score) for idx, score in hits]

    def image_vector(self, ref: IndexedReference) -> np.ndarray:
        return self.store.image_matrix()[ref.index_position]
