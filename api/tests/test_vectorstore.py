from qdrant_client.models import Distance

from app import vectorstore


class FakeClient:
    def __init__(self, existing: bool) -> None:
        self._existing = existing
        self.created: dict | None = None

    def collection_exists(self, name: str) -> bool:
        return self._existing

    def create_collection(self, collection_name: str, vectors_config) -> None:
        self.created = {
            "name": collection_name,
            "size": vectors_config.size,
            "distance": vectors_config.distance,
        }

    def get_collections(self):
        return []


def test_check_qdrant_calls_get_collections(monkeypatch) -> None:
    client = FakeClient(existing=True)
    monkeypatch.setattr(vectorstore, "get_qdrant", lambda: client)
    assert vectorstore.check_qdrant() is True


def test_ensure_collection_creates_when_missing(monkeypatch) -> None:
    client = FakeClient(existing=False)
    monkeypatch.setattr(vectorstore, "get_qdrant", lambda: client)

    vectorstore.ensure_collection()

    assert client.created is not None
    assert client.created["size"] == 384
    assert client.created["distance"] == Distance.COSINE
    assert client.created["name"] == vectorstore.get_settings().qdrant_collection


def test_ensure_collection_noop_when_present(monkeypatch) -> None:
    client = FakeClient(existing=True)
    monkeypatch.setattr(vectorstore, "get_qdrant", lambda: client)

    vectorstore.ensure_collection()

    assert client.created is None
