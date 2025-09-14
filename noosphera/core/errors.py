class NoospheraError(Exception):
    """Base error for Noosphera."""


class ConfigError(NoospheraError):
    """Configuration load/validation error."""


class StartupError(NoospheraError):
    """Application startup error."""
