#!/usr/bin/env python3
"""
Hierarchical Organization Helper
Detects project, episode, and media type from filenames and content
to enable deep folder organization structures.

Example structure:
01_ACTIVE_PROJECTS/
  ├── Creative_Projects/
  │   ├── The_Papers_That_Dream/
  │   │   ├── Episode_02_AttentionIsland/
  │   │   │   ├── Video/
  │   │   │   ├── Audio/
  │   │   │   ├── Images/
  │   │   │   ├── Scripts/
  │   │   │   └── JSON_Prompts/
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

class HierarchicalOrganizer:
    """Intelligently detect project, episode, and media type structure"""

    # Known projects (can be expanded dynamically)
    KNOWN_PROJECTS = {
        'the_papers_that_dream': 'The_Papers_That_Dream',
        'papers_that_dream': 'The_Papers_That_Dream',
        'veo_prompt': 'VEO_Prompt_Machine',
        'veo': 'VEO_Prompt_Machine',
        'ai_file_organizer': 'AI_File_Organizer',
        'calibration_vector': 'Calibration_Vector',
    }

    # Media type mapping
    MEDIA_TYPE_MAP = {
        # Video formats
        'mp4': 'Video',
        'mov': 'Video',
        'avi': 'Video',
        'mkv': 'Video',
        'webm': 'Video',
        'flv': 'Video',

        # Audio formats
        'mp3': 'Audio',
        'wav': 'Audio',
        'flac': 'Audio',
        'aiff': 'Audio',
        'm4a': 'Audio',
        'ogg': 'Audio',

        # Image formats
        'jpg': 'Images',
        'jpeg': 'Images',
        'png': 'Images',
        'gif': 'Images',
        'webp': 'Images',
        'heic': 'Images',
        'heif': 'Images',
        'bmp': 'Images',

        # Document formats
        'pdf': 'Documents',
        'docx': 'Documents',
        'doc': 'Documents',
        'txt': 'Documents',
        'md': 'Documents',
        'pages': 'Documents',

        # Script formats
        'py': 'Scripts',
        'js': 'Scripts',
        'ts': 'Scripts',
        'jsx': 'Scripts',
        'tsx': 'Scripts',
        'sh': 'Scripts',

        # JSON/Data formats (for VEO prompts, cue sheets, etc.)
        'json': 'JSON_Prompts',
        'csv': 'Cue_Sheets',
        'xlsx': 'Cue_Sheets',
        'xls': 'Cue_Sheets',
    }

    def __init__(self):
        """Initialize the hierarchical organizer"""
        pass

    def detect_project_from_filename(self, filename: str) -> Optional[str]:
        """
        Detect project name from filename

        Args:
            filename: The filename to analyze

        Returns:
            Detected project name or None
        """
        filename_lower = filename.lower()

        # Check for known project keywords
        for keyword, project_name in self.KNOWN_PROJECTS.items():
            if keyword in filename_lower:
                return project_name

        return None

    def detect_episode_from_filename(self, filename: str) -> Optional[str]:
        """
        Detect episode information from filename

        Examples:
            "Episode_02_AttentionIsland" -> "Episode_02_AttentionIsland"
            "ep02_attention_island" -> "Episode_02_AttentionIsland"
            "e02" -> "Episode_02"

        Args:
            filename: The filename to analyze

        Returns:
            Detected episode name or None
        """
        filename_lower = filename.lower()

        # Pattern 1: "Episode_02_Name" or "episode 02 name"
        match = re.search(r'episode[_\s]*(\d+)[_\s]*([a-z0-9_\s]*)', filename_lower, re.IGNORECASE)
        if match:
            episode_num = match.group(1).zfill(2)
            episode_name = match.group(2).strip('_').strip()
            if episode_name:
                # Convert to title case with underscores
                episode_name = episode_name.replace(' ', '_').replace('-', '_')
                episode_name = ''.join(word.capitalize() for word in episode_name.split('_'))
                return f"Episode_{episode_num}_{episode_name}"
            else:
                return f"Episode_{episode_num}"

        # Pattern 2: "ep02" or "e02"
        match = re.search(r'e(?:p)?(\d+)', filename_lower)
        if match:
            episode_num = match.group(1).zfill(2)
            return f"Episode_{episode_num}"

        return None

    def get_media_type(self, file_path: Path) -> str:
        """
        Get media type subfolder based on file extension

        Args:
            file_path: Path to the file

        Returns:
            Media type folder name (e.g., "Video", "Audio", "Images")
        """
        extension = file_path.suffix.lower().lstrip('.')
        return self.MEDIA_TYPE_MAP.get(extension, 'Other')

    def build_hierarchical_path(
        self,
        base_category: str,
        file_path: Path,
        project_override: Optional[str] = None,
        episode_override: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build a hierarchical path for file organization

        Args:
            base_category: The base category (e.g., 'creative', 'development')
            file_path: Path to the file being organized
            project_override: Optional manual project name
            episode_override: Optional manual episode name

        Returns:
            Tuple of (relative_path, metadata_dict)
        """
        filename = file_path.name

        # Detect or use override for project
        project = project_override or self.detect_project_from_filename(filename)

        # Detect or use override for episode
        episode = episode_override or self.detect_episode_from_filename(filename)

        # Sanitize episode name: prevent filenames from being used as directory names
        if episode and '.' in episode:
            # Check if it ends with a known media extension (indicating user likely pasted a filename)
            parts = episode.rsplit('.', 1)
            if len(parts) > 1:
                ext = parts[1].lower()
                if ext in self.MEDIA_TYPE_MAP:
                    # It's likely a mistake - we need to extract the meaningful name
                    if '/' in episode or '\\' in episode:
                        # If it looks like a path (e.g. "Episode_01/File.png"), take the parent folder
                        # Normalize slashes
                        normalized_episode = episode.replace('\\', '/')
                        # Remove the filename component
                        parent_dir = normalized_episode.rsplit('/', 1)[0]
                        # If there are still slashes, take the last component (the folder name)
                        if '/' in parent_dir:
                            episode = parent_dir.split('/')[-1]
                        else:
                            episode = parent_dir
                    else:
                        # Just a filename (e.g. "File.png") - strip extension
                        episode = parts[0]

        # Get media type
        media_type = self.get_media_type(file_path)

        # Build the path based on detected components
        metadata = {
            'project': project,
            'episode': episode,
            'media_type': media_type,
            'hierarchy_level': 0
        }

        # Base path mapping
        category_base_paths = {
            'creative': '01_ACTIVE_PROJECTS/Creative_Projects',
            'entertainment': '01_ACTIVE_PROJECTS/Entertainment_Industry',
            'development': '01_ACTIVE_PROJECTS/Development_Projects',
            'financial': '01_ACTIVE_PROJECTS/Business_Operations/Financial_Records',
            'audio': '01_ACTIVE_PROJECTS/Creative_Projects',
            'image': '01_ACTIVE_PROJECTS/Creative_Projects',
            'video': '01_ACTIVE_PROJECTS/Creative_Projects',
            'text_document': '02_REFERENCE/Documents',
            'unknown': '99_TEMP_PROCESSING/Manual_Review'
        }

        base_path = category_base_paths.get(base_category.lower(), '99_TEMP_PROCESSING/Manual_Review')
        path_parts = [base_path]
        metadata['hierarchy_level'] = 2  # Base: level 2 (01_ACTIVE/Creative_Projects)

        # Add project level if detected
        if project:
            path_parts.append(project)
            metadata['hierarchy_level'] = 3

            # Add episode level if detected
            if episode:
                path_parts.append(episode)
                metadata['hierarchy_level'] = 4

                # Add media type level (only if we have episode)
                path_parts.append(media_type)
                metadata['hierarchy_level'] = 5

        # If no project but we have a creative file, just use media type
        elif base_category.lower() in ['creative', 'audio', 'image', 'video']:
            # Generic creative content organization
            path_parts.append('Uncategorized')
            path_parts.append(media_type)
            metadata['hierarchy_level'] = 3

        final_path = '/'.join(path_parts)

        return final_path, metadata

    def suggest_organization(self, file_path: Path, ai_category: str) -> Dict[str, Any]:
        """
        Suggest complete organization structure for a file

        Args:
            file_path: Path to the file
            ai_category: AI-detected category

        Returns:
            Dict with suggested path, project, episode, media_type, and reasoning
        """
        relative_path, metadata = self.build_hierarchical_path(ai_category, file_path)

        reasoning_parts = []

        if metadata['project']:
            reasoning_parts.append(f"Project detected: {metadata['project']}")

        if metadata['episode']:
            reasoning_parts.append(f"Episode detected: {metadata['episode']}")

        reasoning_parts.append(f"Media type: {metadata['media_type']}")
        reasoning_parts.append(f"Organization depth: Level {metadata['hierarchy_level']}")

        return {
            'suggested_path': relative_path,
            'project': metadata['project'],
            'episode': metadata['episode'],
            'media_type': metadata['media_type'],
            'hierarchy_level': metadata['hierarchy_level'],
            'reasoning': ' | '.join(reasoning_parts)
        }


# Helper function for easy import
def get_hierarchical_path(base_category: str, file_path: Path, project: Optional[str] = None, episode: Optional[str] = None) -> str:
    """
    Convenience function to get hierarchical path

    Args:
        base_category: Base category (e.g., 'creative')
        file_path: Path to file
        project: Optional project name
        episode: Optional episode name

    Returns:
        Relative path string
    """
    organizer = HierarchicalOrganizer()
    path, _ = organizer.build_hierarchical_path(base_category, file_path, project, episode)
    return path
