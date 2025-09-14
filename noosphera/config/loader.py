from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from ..core.errors import ConfigError
from .schema import Settings

# TOML reader: stdlib for 3.11+, tomli fallback for 3.10
try:
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

try:
    from confy.loader import Config as ConfyConfig
except Exception as exc:  # pragma: no cover
    raise ConfigError(f"Confy library is required but not available: {exc}") from exc


DEFAULT_CONFIG_PATH = Path(__file__).with_name("default.toml")
ENV_PREFIX = "NOOSPHERA"
ENV_CONFIG_FILE = f"{ENV_PREFIX}_CONFIG"


def _load_repo_defaults(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def load_settings(
    config_path: Optional[Path] = None,
    env_file: Optional[Path] = None,
    overrides: Optional[dict] = None,
) -> Settings:
    """
    Load and merge configuration using Confy with precedence:
      defaults (repo default.toml) < config file < .env < env vars < overrides.

    - config_path: optional path to a user config file, defaults to $NOOSPHERA_CONFIG if set.
    - env_file: optional .env path; if None, Confy will auto-discover .env (non-destructive).
    - overrides: final-layer in-memory overrides (e.g., from CLI arguments).

    Returns:
        Settings: validated, typed settings object.
    """
    try:
        defaults = _load_repo_defaults(DEFAULT_CONFIG_PATH)

        # Allow $NOOSPHERA_CONFIG to specify a custom config file.
        if config_path is None:
            env_cfg = os.getenv(ENV_CONFIG_FILE)
            if env_cfg:
                config_path = Path(env_cfg)

        cfg = ConfyConfig(
            file_path=str(config_path) if config_path else None,
            defaults=defaults,
            prefix=ENV_PREFIX,             # only NOOSPHERA_* env vars apply
            load_dotenv_file=True,         # load .env (won't override real env)
            dotenv_path=str(env_file) if env_file else None,
            overrides_dict=overrides or {},
            # no mandatory keys in Step 1.1
        )

        merged_dict = cfg.as_dict()  # deep dict view of final config
        return Settings.model_validate(merged_dict)
    except Exception as exc:
        raise ConfigError(f"Failed to load settings: {exc}") from exc
