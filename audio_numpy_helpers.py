# numpy 2.x compatibility helpers
def _safe_float(x):
    """Convert numpy scalar/array to Python float safely."""
    import numpy as np
    if isinstance(x, np.ndarray):
        return float(x.item())
    if hasattr(x, "item"):
        return float(x.item())
    return float(x)

def _safe_int(x):
    """Convert numpy scalar/array to Python int safely."""
    import numpy as np
    if isinstance(x, np.ndarray):
        return int(x.item())
    if hasattr(x, "item"):
        return int(x.item())
    return int(x)
