#!/usr/bin/env python3
"""
Centralized Path Configuration for AI File Organizer
Handles dynamic path resolution for different user environments and ADHD-friendly workflows
"""

import os
from pathlib import Path
from typing import Dict, Optional


class PathConfig:
    """
    Centralized path management for ADHD-friendly file organization
    
    Provides dynamic path resolution that works across different:
    - User accounts and home directories
    - Operating system configurations
    - Installation locations
    - Development vs production environments
    """
    
    def __init__(self):
        """Initialize path configuration with dynamic detection"""
        self.base_paths = self._initialize_paths()
        self._validate_critical_paths()
    
    def _initialize_paths(self) -> Dict[str, Path]:
        """
        Initialize all system paths dynamically
        
        Uses environment variables and system detection to ensure
        compatibility across different user environments
        """
        
        # Get user home directory dynamically (works for any username)
        home = Path.home()
        
        # Allow environment variable override for flexibility
        # This supports custom installations and development setups
        base_override = os.getenv('AI_ORGANIZER_BASE')
        if base_override:
            base = Path(base_override)
            print(f"🔧 Using custom base path from environment: {base}")
        else:
            # Default to user's home directory
            base = home
        
        # Detect current installation directory dynamically
        # This works regardless of where the code is cloned/installed
        current_file = Path(__file__).resolve()
        organizer_base = current_file.parent
        
        # Centralized local metadata root (Rule #1 compliance)
        metadata_root = home / 'Documents' / 'AI_METADATA_SYSTEM'
        
        return {
            # User directories (standard across all systems)
            'home': home,
            'documents': base / 'Documents',
            'downloads': base / 'Downloads', 
            'desktop': base / 'Desktop',
            
            # AI Organizer specific directories (SYSTEM ONLY)
            'organizer_base': organizer_base,
            
            # Metadata System (LOCAL ONLY - Rule #1 & #5)
            'metadata_root': metadata_root,
            'logs': metadata_root / 'logs',
            'cache': metadata_root / 'cache',
            'config': metadata_root / 'config',
            
            # Database and storage (STRICTLY LOCAL)
            'metadata_db': metadata_root / 'databases' / 'metadata.db',
            'vector_db': metadata_root / 'databases' / 'vector_store',
            
            # Configuration files
            'user_preferences': metadata_root / 'config' / 'user_preferences.json',
            'classification_rules': metadata_root / 'config' / 'classification_rules.json',
            
            # Temporary and processing directories (Managed by Rules)
            'temp_processing': base / 'Documents' / 'TEMP_PROCESSING',
            'staging': metadata_root / 'staging',
            'backups': metadata_root / 'backups'
        }
    
    def _validate_critical_paths(self):
        """Validate that critical paths are accessible"""
        critical_paths = ['home', 'organizer_base']
        
        for key in critical_paths:
            path = self.base_paths[key]
            if not path.exists():
                if key == 'organizer_base':
                    raise FileNotFoundError(f"AI Organizer installation directory not found: {path}")
                else:
                    print(f"⚠️  Warning: {key} path does not exist: {path}")
    
    def get_path(self, key: str) -> Path:
        """
        Get path by key with validation
        
        Args:
            key: Path identifier (e.g., 'documents', 'logs', 'metadata_db')
            
        Returns:
            Path object for the requested key
            
        Raises:
            ValueError: If key is not recognized
        """
        if key not in self.base_paths:
            available_keys = list(self.base_paths.keys())
            raise ValueError(f"Unknown path key: '{key}'. Available keys: {available_keys}")
        
        return self.base_paths[key]
    
    def get_user_documents_path(self) -> Path:
        """Get user's documents directory (ADHD workflow entry point)"""
        return self.get_path('documents')
    
    def get_organizer_base_path(self) -> Path:
        """Get AI organizer installation directory"""
        return self.get_path('organizer_base')
    
    def get_metadata_db_path(self) -> Path:
        """Get metadata database file path"""
        return self.get_path('metadata_db')
    
    def get_logs_directory(self) -> Path:
        """Get logs directory path"""
        return self.get_path('logs')
    
    def create_required_directories(self, verbose: bool = True):
        """
        Ensure all required directories exist
        
        Creates directories that the AI organizer manages,
        but respects user directories that should already exist
        """
        # Only create directories that we manage (not user directories)
        managed_dir_keys = [
            'logs', 'cache', 'config', 'temp_processing', 
            'staging', 'backups', 'vector_db'
        ]
        
        created_dirs = []
        for key in managed_dir_keys:
            try:
                path = self.get_path(key)
                # For file paths (like metadata_db), create parent directory
                if path.suffix:  # Has file extension, so it's a file path
                    dir_to_create = path.parent
                else:  # It's a directory path
                    dir_to_create = path
                
                if not dir_to_create.exists():
                    dir_to_create.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(dir_to_create)
                    if verbose:
                        print(f"✅ Created directory: {dir_to_create}")
                        
            except (KeyError, PermissionError) as e:
                if verbose:
                    print(f"⚠️  Could not create directory for {key}: {e}")
        
        if verbose and created_dirs:
            print(f"📁 Created {len(created_dirs)} required directories")
        elif verbose:
            print("📁 All required directories already exist")
        
        return len(created_dirs)  # Return count for testing
    
    def get_user_specific_path(self, relative_path: str) -> Path:
        """
        Get a user-specific path relative to documents
        
        Useful for ADHD workflows that need predictable locations
        relative to the user's document folder
        """
        return self.get_user_documents_path() / relative_path
    
    def resolve_legacy_path(self, legacy_path: str) -> Path:
        """
        Resolve legacy hardcoded paths to dynamic equivalents
        
        Args:
            legacy_path: Old hardcoded path string
            
        Returns:
            Dynamically resolved Path object
        """
        legacy_path = str(legacy_path)
        
        # Replace any hardcoded user patterns with dynamic equivalents
        import re
        
        # Pattern to match /Users/[username]/... paths
        user_pattern = r'/Users/[^/]+/'
        
        # Replace common directory patterns
        if re.search(user_pattern + 'Documents', legacy_path):
            resolved_path = re.sub(user_pattern + 'Documents', str(self.get_path('documents')) + '/', legacy_path)
        elif re.search(user_pattern + 'Downloads', legacy_path):
            resolved_path = re.sub(user_pattern + 'Downloads', str(self.get_path('downloads')) + '/', legacy_path)
        elif re.search(user_pattern + 'Desktop', legacy_path):
            resolved_path = re.sub(user_pattern + 'Desktop', str(self.get_path('desktop')) + '/', legacy_path)
        elif re.search(user_pattern + 'Github/ai-file-organizer', legacy_path):
            resolved_path = re.sub(user_pattern + 'Github/ai-file-organizer', str(self.get_path('organizer_base')), legacy_path)
        else:
            # If no specific pattern matched, return as-is
            resolved_path = legacy_path
        
        return Path(resolved_path)
    
    def get_environment_info(self) -> Dict[str, str]:
        """Get environment information for debugging"""
        return {
            'user': os.getenv('USER', 'unknown'),
            'home': str(Path.home()),
            'cwd': str(Path.cwd()),
            'organizer_base': str(self.get_path('organizer_base')),
            'python_path': str(Path(__file__).parent),
            'ai_organizer_base_override': os.getenv('AI_ORGANIZER_BASE', 'not_set')
        }
    
    def __str__(self) -> str:
        """String representation for debugging"""
        lines = ["AI File Organizer - Path Configuration:"]
        for key, path in sorted(self.base_paths.items()):
            exists = "✅" if path.exists() else "❌"
            lines.append(f"  {exists} {key:20} -> {path}")
        return "\n".join(lines)


# Global path configuration instance
# This provides a singleton pattern for consistent path access throughout the application
paths = PathConfig()


def get_dynamic_path(key: str) -> Path:
    """
    Convenience function for getting paths
    
    Args:
        key: Path identifier
        
    Returns:
        Path object for the requested key
    """
    return paths.get_path(key)


def ensure_organizer_directories():
    """
    Convenience function to ensure all organizer directories exist
    Safe to call multiple times
    """
    paths.create_required_directories()


def migrate_legacy_path(legacy_path: str) -> Path:
    """
    Convenience function for migrating legacy hardcoded paths
    
    Args:
        legacy_path: Old hardcoded path string
        
    Returns:
        Dynamically resolved Path object
    """
    return paths.resolve_legacy_path(legacy_path)


if __name__ == "__main__":
    """
    Command-line interface for path configuration testing and debugging
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="AI File Organizer Path Configuration")
    parser.add_argument('--show', action='store_true', help='Show all configured paths')
    parser.add_argument('--create-dirs', action='store_true', help='Create required directories')
    parser.add_argument('--env-info', action='store_true', help='Show environment information')
    parser.add_argument('--test-path', help='Test resolving a specific path key')
    parser.add_argument('--migrate-legacy', help='Test migrating a legacy path')
    
    args = parser.parse_args()
    
    if args.show:
        print(paths)
    
    if args.create_dirs:
        print("Creating required directories...")
        ensure_organizer_directories()
    
    if args.env_info:
        print("\nEnvironment Information:")
        env_info = paths.get_environment_info()
        for key, value in env_info.items():
            print(f"  {key}: {value}")
    
    if args.test_path:
        try:
            path = get_dynamic_path(args.test_path)
            exists = "exists" if path.exists() else "does not exist"
            print(f"Path '{args.test_path}' resolves to: {path} ({exists})")
        except ValueError as e:
            print(f"Error: {e}")
    
    if args.migrate_legacy:
        original = args.migrate_legacy
        migrated = migrate_legacy_path(original)
        print(f"Legacy path migration:")
        print(f"  Original: {original}")
        print(f"  Migrated: {migrated}")
        print(f"  Exists: {'yes' if migrated.exists() else 'no'}")
    
    if not any(vars(args).values()):
        print("AI File Organizer Path Configuration System")
        print("Use --help for available options")
        print(f"\nCurrent user: {os.getenv('USER', 'unknown')}")
        print(f"Installation directory: {paths.get_path('organizer_base')}")
        print(f"Documents directory: {paths.get_path('documents')}")