from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import get_settings

_client: QdrantClient | None = None


def get_qdrant() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=get_settings().qdrant_url)
    return _client


def check_qdrant() -> bool:
    get_qdrant().get_collections()
    return True


def ensure_collection() -> None:
    """Create the chunks collection if it does not exist yet."""
    settings = get_settings()
    client = get_qdrant()
    if not client.collection_exists(settings.qdrant_collection):
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=settings.embed_dim, distance=Distance.COSINE),
        )
