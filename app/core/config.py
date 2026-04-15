from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "Story Consistency Agent"
    api_prefix: str = ""
    data_dir: Path = Path("data")
    stories_dir: Path = Path("data/stories")
    max_agent_steps: int = 4
    max_tool_calls: int = 6
    max_external_calls: int = 1


settings = Settings()
