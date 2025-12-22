#!/usr/bin/env python3
"""
SemanticTextAnalyzer - Gemini Text Analysis Integration
Part of AI File Organizer v3.1 - Semantic Analysis Upgrade

This module provides intelligent text analysis capabilities using Google's Gemini API,
enabling the system to "read" and understand document context beyond simple keywords.
"""

import os
import time
import json
import logging
import google.generativeai as genai
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

class SemanticTextAnalyzer:
    """
    Text analysis system using Google's Gemini API.
    
    Provides intelligent document understanding with:
    - Context-aware categorization
    - Confidence scoring based on semantic meaning
    - Content summarization
    - Key entity extraction
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 base_dir: Optional[str] = None,
                 model_name: str = "gemini-2.0-flash"):
        """
        Initialize the SemanticTextAnalyzer with Gemini API.
        
        Args:
            api_key: Gemini API key (if None, loads from env/config)
            base_dir: Base directory for file operations
            model_name: Gemini model to use (default: gemini-1.5-flash for speed/cost balance)
        """
        self.base_dir = Path(base_dir) if base_dir else Path(os.getcwd())
        self.model_name = model_name
        self.api_initialized = False
        self._last_request_time = 0
        self._min_request_interval = 4.0  # 15 RPM = 1 request every 4 seconds
        
        # Initialize API
        self._initialize_api(api_key)

    def _initialize_api(self, api_key: Optional[str] = None):
        """Initialize the Gemini API client."""
        try:
            # 1. Try provided key
            if api_key:
                genai.configure(api_key=api_key)
                self.api_initialized = True
                return

            # 2. Try environment variable
            env_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
            if env_key:
                genai.configure(api_key=env_key)
                self.api_initialized = True
                return

            # 3. Try config file (shared with VisionAnalyzer)
            # Priorities:
            # A. ~/.ai_organizer_config/gemini_api_key.txt (Common user path)
            # B. base_dir/config/gemini_config.json (Project path)
            
            # Check A: User Home Config
            user_config_path = Path.home() / ".ai_organizer_config" / "gemini_api_key.txt"
            if user_config_path.exists():
                try:
                    with open(user_config_path, 'r') as f:
                        key = f.read().strip()
                        if key:
                            genai.configure(api_key=key)
                            self.api_initialized = True
                            return
                except Exception:
                    pass

            # Check B: Project Config
            config_path = self.base_dir / "config" / "gemini_config.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    if config.get('api_key'):
                        genai.configure(api_key=config['api_key'])
                        self.api_initialized = True
                        return

            logger.warning("No Gemini API key found. Semantic text analysis will be disabled.")
            self.api_initialized = False

        except Exception as e:
            logger.error(f"Failed to initialize Gemini API: {e}")
            self.api_initialized = False

    def _wait_for_rate_limit(self):
        """Enforce rate limiting (15 RPM)."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def analyze_text(self, text_content: str, filename: str) -> Dict[str, Any]:
        """
        Analyze text content using Gemini API to determine category and context.
        
        Args:
            text_content: The extracted text from the document
            filename: Original filename (for context)
            
        Returns:
            Dictionary with classification result, confidence, and reasoning
        """
        if not self.api_initialized:
            return {
                "success": False,
                "error": "API not initialized"
            }

        # Truncate text if too long (Gemini 1.5 Flash has 1M context, but let's be safe/efficient)
        # 50,000 chars is plenty for classification
        truncated_text = text_content[:50000]
        
        prompt = f"""
        Analyze this document text and strictly output JSON.
        
        Filename: "{filename}"
        
        Task:
        1. Determine the exact document type (e.g., "Legal Contract", "Meeting Minutes", "Invoice", "Screenplay", "Technical Spec", "Financial Report").
        2. Assign a confidence score (0.0 to 1.0).
        3. Extract 3-5 key topics/entities.
        4. Suggest a specific category slug (underscores, no spaces, e.g., "business_contracts").
        5. Suggest a descriptive filename (e.g., "Contract_VendorName_Date.pdf").
        
        Rules:
        - If it's an NDA, confidence must be > 0.9.
        - If it's a Script/Screenplay, category is "creative_screenplay".
        - If it's an Invoice/Receipt, category is "business_financial".
        
        Text Content:
        \"\"\"
        {truncated_text}
        \"\"\"
        
        Output JSON Format:
        {{
            "category": "category_slug",
            "document_type": "Human Readable Type",
            "confidence": 0.85,
            "summary": "1-sentence summary",
            "keywords": ["tag1", "tag2"],
            "reasoning": "Why you chose this category",
            "suggested_filename": "New_Filename.ext"
        }}
        """

        try:
            self._wait_for_rate_limit()
            
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            result = json.loads(response.text)
            
            # Ensure result is a dictionary (Gemini occasionally returns a list)
            if isinstance(result, list) and len(result) > 0:
                result = result[0]
            
            if not isinstance(result, dict):
                result = {"raw_result": result}
                
            result["success"] = True
            return result

        except Exception as e:
            logger.error(f"Error during semantic text analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "category": "unknown",
                "confidence": 0.0
            }
