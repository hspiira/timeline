"""ID and value generators (e.g. CUID)."""

from cuid2 import cuid_wrapper

cuid_generator = cuid_wrapper()


def generate_cuid() -> str:
    """Generate a collision-resistant unique identifier (CUID2).

    Returns:
        A new CUID string.
    """
    result = cuid_generator()
    if not isinstance(result, str):
        raise TypeError(
            f"Expected str from cuid_generator, got {type(result).__name__}"
        )
    return result
