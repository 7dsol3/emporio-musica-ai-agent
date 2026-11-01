from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    data_dir: Path = ROOT / "data"
    state_dir: Path = ROOT / "var"
    provider: str = "local"
    model_url: str = ""
    model: str = ""
    model_key: str = ""
    model_timeout: float = 15.0

    @classmethod
    def from_env(cls) -> "Settings":
        provider = os.getenv("EMPORIO_PROVIDER", "local")
        if provider not in {"local", "openai_compatible"}:
            raise ValueError("EMPORIO_PROVIDER must be local or openai_compatible")
        timeout = float(os.getenv("EMPORIO_MODEL_TIMEOUT", "15"))
        if not 1 <= timeout <= 60:
            raise ValueError("EMPORIO_MODEL_TIMEOUT must be between 1 and 60 seconds")
        return cls(
            data_dir=Path(os.getenv("EMPORIO_DATA_DIR", str(ROOT / "data"))),
            state_dir=Path(os.getenv("EMPORIO_STATE_DIR", str(ROOT / "var"))),
            provider=provider,
            model_url=os.getenv("EMPORIO_MODEL_URL", ""),
            model=os.getenv("EMPORIO_MODEL", ""),
            model_key=os.getenv("EMPORIO_MODEL_KEY", ""),
            model_timeout=timeout,
        )
