import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(dotenv_path: Path = Path(".env")) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_dotenv()


def first_env(*keys: str) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return None


@dataclass(frozen=True)
class Settings:
    app_name: str = "Story Consistency Agent"
    api_prefix: str = ""
    data_dir: Path = Path("data")
    stories_dir: Path = Path("data/stories")
    max_agent_steps: int = 4
    max_tool_calls: int = 6
    max_external_calls: int = 1
    llm_model: str = os.getenv("LLM_MODEL", "gpt-5.4-mini")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "demo-token-overlap")
    llm_api_key: str | None = first_env("LLM_API_KEY", "OPENAI_API_KEY", "openai_api_key")
    openai_api_key: str | None = first_env("OPENAI_API_KEY", "openai_api_key", "openai_api_key_")
    anthropic_api_key: str | None = first_env("ANTHROPIC_API_KEY", "anthropic_api_key")
    embedding_api_key: str | None = os.getenv("EMBEDDING_API_KEY")
    external_research_api_key: str | None = os.getenv("EXTERNAL_RESEARCH_API_KEY")


settings = Settings()
