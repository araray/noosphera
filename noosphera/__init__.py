"""Noosphera package marker."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("noosphera")
except PackageNotFoundError:
    from .get_version import _get_version_from_pyproject
    __version__ = _get_version_from_pyproject()

__all__ = ["__version__"]
