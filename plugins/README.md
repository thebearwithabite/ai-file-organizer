# AI File Organizer Plugins

Plugins extend the AI File Organizer with custom classifiers, analyzers, and integrations.

## Creating a Plugin

1. Create a directory under `plugins/` with your plugin name
2. Add an `__init__.py` that exposes a `register(app, config)` function
3. For classifiers, implement `classify(file_path: Path) -> dict`

## Classifier Contract

```python
from pathlib import Path

def classify(file_path: Path) -> dict:
    """
    Classify a file and return classification result.
    
    Returns:
        dict with keys:
        - category: str (e.g., "documents", "images")
        - confidence: float (0.0 to 1.0)
        - reasoning: str (explanation of classification)
    """
    return {
        "category": "unknown",
        "confidence": 0.0,
        "reasoning": "Not implemented"
    }
```

## Loading Plugins

Add your plugin to `config.yaml`:

```yaml
plugins:
  enabled:
    - example_classifier
```

Plugins are loaded at startup if listed in the config.
