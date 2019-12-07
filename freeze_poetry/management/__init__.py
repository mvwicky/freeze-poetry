try:
    import django
except ImportError as e:
    raise RuntimeError(
        "Install with extra 'django' to use the management commands."
    ) from e

