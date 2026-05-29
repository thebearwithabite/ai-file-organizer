"""
EnhancedLibrarianCLI - Compatibility Shim for AI File Organizer v3.5
Routes legacy EnhancedLibrarianCLI calls to the modern UnifiedLibrarian and search engines.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# We'll use UnifiedLibrarian if it exists, or fall back to basic logic
try:
    from unified_librarian import UnifiedLibrarian
except ImportError:
    UnifiedLibrarian = None

class EnhancedLibrarianCLI:
    """Legacy compatibility shim for EnhancedLibrarianCLI"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        if UnifiedLibrarian:
            self.librarian = UnifiedLibrarian()
        else:
            self.librarian = None
            
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform a semantic search using the modern engine"""
        if self.librarian and hasattr(self.librarian, 'search'):
            return self.librarian.search(query, limit=limit)
        
        self.logger.warning("Search called on shim but UnifiedLibrarian not fully available")
        return []

    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get information about a file"""
        # Could use MetadataService here
        from metadata_service import MetadataService
        service = MetadataService()
        return service.get_metadata(file_path)

    def update_index(self, directory: str):
        """Trigger an index update for a directory"""
        if self.librarian and hasattr(self.librarian, 'index_directory'):
            self.librarian.index_directory(Path(directory))
        else:
            self.logger.info(f"Indexing directory: {directory} (shim no-op)")
