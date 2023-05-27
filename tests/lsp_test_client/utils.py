"""Provides LSP client side utilities for easier testing."""

import pathlib
import platform
import functools

import py

# pylint: disable=no-member


def normalizecase(path: str) -> str:
    """Fixes 'file' uri or path case for easier testing in windows."""
    if platform.system() == "Windows":
        return path.lower()
    return path


def as_uri(path: py.path.local) -> str:
    """Return 'file' uri as string."""
    return normalizecase(pathlib.Path(path).as_uri())


def handle_notification(params, event, results=None):
    if results is not None:
        results.append(params)
    event.set()


def get_notification_handler(*args, **kwargs):
    return functools.partial(handle_notification, *args, **kwargs)
