from .common import *
try:
    from .secretstuff import SecretStuff
except ImportError:
    raise ValueError("Missing secretstuff module; please acquire a copy")

__version__ = "1.0.0"
