import sys
from pathlib import Path
from unittest.mock import MagicMock

# Mock dependencies
sys.modules['pandas'] = MagicMock()
sys.modules['google'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()

# Mock gdrive_integration properly
gdrive_mock = MagicMock()
gdrive_mock.ensure_safe_local_path = lambda x: Path(x)
gdrive_mock.get_ai_organizer_root = lambda: Path('/tmp')
gdrive_mock.get_metadata_root = lambda: Path('/tmp')
sys.modules['gdrive_integration'] = gdrive_mock

# Mock path_manager
pm_mock = MagicMock()
pm_mock.get_path = lambda *args, **kwargs: Path('/tmp/metadata.db')
sys.modules['path_manager'] = pm_mock

import test_metadata
import metadata_generator
import sqlite3

# Initialize generator to ensure DB is created
generator = metadata_generator.MetadataGenerator()
generator._init_tracking_db()

# Provide metadata manually since the mocked dependencies might not generate it
test_data = {"file_path": "/tmp/test.txt", "file_name": "test.txt"}
generator.save_file_metadata(test_data)

# Check db
with sqlite3.connect(generator.db_path) as conn:
    print(conn.execute("SELECT * FROM file_metadata;").fetchall())
