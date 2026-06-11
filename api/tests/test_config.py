from pathlib import Path

from app.config import Settings


def test_env_local_wins_over_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=from-env\nLLM_MODEL=base-model\n")
    (tmp_path / ".env.local").write_text("OPENAI_API_KEY=from-env-local\n")

    settings = Settings()

    assert settings.openai_api_key == "from-env-local"
    assert settings.llm_model == "base-model"


def test_contract_vars_have_defaults() -> None:
    settings = Settings(openai_api_key="x", _env_file=None)

    assert settings.qdrant_collection == "docchat_chunks"
    assert settings.embed_dim == 384
    assert settings.chunk_size > 0
    assert settings.chunk_overlap >= 0
    assert settings.retrieval_top_k > 0
    assert 0.0 <= settings.retrieval_score_threshold <= 1.0
    assert settings.chat_token_budget > 0


def test_env_var_overrides_default(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setenv("RETRIEVAL_TOP_K", "9")

    settings = Settings()

    assert settings.retrieval_top_k == 9
