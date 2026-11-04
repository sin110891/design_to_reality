from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Lock, RLock
from time import sleep

import numpy as np

from vision_engine.infrastructure.embedding_clients import joint
from vision_engine.infrastructure.embedding_clients.local_clip_joint import (
    LocalClipJointEmbeddingClient,
)


def test_local_joint_client_is_constructed_once_per_model(monkeypatch):
    class FakeLocalClient:
        created = 0

        def __init__(self, *, model_name: str):
            type(self).created += 1
            self.model_name = model_name

    import vision_engine.infrastructure.embedding_clients.local_clip_joint as local_module

    joint._LOCAL_CLIENTS.clear()
    monkeypatch.setattr(local_module, "LocalClipJointEmbeddingClient", FakeLocalClient)
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            clients = list(
                pool.map(
                    lambda _: joint.build_joint_embedding_client(
                        provider="local", model_name="test-clip"
                    ),
                    range(8),
                )
            )
        assert FakeLocalClient.created == 1
        assert len({id(client) for client in clients}) == 1
    finally:
        joint._LOCAL_CLIENTS.clear()


def test_local_clip_serializes_encode_calls():
    class FakeModel:
        def __init__(self):
            self.active = 0
            self.maximum_active = 0
            self.lock = Lock()

        def encode(self, _value, *, convert_to_numpy: bool):
            assert convert_to_numpy
            with self.lock:
                self.active += 1
                self.maximum_active = max(self.maximum_active, self.active)
            sleep(0.01)
            with self.lock:
                self.active -= 1
            return np.asarray([1.0, 0.0], dtype=np.float32)

    client = object.__new__(LocalClipJointEmbeddingClient)
    client._model = FakeModel()
    client._encode_lock = RLock()

    with ThreadPoolExecutor(max_workers=8) as pool:
        vectors = list(pool.map(client.embed_text, [f"brief {i}" for i in range(8)]))

    assert len(vectors) == 8
    assert client._model.maximum_active == 1
