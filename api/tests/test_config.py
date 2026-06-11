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
