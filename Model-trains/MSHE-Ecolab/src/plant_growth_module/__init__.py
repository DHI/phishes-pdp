"""Plant Growth Module package."""

from importlib import import_module

__all__ = [
    "pgm_helper",
    "forcing_repository",
    "common_utils",
    "template_maps",
    "soil_profile_setup",
]


def __getattr__(name):
    if name in __all__:
        module = import_module(f".{name}", __name__)
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
