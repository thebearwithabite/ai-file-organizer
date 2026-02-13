"""Example classifier plugin - demonstrates the plugin interface."""

from .classifier import classify

def register(app, config):
    """
    Register this plugin with the application.
    
    Args:
        app: FastAPI application instance
        config: Configuration dictionary
    """
    # Plugins can add routes, register classifiers, etc.
    print(f"[example_classifier] Plugin registered")
