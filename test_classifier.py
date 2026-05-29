import sys
from pathlib import Path
from unified_classifier import UnifiedClassificationService

classifier = UnifiedClassificationService(Path("."))
result = classifier.classify_file(Path("SKY140US Kitchen Quote 0221 (1).xlsx"))
print(result)
