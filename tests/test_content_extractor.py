
import pytest
import sqlite3
import sys
import shutil
from pathlib import Path
from unittest.mock import MagicMock

# Setup environment mock
TEMP_DIR = Path("temp_test_content_extractor").resolve()

@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir()

    # Mock gdrive_integration
    mock_gdrive = MagicMock()
    mock_gdrive.get_ai_organizer_root.return_value = TEMP_DIR
    mock_gdrive.get_metadata_root.return_value = TEMP_DIR
    mock_gdrive.ensure_safe_local_path = lambda p: p

    # Store original module if exists
    original_gdrive = sys.modules.get('gdrive_integration')

    # Patch sys.modules
    sys.modules['gdrive_integration'] = mock_gdrive

    yield

    # Restore
    if original_gdrive:
        sys.modules['gdrive_integration'] = original_gdrive
    else:
        del sys.modules['gdrive_integration']

    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)

def test_content_extractor_init():
    from content_extractor import ContentExtractor
    extractor = ContentExtractor(str(TEMP_DIR))
    assert extractor.base_dir == TEMP_DIR
    assert extractor.db_path == TEMP_DIR / "databases" / "content_index.db"

def test_content_extractor_db_reuse():
    from content_extractor import ContentExtractor
    extractor = ContentExtractor(str(TEMP_DIR))

    # Create a dummy file
    test_file = TEMP_DIR / "test.txt"
    test_file.write_text("Hello World")

    # Test with connection reuse
    with sqlite3.connect(extractor.db_path) as conn:
        result = extractor.extract_content(test_file, db_connection=conn)
        assert result['success'] is True
        assert result['text'] == "Hello World"

        # Check cache
        cached = extractor._is_content_cached(test_file, extractor._get_file_hash(test_file), db_connection=conn)
        assert cached is True

def test_content_extractor_no_reuse():
    from content_extractor import ContentExtractor
    extractor = ContentExtractor(str(TEMP_DIR))

    # Create a dummy file
    test_file = TEMP_DIR / "test2.txt"
    test_file.write_text("Hello World 2")

    # Test without connection reuse
    result = extractor.extract_content(test_file)
    assert result['success'] is True
    assert result['text'] == "Hello World 2"

    # Check cache
    cached = extractor._is_content_cached(test_file, extractor._get_file_hash(test_file))
    assert cached is True
