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
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

class HierarchicalOrganizer:
    """Intelligently detect project, episode, and media type structure"""

    # Static Seed (Fallback)
    STATIC_KNOWLEDGE = {
        'the_papers_that_dream': 'The Papers That Dream',
        'papers_that_dream': 'The Papers That Dream',
        'ptd': 'The Papers That Dream',
        'attention_island': 'Attention Island',
        'attentionisland': 'Attention Island',
        'csc': 'The_Papers_That_Dream',
        'veo_prompt': 'VEO_Prompt_Machine',
        'veo': 'VEO_Prompt_Machine',
        'ai_file_organizer': 'AI_File_Organizer',
        'calibration_vector': 'Calibration_Vector',
    }

    # Media type mapping
    MEDIA_TYPE_MAP = {
        'mp4': 'Video', 'mov': 'Video', 'avi': 'Video', 'mkv': 'Video', 'webm': 'Video', 'flv': 'Video',
        'mp3': 'Audio', 'wav': 'Audio', 'flac': 'Audio', 'aiff': 'Audio', 'm4a': 'Audio', 'ogg': 'Audio',
        'jpg': 'Images', 'jpeg': 'Images', 'png': 'Images', 'gif': 'Images', 'webp': 'Images', 'heic': 'Images', 'heif': 'Images', 'bmp': 'Images',
        'pdf': 'Documents', 'docx': 'Documents', 'doc': 'Documents', 'txt': 'Documents', 'md': 'Documents', 'pages': 'Documents',
        'py': 'Scripts', 'js': 'Scripts', 'ts': 'Scripts', 'jsx': 'Scripts', 'tsx': 'Scripts', 'sh': 'Scripts',
        'json': 'JSON_Prompts', 'csv': 'Cue_Sheets', 'xlsx': 'Cue_Sheets', 'xls': 'Cue_Sheets',
    }

    def __init__(self, taxonomy_service: Optional[Any] = None):
        """Initialize the hierarchical organizer with V2 Robust Dynamic Registry"""
        self.logger = logging.getLogger(__name__)
        self.dynamic_projects_path = Path.home() / "Documents" / "AI_METADATA_SYSTEM" / "config" / "dynamic_projects.json"
        
        # Instance-scoped storage (Prevents cross-instance bleed)
        self.registries = {"projects": {}}
        self.known_projects = dict(self.STATIC_KNOWLEDGE)
        
        # Safe Roots for Learning (Prevent junk from Downloads)
        self.project_roots = ["01_ACTIVE_PROJECTS", "02_ARCHIVE", "Creative_Projects"]
        
        # V3 Taxonomy Service Integration
        if taxonomy_service:
            self.taxonomy_service = taxonomy_service
        else:
            try:
                from taxonomy_service import TaxonomyService
                from gdrive_integration import get_metadata_root
                config_dir = get_metadata_root() / "config"
                self.taxonomy_service = TaxonomyService.get_instance(config_dir)
            except Exception as e:
                self.logger.error(f"Failed to load TaxonomyService: {e}")
                self.taxonomy_service = None
        
        self._load_dynamic_projects()

    def get_media_type_folder(self, category_id: str) -> str:
        """
        Get the folder name for a category using V3 Taxonomy.
        """
        if self.taxonomy_service:
            cat = self.taxonomy_service.get_category(category_id)
            if cat:
                # Taxonomy returns path like "Visual_Assets/Screenshots"
                # But here we might just want the subfolder name if we handle parent separately?
                # Actually, V3 organizer should respect the full path structure defined in Taxonomy ("Visual_Assets/Screenshots").
                # But legacy logic might expect a single folder name.
                
                # If the category defines a folder_name and parent_path:
                folder = cat.get("folder_name", "Other")
                parent = cat.get("parent_path", "")
                
                # If we are building a path inside a Project/Episode, we might just append the folder?
                # Or do we respect the "Visual_Assets" parent?
                # Ideally: Project/Episode/Visual_Assets/Screenshots
                
                if parent:
                    return f"{parent}/{folder}"
                return folder
        
        # Fallback for unknown categories or if service fails
        return "Other"

    def _tokens(self, s: str) -> set[str]:
        """Normalize string into tokens for safe matching"""
        import re
        s = s.lower()
        parts = re.split(r"[^a-z0-9]+", s)
        return {p for p in parts if len(p) >= 3}

    def normalize_key(self, name: str) -> str:
        """Strong normalization for collision avoidance"""
        s = name.strip().lower()
        s = re.sub(r'[\s\-]+', '_', s)       # spaces + hyphens -> _
        s = re.sub(r'[^a-z0-9_]+', '', s)    # drop punctuation
        s = re.sub(r'_+', '_', s).strip('_') # collapse underscores
        return s

    def _atomic_write_json(self, path: Path, data: dict):
        """Atomic write to prevent corruption"""
        import json, os, tempfile
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)  # atomic on mac/linux
        finally:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass

    def _load_dynamic_projects(self):
        """Load dynamically learned projects from JSON (V2 Schema)"""
        import json
        try:
            if self.dynamic_projects_path.exists():
                with open(self.dynamic_projects_path, 'r') as f:
                    data = json.load(f)
                    # Support V2 Registry Schema
                    if "projects" in data and isinstance(data["projects"], dict):
                        self.registries = data
                        # Populate known_projects for fast lookup
                        for pid, pdata in self.registries["projects"].items():
                            if pdata.get("status") in ["verified", "observed"]:
                                # Add main name
                                norm_name = self.normalize_key(pdata["name"])
                                self.known_projects[norm_name] = pdata["name"]
                                # Add aliases
                                for alias in pdata.get("aliases", []):
                                    self.known_projects[self.normalize_key(alias)] = pdata["name"]
                    else:
                        # V1 Legacy Fallback (Simple Dict)
                        for k, v in data.items():
                            self.known_projects[self.normalize_key(k)] = v
        except Exception as e:
            self.logger.warning(f"Failed to load dynamic projects: {e}")

    def register_project(self, project_name: str, folder_path: str, status: str = "observed"):
        """
        Register a project in the dynamic registry (V2).
        Uses UUID identity and Atomic persistence.
        """
        import json
        import uuid
        
        # 1. Scope Check
        path_obj = Path(folder_path)
        is_safe = any(root in str(path_obj) for root in self.project_roots)
        if not is_safe:
            self.logger.info(f"Skipping project registration: {project_name} (Outside allowed roots)")
            return

        # 2. Identity & Marker (Stable ID)
        project_id = self._get_or_create_project_id(path_obj, project_name)
        
        # 3. Update Registry
        entry = {
            "id": project_id,
            "name": project_name,
            "path": str(folder_path),
            "status": status,
            "last_seen": datetime.now().isoformat(),
            "aliases": [project_name]
        }
        
        # Merge if exists
        if project_id in self.registries["projects"]:
            existing = self.registries["projects"][project_id]
            entry["aliases"] = list(set(existing.get("aliases", []) + [project_name]))
            # Preserve verified status
            if existing.get("status") == "verified":
                entry["status"] = "verified"
        
        self.registries["projects"][project_id] = entry
        
        # 4. Update Runtime Lookup
        norm_key = self.normalize_key(project_name)
        self.known_projects[norm_key] = project_name
        
        self._atomic_write_json(self.dynamic_projects_path, self.registries)

    def _get_or_create_project_id(self, path: Path, name: str) -> str:
        """Get ID from marker or generate new one"""
        import uuid
        import json
        
        marker_path = path / ".project.json"
        if marker_path.exists():
            try:
                with open(marker_path, 'r') as f:
                    data = json.load(f)
                    return data.get("project_id", str(uuid.uuid4()))
            except:
                pass
        
        # Generate new ID (Caller responsible for writing marker if verified)
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(path)))

    def detect_project_from_filename(self, filename: str) -> Optional[str]:
        """Detect project name from filename using token matching"""
        tokens = self._tokens(filename)
        
        # Check against known projects (includes static + dynamic)
        for key, project_name in self.known_projects.items():
            # Check if key (normalized) is present as a token or sub-token
            # Simple token check for now as requested
            if key in tokens:
                return project_name
                
            # Fallback: check if key is inside filename (string match) 
            # ONLY if key length >= 4 to avoid short noise like 'ai' or 'is'
            if len(key) >= 4 and key in filename.lower():
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

    def detect_chapter_from_filename(self, filename: str) -> Optional[str]:
        """Detect chapter information (Ch 1, Chapter 2) from filename"""
        filename_lower = filename.lower()
        # Pattern: Chapter 1, Ch 1, Chap 1
        # Use more restrictive matching to avoid taking the whole filename
        match = re.search(r'(?:chap(?:ter)?|ch)[_\s]*(\d+)', filename_lower)
        if match:
            ch_num = match.group(1)
            # Find a short name following (limit to 2 words max)
            name_match = re.search(r'(?:chap(?:ter)?|ch)[_\s]*' + ch_num + r'[_\s\-]*([a-z0-9_]{1,15})', filename_lower)
            if name_match:
                name = name_match.group(1).strip().title()
                if name:
                    return f"-Chapter {ch_num} - {name}"
            return f"-Chapter {ch_num}"
        return None

    def detect_client_from_filename(self, filename: str) -> Optional[str]:
        """Detect client name from filename (e.g. Finn Wolhard)"""
        # For now, let's use a simple list or assume if it's in Business/Clients root it's a client
        # In the future, we can query a dynamic_clients.json
        tokens = self._tokens(filename)
        filename_clean = filename.lower().replace('_', ' ')
        
        # Hardcoded seeding from user's examples
        seed_clients = {
            "Finn Wolhard": ["finn", "wolhard"],
            "Danielle Reha": ["danielle", "reha"]
        }
        
        for name, keywords in seed_clients.items():
            # Check if all keywords are present in filename
            if all(k in filename_clean for k in keywords):
                return name
        return None
    def get_media_type(self, file_path: Path) -> str:
        """
        Get media type folder name based on extension (Taxonomy V3 Aware).
        Fallback to 'Other' if unknown.
        """
        extension = file_path.suffix.lower()
        if self.taxonomy_service:
            cats = self.taxonomy_service.get_all_categories()
            for cat_id, data in cats.items():
                if extension in data.get("extensions", []):
                    # Taxonomy returns folder name (e.g. "Installers")
                    # If it has a parent path, we might want to include it?
                    # For now, let's defer to get_media_type_folder which handles structure
                    return data.get("folder_name", "Other")
        
        # Fallback if taxonomy missing or no match
        return "Other"

    def is_known_media_extension(self, extension: str) -> bool:
        """Check if extension matches any taxonomy category"""
        if not extension.startswith('.'): extension = f".{extension}"
        extension = extension.lower()
        
        if self.taxonomy_service:
            cats = self.taxonomy_service.get_all_categories()
            for data in cats.values():
                if extension in data.get("extensions", []):
                    return True
        return False

    def build_hierarchical_path(
        self,
        base_category: str,
        file_path: Path,
        project_override: Optional[str] = None,
        episode_override: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build a hierarchical path for file organization using V3 Taxonomy
        and the "Golden Hierarchy" templates.
        """
        filename = file_path.name
        cat_data = None
        if self.taxonomy_service:
            cat_data = self.taxonomy_service.get_category(base_category)
            
        # --- Root & Subfolder Resolution ---
        if cat_data:
            root = cat_data.get("parent_path", "99_TEMP_PROCESSING/Manual_Review")
            media_folder = cat_data.get("folder_name", "Other")
        else:
            # Smart Fallback for unknown categories (e.g. AI suggested a new one)
            # Try to determine a sensible root based on file extension
            extension = file_path.suffix.lower().lstrip('.')
            media_type = self.MEDIA_TYPE_MAP.get(extension, "Other")
            
            # Map media type to a sensible default root
            if media_type in ["Scripts", "Code", "JSON_Prompts"]:
                # --- IMPROVEMENT: Stay in Projects if a project is detected ---
                project_peek = self.detect_project_from_filename(filename)
                if project_peek:
                    root = "Projects"
                    media_folder = "JSON_Prompts" if media_type == "JSON_Prompts" else "Scripts"
                else:
                    root = "Technology"
                    media_folder = "Scripts" if media_type == "Scripts" else "Data"
            elif media_type == "Images":
                root = "Personal"
                media_folder = "Photos"
            elif media_type == "Audio":
                root = "Projects"
                media_folder = "Audio"
            elif media_type == "Video":
                root = "Projects"
                media_folder = "Video"
            elif media_type == "3D":
                root = "Projects"
                media_folder = "3D Assets"
            elif media_type == "Design":
                root = "Projects"
                media_folder = "Design Assets"
            elif media_type in ["Archives", "Executables", "DiscImages"]:
                root = "99_TEMP_PROCESSING/Software & Archives"
                media_folder = media_type
            else:
                # Absolute fallback
                root = "99_TEMP_PROCESSING/Manual_Review"
                media_folder = "Other"
            
            self.logger.info(f"Unknown category '{base_category}' -> Smart mapped to {root}/{media_folder} based on extension {extension}")
        
        # 2. Entity Detection
        project = project_override or self.detect_project_from_filename(filename)
        episode = episode_override or self.detect_episode_from_filename(filename)
        chapter = self.detect_chapter_from_filename(filename)
        client = self.detect_client_from_filename(filename)
        
        # Metadata for trace/API
        metadata = {
            'project': project,
            'episode': episode,
            'chapter': chapter,
            'client': client,
            'media_type': media_folder,
            'category_id': base_category,
            'hierarchy_level': 0
        }

        path_parts = [root]

        # --- TEMPLATE: PROJECTS ---
        if root == "Projects" and project:
            path_parts.append(project)
            if episode:
                path_parts.append("- Episodes")
                if chapter:
                    path_parts.append(chapter)
                else:
                    path_parts.append(episode)
                
                # Functional Subfolder (User's style: - Music, - SFX, etc.)
                func_folder = f"- {media_folder}" if not media_folder.startswith('-') else media_folder
                # Handle "Working Files" layer if it's a media asset
                if any(x in base_category.lower() for x in ['video', 'audio', 'images', 'sfx', 'music', 'vox']):
                    path_parts.append("- Working Files")
                
                path_parts.append(func_folder)
            else:
                # Top level project asset
                path_parts.append(f"- {media_folder}")

        # --- TEMPLATE: BUSINESS MANAGEMENT (CLIENTS) ---
        elif root == "Business Management" and client:
            path_parts.append("Clients")
            path_parts.append(f"- {client}")
            path_parts.append(f"- {media_folder}")

        # --- TEMPLATE: GENERAL ---
        elif base_category != 'unknown':
            # Default to Taxonomy's preferred folder_name
            if cat_data:
                # We already have root from parent_path
                # Just add the leaf folder
                folder = cat_data.get("folder_name", "Other")
                path_parts.append(folder)
            else:
                path_parts.append(media_folder)

        final_path = '/'.join(path_parts)
        metadata['hierarchy_level'] = len(path_parts)

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
