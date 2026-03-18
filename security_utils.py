"""
Security utility functions for file operations and path validation.

This module provides essential security functions to prevent path traversal
attacks and other file-based vulnerabilities in the AI File Organizer.

Functions:
    sanitize_filename: Remove path traversal sequences from filenames
    validate_path_within_base: Verify paths stay within allowed directories
"""
import os
import re
from pathlib import Path
from typing import Union
import logging

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str, fallback_prefix: str = "file") -> str:
    """
    Remove path traversal sequences and dangerous characters from filename.

    This function prevents path traversal attacks by:
    1. Extracting just the filename (removing directory components)
    2. Removing path traversal sequences like '../' or '..\\'
    3. Removing potentially dangerous characters
    4. Ensuring a valid filename is always returned

    Args:
        filename: User-provided filename (potentially malicious)
        fallback_prefix: Prefix for generated filenames if input is invalid

    Returns:
        Safe filename without path components or dangerous characters

    Examples:
        >>> sanitize_filename("../../etc/passwd")
        'passwd'
        >>> sanitize_filename("malicious/../../../file.txt")
        'file.txt'
        >>> sanitize_filename("normal_file.pdf")
        'normal_file.pdf'
        >>> sanitize_filename("../../../")
        'file_<hash>'

    Security Notes:
        - Blocks absolute paths (C:\\, /etc/, etc.)
        - Blocks relative paths (../, .\\, etc.)
        - Preserves file extensions for proper handling
        - Always returns a valid, safe filename
    """
    if not filename or not isinstance(filename, str):
        logger.warning(f"Invalid filename type: {type(filename)}")
        return f"{fallback_prefix}_{abs(hash(str(filename)))}"

    # Step 1: Get just the filename, removing any directory components
    # This handles cases like "/etc/passwd" or "C:\\Windows\\System32\\file.txt"
    safe_name = os.path.basename(filename)

    # Step 2: Remove any remaining path traversal attempts
    # Handle both Unix (..) and Windows (..) style traversal
    safe_name = safe_name.replace('..', '').replace('/', '').replace('\\', '')

    # Step 3: Remove potentially dangerous characters
    # Allow only alphanumeric, spaces, dots, dashes, and underscores
    # This prevents issues with special shell characters
    safe_name = re.sub(r'[^\w\s\-\.]', '', safe_name)

    # Step 4: Remove leading/trailing whitespace and dots
    safe_name = safe_name.strip(). strip('.')

    # Step 5: Ensure we have a valid filename
    # If sanitization removed everything, generate a safe filename
    if not safe_name or safe_name in ('.', '..'):
        # Generate a deterministic but safe filename based on original
        safe_name = f"{fallback_prefix}_{abs(hash(filename))}"
        logger.warning(f"Heavily sanitized filename '{filename}' -> '{safe_name}'")

    # Step 6: Limit filename length (common filesystem limit is 255 characters)
    max_length = 255
    if len(safe_name) > max_length:
        # Preserve extension if possible
        name_parts = safe_name.rsplit('.', 1)
        if len(name_parts) == 2:
            name, ext = name_parts
            # Truncate name but keep extension
            safe_name = name[:max_length - len(ext) - 1] + '.' + ext
        else:
            safe_name = safe_name[:max_length]
        logger.info(f"Truncated long filename to {max_length} characters")

    return safe_name


def validate_path_within_base(target_path: Union[Path, str],
                              base_path: Union[Path, str],
                              warn: bool = True) -> bool:
    """
    Verify that target_path is within base_path to prevent path traversal.

    This function prevents attackers from accessing files outside allowed
    directories by resolving both paths to absolute paths and checking
    if the target is a child of the base directory.

    Args:
        target_path: Path to validate (can be relative or absolute)
        base_path: Base directory that must contain target_path
        warn: Whether to log a warning on validation failure (default: True)

    Returns:
        True if target_path is within base_path, False otherwise
    """
    try:
        # Convert strings to Path objects
        if isinstance(target_path, str):
            target_path = Path(target_path)
        if isinstance(base_path, str):
            base_path = Path(base_path)

        # Resolve both paths to absolute paths
        # This resolves symlinks and normalizes the path (removes .. and .)
        target_abs = target_path.resolve()
        base_abs = base_path.resolve()

        # Check if target is relative to base using Python 3.9+ is_relative_to
        # This is the safest way to check path containment
        try:
            is_valid = target_abs.is_relative_to(base_abs)
        except AttributeError:
            # Fallback for Python < 3.9
            try:
                target_abs.relative_to(base_abs)
                is_valid = True
            except ValueError:
                is_valid = False

        if not is_valid and warn:
            logger.warning(
                f"Path validation failed: '{target_path}' is outside '{base_path}' "
                f"(resolved: '{target_abs}' vs '{base_abs}')"
            )

        return is_valid

    except (ValueError, OSError, RuntimeError) as e:
        # Any error in path resolution is treated as invalid (fail-secure)
        logger.error(
            f"Path validation error for '{target_path}' within '{base_path}': {e}"
        )
        return False
    except Exception as e:
        # Catch-all for unexpected errors - fail securely
        logger.error(
            f"Unexpected error in path validation: {e}",
            exc_info=True
        )
        return False


def safe_join_path(base: Union[Path, str], *parts: str) -> Path:
    """
    Safely join path components and validate result stays within base.

    This is a convenience function that combines path joining with
    validation to prevent path traversal attacks.

    Args:
        base: Base directory path
        *parts: Path components to join

    Returns:
        Safe Path object within base directory

    Raises:
        ValueError: If resulting path would be outside base directory

    Examples:
        >>> base = Path("/home/user/uploads")
        >>> safe_join_path(base, "file.txt")
        Path('/home/user/uploads/file.txt')
        >>> safe_join_path(base, "subdir", "file.txt")
        Path('/home/user/uploads/subdir/file.txt')
        >>> safe_join_path(base, "../../etc/passwd")  # Raises ValueError

    Security Notes:
        - Sanitizes each path component
        - Validates final path is within base
        - Raises exception rather than returning unsafe path
    """
    if isinstance(base, str):
        base = Path(base)

    # Sanitize each part
    safe_parts = [sanitize_filename(part) for part in parts]

    # Join the paths
    result_path = base.joinpath(*safe_parts)

    # Validate the result is within base
    if not validate_path_within_base(result_path, base):
        raise ValueError(
            f"Resulting path '{result_path}' would be outside base directory '{base}'"
        )

    return result_path
