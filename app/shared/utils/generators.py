"""ID and value generators (e.g. CUID)."""

from cuid2 import cuid_wrapper

cuid_generator = cuid_wrapper()


def generate_cuid() -> str:
    """Generate a collision-resistant unique identifier (CUID2).

    Returns:
        A new CUID string.
    """
    result = cuid_generator()
    assert isinstance(result, str)
    return result
