#!/usr/bin/env python3
"""
File Classification Engine with Confidence Scoring
Inspired by AI-Audio-Organizer approach with confidence-based automation
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import mimetypes

@dataclass
class ClassificationResult:
    """Result of file classification"""
    category: str
    subcategory: str
    confidence: float
    suggested_path: str
    reasoning: List[str]
    tags: List[str]
    people: List[str]
    projects: List[str]

class FileClassificationEngine:
    """
    Intelligent file classification with confidence scoring
    Maps files to organized folder structure based on content analysis
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents"
        self.rules_path = self.base_dir / "04_METADATA_SYSTEM" / "classification_rules.json"
        
        # Load classification rules
        self._load_classification_rules()
        
        # Folder structure mapping
        self.folder_structure = {
            "entertainment": "01_ACTIVE_PROJECTS/Entertainment_Industry",
            "creative": "01_ACTIVE_PROJECTS/Creative_Projects", 
            "development": "01_ACTIVE_PROJECTS/Development_Projects",
            "business": "01_ACTIVE_PROJECTS/Business_Operations",
            "financial": "01_ACTIVE_PROJECTS/Business_Operations/Financial",
            "audio": "02_MEDIA_ASSETS/Audio",
            "visual": "02_MEDIA_ASSETS/Visual", 
            "templates": "02_MEDIA_ASSETS/Templates",
            "archive": "03_ARCHIVE_REFERENCE",
            "temp": "99_TEMP_PROCESSING"
        }
    
    def _load_classification_rules(self):
        """Load classification rules from JSON file"""
        if self.rules_path.exists():
            with open(self.rules_path, 'r') as f:
                loaded_data = json.load(f)
            
            # Adapt the existing rules structure to our engine format
            self.rules = {
                "people_indicators": {
                    "finn_wolfhard": ["finn", "wolfhard", "stranger things", "netflix"],
                    "business_contacts": ["refinery", "payment report", "contract", "agreement"]
                },
                "project_indicators": {
                    "stranger_things": ["stranger", "things", "netflix", "hawkins"], 
                    "papers_that_dream": ["papers", "dream", "screenplay"],
                    "refinery": ["refinery", "payment", "residual"]
                },
                "document_types": {},
                "confidence_thresholds": {
                    "auto_organize": loaded_data.get("confidence_thresholds", {}).get("auto_move", 0.8),
                    "suggest_organization": loaded_data.get("confidence_thresholds", {}).get("suggest_move", 0.6),
                    "manual_review": loaded_data.get("confidence_thresholds", {}).get("manual_review", 0.4)
                }
            }
            
            # Convert classification_rules to our document_types format
            classification_rules = loaded_data.get("classification_rules", {})
            for category, rules in classification_rules.items():
                self.rules["document_types"][category] = {
                    "keywords": rules.get("keywords", []),
                    "extensions": rules.get("file_types", []),
                    "confidence_boost": 0.3,
                    "target_folder": self._map_category_to_folder(category)
                }
            
            # Add some common extensions that might be missing
            if "audio_files" not in self.rules["document_types"]:
                self.rules["document_types"]["audio_files"] = {
                    "keywords": ["audio", "sound", "music"],
                    "extensions": [".mp3", ".wav", ".aiff", ".m4a", ".flac"],
                    "confidence_boost": 0.4,
                    "target_folder": "audio"
                }
            
            if "visual_files" not in self.rules["document_types"]:
                self.rules["document_types"]["visual_files"] = {
                    "keywords": ["image", "photo", "picture"],
                    "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
                    "confidence_boost": 0.4,
                    "target_folder": "visual"
                }
                
        else:
            # Create default rules if none exist
            self.rules = {
                "people_indicators": {
                    "finn_wolfhard": ["finn", "wolfhard", "stranger things", "netflix"],
                    "business_contacts": ["refinery", "payment report", "contract", "agreement"]
                },
                "project_indicators": {
                    "stranger_things": ["stranger", "things", "netflix", "hawkins"],
                    "papers_that_dream": ["papers", "dream", "screenplay"],
                    "refinery": ["refinery", "payment", "residual"]
                },
                "document_types": {
                    "contracts": {
                        "keywords": ["contract", "agreement", "deal memo", "nda"],
                        "confidence_boost": 0.3,
                        "target_folder": "entertainment"
                    },
                    "financial": {
                        "keywords": ["payment", "report", "residual", "tax", "invoice"],
                        "confidence_boost": 0.3,
                        "target_folder": "financial"
                    },
                    "audio_files": {
                        "extensions": [".mp3", ".wav", ".aiff", ".m4a", ".flac"],
                        "confidence_boost": 0.4,
                        "target_folder": "audio"
                    }
                },
                "confidence_thresholds": {
                    "auto_organize": 0.8,
                    "suggest_organization": 0.6,
                    "manual_review": 0.4
                }
            }
            self._save_classification_rules()
    
    def _map_category_to_folder(self, category: str) -> str:
        """Map category names to folder keys"""
        mapping = {
            "entertainment_industry": "entertainment",
            "financial_documents": "financial", 
            "creative_projects": "creative",
            "development_projects": "development"
        }
        return mapping.get(category, "temp")
    
    def _save_classification_rules(self):
        """Save classification rules to file"""
        self.rules_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.rules_path, 'w') as f:
            json.dump(self.rules, f, indent=2)
    
    def analyze_filename(self, file_path: Path) -> Dict[str, any]:
        """Extract information from filename and path"""
        filename = file_path.name.lower()
        full_path = str(file_path).lower()
        
        analysis = {
            "filename": file_path.name,
            "extension": file_path.suffix.lower(),
            "size": file_path.stat().st_size if file_path.exists() else 0,
            "people_mentioned": [],
            "projects_mentioned": [],
            "keywords_found": [],
            "date_indicators": [],
            "content_type": None
        }
        
        # Extract people
        for person, indicators in self.rules["people_indicators"].items():
            if any(indicator in filename for indicator in indicators):
                analysis["people_mentioned"].append(person)
        
        # Extract projects
        for project, indicators in self.rules["project_indicators"].items():
            if any(indicator in filename for indicator in indicators):
                analysis["projects_mentioned"].append(project)
        
        # Find date patterns
        date_patterns = [
            r'20\d{2}',  # Year
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}-\d{2}-\d{4}'   # MM-DD-YYYY
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, filename)
            analysis["date_indicators"].extend(matches)
        
        # Determine content type from mime type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type:
            analysis["content_type"] = mime_type
        
        return analysis
    
    def calculate_confidence_score(self, analysis: Dict, document_type: str) -> Tuple[float, List[str]]:
        """Calculate confidence score for classification"""
        confidence = 0.0
        reasoning = []
        
        doc_rules = self.rules["document_types"].get(document_type, {})
        
        # Base confidence from document type detection
        if "keywords" in doc_rules:
            keyword_matches = 0
            for keyword in doc_rules["keywords"]:
                if keyword in analysis["filename"].lower():
                    keyword_matches += 1
                    reasoning.append(f"Found keyword: {keyword}")
            
            if keyword_matches > 0:
                confidence += doc_rules.get("confidence_boost", 0.2) * (keyword_matches / len(doc_rules["keywords"]))
        
        # Extension-based confidence
        if "extensions" in doc_rules:
            if analysis["extension"] in doc_rules["extensions"]:
                confidence += doc_rules.get("confidence_boost", 0.3)
                reasoning.append(f"File extension matches: {analysis['extension']}")
        
        # People/project associations boost confidence
        if analysis["people_mentioned"]:
            confidence += 0.2
            reasoning.append(f"People mentioned: {', '.join(analysis['people_mentioned'])}")
        
        if analysis["projects_mentioned"]:
            confidence += 0.2  
            reasoning.append(f"Projects mentioned: {', '.join(analysis['projects_mentioned'])}")
        
        # Date indicators add slight confidence
        if analysis["date_indicators"]:
            confidence += 0.1
            reasoning.append(f"Date indicators found: {', '.join(analysis['date_indicators'])}")
        
        # Content type alignment
        if analysis["content_type"]:
            if document_type == "audio_files" and analysis["content_type"].startswith("audio/"):
                confidence += 0.3
                reasoning.append("Content type matches audio classification")
            elif document_type == "development" and analysis["content_type"].startswith("text/"):
                confidence += 0.1
                reasoning.append("Content type supports development classification")
        
        return min(confidence, 1.0), reasoning
    
    def classify_file(self, file_path: Path) -> ClassificationResult:
        """Classify a file and return detailed results"""
        analysis = self.analyze_filename(file_path)
        
        best_classification = None
        best_confidence = 0.0
        best_reasoning = []
        
        # Test against each document type
        for doc_type, rules in self.rules["document_types"].items():
            confidence, reasoning = self.calculate_confidence_score(analysis, doc_type)
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_classification = doc_type
                best_reasoning = reasoning
        
        # Determine target folder
        if best_classification and best_classification in self.rules["document_types"]:
            target_key = self.rules["document_types"][best_classification].get("target_folder", "temp")
        else:
            target_key = "temp"
        target_folder = self.folder_structure.get(target_key, "99_TEMP_PROCESSING")
        
        # Build suggested path
        suggested_filename = self._generate_filename(analysis, best_classification)
        suggested_path = str(self.base_dir / target_folder / suggested_filename)
        
        # Generate tags
        tags = self._generate_tags(analysis, best_classification)
        
        return ClassificationResult(
            category=best_classification or "unknown",
            subcategory=self._determine_subcategory(analysis, best_classification),
            confidence=best_confidence,
            suggested_path=suggested_path,
            reasoning=best_reasoning,
            tags=tags,
            people=analysis["people_mentioned"],
            projects=analysis["projects_mentioned"]
        )
    
    def _determine_subcategory(self, analysis: Dict, category: str) -> str:
        """Determine subcategory based on analysis"""
        subcategories = {
            "contracts": "Current_Contracts" if any(year in str(datetime.now().year) for year in analysis["date_indicators"]) else "Historical_Contracts",
            "scripts": "Active_Scripts" if analysis["projects_mentioned"] else "Spec_Scripts",
            "financial": "Tax_Documents" if "tax" in analysis["filename"].lower() else "Payment_Reports",
            "audio_files": "Voice_Samples" if any("voice" in kw for kw in analysis["keywords_found"]) else "Raw_Audio",
            "development": "Jupyter_Notebooks" if analysis["extension"] == ".ipynb" else "Code_Files"
        }
        
        return subcategories.get(category, "General")
    
    def _generate_filename(self, analysis: Dict, category: str) -> str:
        """Generate organized filename following naming conventions"""
        parts = []
        
        # Add people first (for alphabetical grouping)
        if analysis["people_mentioned"]:
            # Convert to proper case and join
            people = [person.replace("_", " ").title().replace(" ", "") for person in analysis["people_mentioned"]]
            parts.append("_".join(people))
        
        # Add date if found
        if analysis["date_indicators"]:
            # Use most recent/complete date
            best_date = max(analysis["date_indicators"], key=len)
            if len(best_date) == 4:  # Just year
                parts.append(best_date)
            else:
                parts.append(best_date.replace("-", ""))
        
        # Add category descriptor
        category_names = {
            "contracts": "Contract",
            "scripts": "Script", 
            "financial": "PaymentReport",
            "audio_files": "Audio",
            "development": "Code"
        }
        
        if category in category_names:
            parts.append(category_names[category])
        
        # Add project if mentioned
        if analysis["projects_mentioned"]:
            projects = [proj.replace("_", " ").title().replace(" ", "") for proj in analysis["projects_mentioned"]]
            parts.extend(projects)
        
        # If no meaningful parts, use original name
        if not parts:
            return analysis["filename"]
        
        # Combine parts and add extension
        new_name = "_".join(parts)
        return f"{new_name}{analysis['extension']}"
    
    def _generate_tags(self, analysis: Dict, category: str) -> List[str]:
        """Generate tags for the file"""
        tags = [category] if category else []
        
        # Add people as tags
        tags.extend(analysis["people_mentioned"])
        
        # Add projects as tags  
        tags.extend(analysis["projects_mentioned"])
        
        # Add year if found
        for date_indicator in analysis["date_indicators"]:
            if len(date_indicator) == 4:  # Year
                tags.append(date_indicator)
                break
        
        # Add content type tags
        if analysis["content_type"]:
            if analysis["content_type"].startswith("audio/"):
                tags.append("Audio")
            elif analysis["content_type"].startswith("image/"):
                tags.append("Visual")
            elif analysis["content_type"].startswith("video/"):
                tags.append("Video")
        
        return list(set(tags))  # Remove duplicates
    
    def get_organization_recommendation(self, classification: ClassificationResult) -> str:
        """Get recommendation for how to handle file organization"""
        thresholds = self.rules["confidence_thresholds"]
        
        if classification.confidence >= thresholds["auto_organize"]:
            return "auto_organize"
        elif classification.confidence >= thresholds["suggest_organization"]:
            return "suggest_organization"  
        elif classification.confidence >= thresholds["manual_review"]:
            return "manual_review"
        else:
            return "uncertain"
    
    def batch_classify(self, file_paths: List[Path]) -> List[ClassificationResult]:
        """Classify multiple files in batch"""
        results = []
        
        for file_path in file_paths:
            try:
                result = self.classify_file(file_path)
                results.append(result)
            except Exception as e:
                print(f"Error classifying {file_path}: {e}")
        
        return results

def test_classification_engine():
    """Test the classification engine"""
    print("🧪 Testing File Classification Engine")
    print("-" * 40)
    
    # Initialize engine
    engine = FileClassificationEngine()
    
    # Test with some sample files from Downloads
    downloads_path = Path.home() / "Downloads" 
    sample_files = []
    
    if downloads_path.exists():
        # Get first 5 files for testing
        for file_path in downloads_path.iterdir():
            if file_path.is_file() and len(sample_files) < 5:
                sample_files.append(file_path)
    
    if not sample_files:
        print("⚠️ No sample files found for testing")
        return
    
    print(f"📁 Testing with {len(sample_files)} sample files:")
    
    for i, file_path in enumerate(sample_files, 1):
        print(f"\n[{i}] {file_path.name}")
        
        try:
            result = engine.classify_file(file_path)
            recommendation = engine.get_organization_recommendation(result)
            
            print(f"  📂 Category: {result.category}")
            print(f"  📊 Confidence: {result.confidence:.1%}")
            print(f"  🎯 Recommendation: {recommendation}")
            print(f"  🏷️ Tags: {', '.join(result.tags)}")
            if result.people:
                print(f"  👥 People: {', '.join(result.people)}")
            if result.reasoning:
                print(f"  💭 Reasoning: {result.reasoning[0]}")
                
        except Exception as e:
            import traceback
            print(f"  ❌ Error: {e}")
            print(f"  🐛 Traceback: {traceback.format_exc()}")
    
    print(f"\n✅ Classification engine test completed!")

if __name__ == "__main__":
    test_classification_engine()