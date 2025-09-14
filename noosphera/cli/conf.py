from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional

from confy.loader import Config as ConfyConfig

# local defaults (repo) for precedence's base layer
from ..config.loader import DEFAULT_CONFIG_PATH, _load_repo_defaults  # type: ignore
from ..core.errors import ConfigError

ENV_PREFIX = "NOOSPHERA"


def _parse_overrides(overrides_str: Optional[str]) -> Dict[str, object]:
    """
    Parse CLI overrides as comma-separated `dot.key:JSON_value`, e.g.:
      logging.level:"DEBUG",server.port:8081
    """
    if not overrides_str:
        return {}
    result: Dict[str, object] = {}
    for item in overrides_str.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            raise ConfigError(f"Invalid override '{item}', expected 'key:JSON_value'")
        key, val = item.split(":", 1)
        try:
            result[key.strip()] = json.loads(val.strip())
        except json.JSONDecodeError:
            # treat as raw string if not valid JSON
            result[key.strip()] = val.strip().strip('"')
    return result


def _load_confy(
    config_file: Optional[str],
    dotenv_path: Optional[str],
    prefix: str,
    overrides_str: Optional[str],
) -> ConfyConfig:
    defaults = _load_repo_defaults(DEFAULT_CONFIG_PATH)
    return ConfyConfig(
        file_path=config_file,
        defaults=defaults,
        prefix=prefix,
        dotenv_path=dotenv_path,
        load_dotenv_file=True,
        overrides_dict=_parse_overrides(overrides_str),
    )


def main(argv: Optional[list[str]] = None) -> int:
    argv = argv or sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="noosphera-conf",
        description="Inspect Noosphera effective configuration (Confy-backed).",
    )
    parser.add_argument("-c", "--config", help="Path to user config TOML/JSON", default=None)
    parser.add_argument("--dotenv", help="Path to .env file (optional)", default=None)
    parser.add_argument("-p", "--prefix", help="Env var prefix", default=ENV_PREFIX)
    parser.add_argument(
        "--overrides",
        help='Comma separated overrides: dot.key:JSON_value (e.g., logging.level:"DEBUG")',
        default=None,
    )

    subparsers = parser.add_subparsers(dest="cmd", required=True)

    subparsers.add_parser("show", help="Print merged config as pretty JSON")

    get_p = subparsers.add_parser("get", help="Get merged value of a key (JSON)")
    get_p.add_argument("key")

    set_p = subparsers.add_parser(
        "set",
        help="Set a key (in-memory only in Step 1.1; to persist, use the `confy` CLI).",
    )
    set_p.add_argument("key")
    set_p.add_argument("value", help="JSON value (e.g., '8081', '\"DEBUG\"', 'true')")

    exists_p = subparsers.add_parser("exists", help="Exit 0 if key exists; 1 otherwise")
    exists_p.add_argument("key")

    args = parser.parse_args(argv)

    cfg = _load_confy(args.config, args.dotenv, args.prefix, args.overrides)

    if args.cmd == "show":
        print(json.dumps(cfg.as_dict(), indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "get":
        key = args.key
        val = cfg.get(key, None)
        if val is None and key not in cfg:
            print(f"Key not found: {key}", file=sys.stderr)
            return 1
        print(json.dumps(val, ensure_ascii=False))
        return 0

    if args.cmd == "set":
        key = args.key
        try:
            value = json.loads(args.value)
        except json.JSONDecodeError:
            value = args.value
        # In-memory update only (Step 1.1)
        cfg.set(key, value)  # Confy dict-like setter supports dot-keys via helper
        print(json.dumps({key: cfg.get(key)}, ensure_ascii=False))
        print(
            "Note: This change is in-memory only for Step 1.1. "
            "To persist to a file, use: confy -c <file> set "
            f"{key} {args.value}",
            file=sys.stderr,
        )
        return 0

    if args.cmd == "exists":
        return 0 if args.key in cfg else 1

    return 2
