from __future__ import annotations

import importlib
import os
from typing import Any

import pytest
from fastapi.testclient import TestClient


APP_IMPORT_ENV_VAR = "TEST_APP_IMPORT"
DEFAULT_APP_IMPORT = "backend.main:app"


def _load_backend_app() -> Any:
    import_path = os.getenv(APP_IMPORT_ENV_VAR, DEFAULT_APP_IMPORT)
    if ":" not in import_path:
        pytest.fail(
            f"{APP_IMPORT_ENV_VAR} must be in 'module:attribute' format; got '{import_path}'"
        )

    module_path, attr_name = import_path.split(":", 1)
    try:
        module = importlib.import_module(module_path)
    except Exception as exc:  # pragma: no cover - explicit failure path
        pytest.fail(
            f"Failed to import backend app from '{import_path}'. "
            f"Set {APP_IMPORT_ENV_VAR} if your app uses a different path. Error: {exc}"
        )

    if not hasattr(module, attr_name):
        pytest.fail(f"Module '{module_path}' has no attribute '{attr_name}'")

    app = getattr(module, attr_name)
    if callable(app) and not hasattr(app, "router"):
        app = app()

    return app


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(_load_backend_app())
