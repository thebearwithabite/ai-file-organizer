
import os
import json
import logging
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

class IdentityService:
    """
    Manages the 'World Model' registry of known identities.
    These identities are injected into Gemini Vision prompts to enable
    recognition of recurring people, pets, and specific locations.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        if not config_dir:
            from gdrive_integration import get_metadata_root
            config_dir = get_metadata_root() / "config"
        
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.identity_file = self.config_dir / "identities.json"
        
        self.logger = logging.getLogger(__name__)
        self.identities = self._load()

    def _load(self) -> Dict[str, Any]:
        """Loads identities from JSON file with default seeding if missing."""
        if self.identity_file.exists():
            try:
                with open(self.identity_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load identities: {e}")
        
        # Default Schema
        default_data = {
            "version": "1.0",
            "identities": {}
        }
        self._save(default_data)
        return default_data

    def _save(self, data: Dict[str, Any]):
        """Atomic write for identity registry."""
        fd, tmp = tempfile.mkstemp(prefix="identities_", dir=str(self.config_dir))
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.identity_file)
        except Exception as e:
            self.logger.error(f"Failed to save identities: {e}")
            if os.path.exists(tmp):
                os.remove(tmp)

    def register_identity(self, id: str, name: str, type: str, description: str, priority: str = "medium") -> bool:
        """Register or update an identity."""
        self.identities["identities"][id] = {
            "id": id,
            "name": name,
            "type": type.lower(), # person, pet, location, object
            "description": description,
            "priority": priority,
            "updated_at": datetime.now().isoformat()
        }
        self._save(self.identities)
        return True

    def get_identity(self, identity_id: str) -> Optional[Dict[str, Any]]:
        return self.identities["identities"].get(identity_id)

    def get_all_identities(self) -> Dict[str, Any]:
        return self.identities["identities"]

    def delete_identity(self, identity_id: str) -> bool:
        if identity_id in self.identities["identities"]:
            del self.identities["identities"][identity_id]
            self._save(self.identities)
            return True
        return False

    def generate_prompt_context(self) -> str:
        """
        Generates a text block describing known identities for injection into Gemini prompts.
        """
        if not self.identities["identities"]:
            return "No specific people or recurring locations are currently indexed in the user's private registry."

        context = "The following specific people, pets, or locations are known to the user. If you see them, identify them by their ID:\n"
        for id, info in self.identities["identities"].items():
            context += f"- [{id}]: {info['name']} ({info['type']}). Visual cues: {info['description']}\n"
        
        context += "\nIf you see recurring entities NOT listed above, please label them as 'Unknown Entity #[Name/ID hint]' so the user can identify them later."
        return context
