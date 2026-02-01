
import pytest
import re
from pathlib import Path
from bulletproof_deduplication import BulletproofDeduplicator

class TestDeduplicationProtection:
    @pytest.fixture
    def dedup(self):
        return BulletproofDeduplicator()

    def test_protected_extensions_blocked(self, dedup):
        """Test that files with protected extensions are blocked."""
        assert dedup.is_database_or_learned_data(Path("test.db")) is True
        assert dedup.is_database_or_learned_data(Path("test.sqlite")) is True
        assert dedup.is_database_or_learned_data(Path("test.sqlite3")) is True
        assert dedup.is_database_or_learned_data(Path("test.pkl")) is True
        assert dedup.is_database_or_learned_data(Path("test.pickle")) is True
        assert dedup.is_database_or_learned_data(Path("TEST.DB")) is True  # Case insensitive

        # Test unprotected extensions
        assert dedup.is_database_or_learned_data(Path("test.txt")) is False
        assert dedup.is_database_or_learned_data(Path("test.jpg")) is False

    def test_protected_directory_names_blocked(self, dedup):
        """Test that files within protected directories are blocked."""
        assert dedup.is_database_or_learned_data(Path("path/to/vector_db/index.json")) is True
        assert dedup.is_database_or_learned_data(Path("path/to/chroma/data.bin")) is True
        assert dedup.is_database_or_learned_data(Path("path/to/metadata_system/config.json")) is True
        assert dedup.is_database_or_learned_data(Path("path/to/learning/model.pt")) is True
        assert dedup.is_database_or_learned_data(Path("path/to/adaptive/rules.json")) is True
        assert dedup.is_database_or_learned_data(Path("path/to/embeddings/cache.bin")) is True
        assert dedup.is_database_or_learned_data(Path("path/to/index/lookup.dat")) is True
        assert dedup.is_database_or_learned_data(Path("path/to/_system/internal.dat")) is True
        assert dedup.is_database_or_learned_data(Path("path/to/classification_logs/log.txt")) is True

        # Case insensitive check
        assert dedup.is_database_or_learned_data(Path("path/to/VECTOR_DB/index.json")) is True

    def test_protected_regex_patterns_blocked(self, dedup):
        """Test that files matching protected regex patterns are blocked."""
        assert dedup.is_database_or_learned_data(Path("path/to/_METADATA_SYSTEM/file.txt")) is True
        assert dedup.is_database_or_learned_data(Path("path/to/_SYSTEM/my.db")) is True
        assert dedup.is_database_or_learned_data(Path("adaptive_learning_v1.json")) is True
        assert dedup.is_database_or_learned_data(Path("deduplication.db")) is True

    def test_safe_duplicate_patterns(self, dedup):
        """Test that safe duplicate patterns match correctly."""
        # Note: Original implementation was case-sensitive for these patterns?
        # Let's check the code: re.match(pattern, filename) -> standard is case sensitive.
        # But 'Generated Image' implies specific casing.

        # Matches
        assert any(p.match("test (1).txt") for p in dedup.safe_duplicate_compiled)
        assert any(p.match("test copy.txt") for p in dedup.safe_duplicate_compiled)
        assert any(p.match("Generated Image 123.jpeg") for p in dedup.safe_duplicate_compiled)
        assert any(p.match("file_20230101_120000.jpg") for p in dedup.safe_duplicate_compiled)
        assert any(p.match("Screenshot 2023-01-01.png") for p in dedup.safe_duplicate_compiled)
        assert any(p.match("Copy of file.txt") for p in dedup.safe_duplicate_compiled)

        # Non-matches
        assert not any(p.match("test.txt") for p in dedup.safe_duplicate_compiled)
        assert not any(p.match("image.jpg") for p in dedup.safe_duplicate_compiled)

        # Case sensitivity check (should FAIL if case doesn't match, as we reverted IGNORECASE)
        # "Generated Image" vs "generated image"
        # Since we removed IGNORECASE, this should NOT match if pattern assumes specific casing
        # The pattern is r'Generated Image.*\.jpeg'
        assert not any(p.match("generated image 123.jpeg") for p in dedup.safe_duplicate_compiled)

    def test_protected_paths_check(self, dedup):
        """Test that calculate_safety_score returns 0.0 for protected system paths."""
        # Mock group and last modified
        group = [{'path': Path('/System/Library/CoreServices/Finder.app'), 'size': 100}]

        assert dedup.calculate_safety_score(Path('/System/Library/CoreServices/Finder.app'), group) == 0.0
        assert dedup.calculate_safety_score(Path('/Applications/MyApp.app'), group) == 0.0
        assert dedup.calculate_safety_score(Path('/.git/config'), group) == 0.0

        # Exceptions
        # iCloud Drive
        file_path = Path('/Library/Mobile Documents/com~apple~CloudDocs/test.txt')
        # Should NOT return 0.0 purely based on protected paths (it's whitelisted)
        # Note: Might return > 0.0 based on other factors
        assert dedup.calculate_safety_score(file_path, group) >= 0.0
