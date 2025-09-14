from fastapi import Request

from ..config.schema import Settings


def get_settings(request: Request) -> Settings:
    """
    FastAPI dependency to access the merged, typed settings
    stored on the app state.
    """
    return request.app.state.settings  # type: ignore[no-any-return]
