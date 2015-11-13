import imp
import importlib
from logging import getLogger
import threading


LOG = getLogger(__name__)

_HANDLERS_LOADED = False # protect against shenanigans.


def autodiscover_bus_handlers():
    """Include handlers for all applications in ``INSTALLED_APPS``."""
    from django.conf import settings
    # from django.conf import settings
    global _HANDLERS_LOADED

    with threading.RLock():
        if _HANDLERS_LOADED:
            return
        _HANDLERS_LOADED = True
        try:
            LOG.info("Discovering bus handlers...")
            return filter(None, [find_related_module(app, "handlers")
                                 for app in settings.INSTALLED_APPS])
        finally:
            _HANDLERS_LOADED = False


def find_related_module(app, related_name):
    """Given an application name and a module name, tries to find that
    module in the application."""

    try:
        app_path = importlib.import_module(app).__path__
    except AttributeError:
        return

    try:
        imp.find_module(related_name, app_path)
    except ImportError:
        return

    return importlib.import_module("%s.%s" % (app, related_name))
