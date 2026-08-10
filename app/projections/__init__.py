"""Projection handlers: register at startup via register_all_handlers()."""

import importlib
import logging
import pkgutil

from app.core.projections import get_registry

logger = logging.getLogger(__name__)


def register_all_handlers() -> None:
    """Import all handler modules so @projection decorators run. Call from lifespan.

    Discovers all submodules in the app.projections package (e.g. audit, metrics)
    and imports them, triggering their @projection decorators to register handlers.
    """
    import app.projections as projections_pkg

    for module_info in pkgutil.iter_modules(projections_pkg.__path__):
        module_name = f"{projections_pkg.__name__}.{module_info.name}"
        importlib.import_module(module_name)
        logger.debug("Loaded projection handler module: %s", module_name)

    # Touch the registry to ensure handlers are initialized (primarily for tests/introspection).
    get_registry().all()
