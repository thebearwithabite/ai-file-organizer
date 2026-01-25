#!/usr/bin/env python3
"""
Computer Vision Content Extractor using Gemini 2.5 Flash
Analyzes images and videos to extract meaningful content for file organization
Optimized for ADHD workflow with batch processing and clear reasoning
"""

import sys
import os
import base64
import json
import sqlite3
from gdrive_integration import get_metadata_root
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import mimetypes

# Add project directory to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

@dataclass
class VisionAnalysisResult:
    """Result of vision analysis"""
    success: bool
    description: str
    content_type: str  # 'screenshot', 'photo', 'document_image', 'creative_asset', etc.
    subjects: List[str]  # People, objects, main subjects
    context: str  # What's happening, setting, purpose
    text_content: str  # Any text found in image/video
    confidence: float
    suggested_tags: List[str]
    suggested_category: str
    reasoning: List[str]
    technical_details: Dict[str, Any]

class GeminiVisionExtractor:
    """
    Computer Vision content extractor using Gemini 2.5 Flash
    Analyzes images and videos for intelligent file organization
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents" / "AI_ORGANIZER_BASE"
        
        # Vision processing directory
        self.vision_dir = get_metadata_root() / "vision_analysis"
        self.vision_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache directory for vision results
        self.cache_dir = self.vision_dir / "vision_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Supported file types
        self.supported_image_types = {
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff', '.svg'
        }
        self.supported_video_types = {
            '.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.3gp'
        }
        
        # Initialize Gemini client
        self.client = None
        self._init_gemini_client()
        
        # ADHD-friendly settings
        self.batch_size = 10  # Process max 10 files at once
        self.enable_caching = True
        self.detailed_logging = True
        
        # Vision analysis prompts
        self.analysis_prompts = {
            'general': """Analyze this image/video for file organization purposes. Provide:

1. CONTENT TYPE: What type of content is this? (screenshot, photo, document scan, creative asset, etc.)
2. MAIN SUBJECTS: What are the key subjects or people in this content?
3. CONTEXT: What's happening? What's the setting or purpose?
4. TEXT CONTENT: Any visible text, captions, or writing?
5. ORGANIZATION CATEGORY: How should this be categorized for file organization?
6. TAGS: Relevant tags for search and organization
7. CONFIDENCE: How confident are you in this analysis? (0-100%)

Be specific and focus on details that would help with intelligent file organization.""",
            
            'entertainment': """Analyze this image/video for entertainment industry file organization. Look for:

1. ENTERTAINMENT CONTENT: Is this related to TV/film production, acting, or entertainment business?
2. PEOPLE: Any recognizable actors, crew, or industry professionals?
3. PRODUCTION DETAILS: Show/movie titles, production companies, set details?
4. DOCUMENT TYPE: Contract, headshot, behind-scenes, promotional material?
5. BUSINESS CONTEXT: Meetings, signings, presentations, negotiations?
6. CREATIVE ASSETS: Scripts, storyboards, concept art, demo reels?

Focus on details relevant to entertainment industry workflow and Client Name Wolfhard's career management.""",
            
            'creative': """Analyze this image/video for creative project organization. Identify:

1. CREATIVE TYPE: Artwork, design, music production, video content, writing?
2. PROJECT STAGE: Concept, draft, revision, final, published?
3. CREATIVE ELEMENTS: Colors, styles, themes, artistic techniques?
4. PODCAST/AUDIO: If audio-related, identify podcast content, voice recordings, music?
5. AI/CONSCIOUSNESS THEMES: Any AI, consciousness, or technology themes?
6. COLLABORATION: Multiple creators, team projects, feedback sessions?

Perfect for organizing Papers That Dream podcast content and other creative work."""
        }
    
    def _init_gemini_client(self):
        """Initialize Gemini API client"""
        try:
            import google.generativeai as genai
            
            # Get API key from environment
            api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
            if not api_key:
                print("⚠️ Warning: No Google API key found in environment variables")
                print("   Set GOOGLE_API_KEY or GEMINI_API_KEY to enable vision analysis")
                return
            
            genai.configure(api_key=api_key)
            
            # Use Gemini 2.5 Flash for optimal speed and cost
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            self.client = genai
            
            print("✅ Gemini 2.5 Flash vision analysis initialized")
            
        except ImportError:
            print("⚠️ Google GenerativeAI library not installed")
            print("   Run: pip install google-generativeai")
        except Exception as e:
            print(f"⚠️ Error initializing Gemini client: {e}")
    
    def can_process_file(self, file_path: Path) -> bool:
        """Check if file can be processed by vision analysis"""
        if not self.client:
            return False
        
        extension = file_path.suffix.lower()
        return extension in self.supported_image_types or extension in self.supported_video_types
    
    def analyze_visual_content(self, file_path: Path, context: str = 'general') -> VisionAnalysisResult:
        """Analyze a single image or video file"""
        
        if not self.can_process_file(file_path):
            return VisionAnalysisResult(
                success=False,
                description="Unsupported file type for vision analysis",
                content_type="unsupported",
                subjects=[],
                context="",
                text_content="",
                confidence=0.0,
                suggested_tags=[],
                suggested_category="unknown",
                reasoning=["File type not supported by vision analysis"],
                technical_details={}
            )
        
        if not file_path.exists():
            return VisionAnalysisResult(
                success=False,
                description="File not found",
                content_type="missing",
                subjects=[],
                context="",
                text_content="",
                confidence=0.0,
                suggested_tags=[],
                suggested_category="unknown",
                reasoning=["File does not exist"],
                technical_details={}
            )
        
        # Check cache first
        if self.enable_caching:
            cached_result = self._get_cached_analysis(file_path)
            if cached_result:
                if self.detailed_logging:
                    print(f"📋 Using cached vision analysis for {file_path.name}")
                return cached_result
        
        try:
            if self.detailed_logging:
                print(f"👁️ Analyzing visual content: {file_path.name}")
            
            # Analyze the file
            analysis_result = self._perform_vision_analysis(file_path, context)
            
            # Cache the result
            if self.enable_caching and analysis_result.success:
                self._cache_analysis_result(file_path, analysis_result)
            
            return analysis_result
            
        except Exception as e:
            return VisionAnalysisResult(
                success=False,
                description=f"Vision analysis failed: {str(e)}",
                content_type="error",
                subjects=[],
                context="",
                text_content="",
                confidence=0.0,
                suggested_tags=[],
                suggested_category="unknown",
                reasoning=[f"Analysis error: {str(e)}"],
                technical_details={"error": str(e)}
            )
    
    def _perform_vision_analysis(self, file_path: Path, context: str) -> VisionAnalysisResult:
        """Perform the actual vision analysis using Gemini"""
        
        if not self.client:
            raise Exception("Gemini client not initialized")
        
        # Get appropriate prompt
        prompt = self.analysis_prompts.get(context, self.analysis_prompts['general'])
        
        # Prepare file for analysis
        if file_path.suffix.lower() in self.supported_image_types:
            result = self._analyze_image(file_path, prompt)
        else:
            result = self._analyze_video(file_path, prompt)
        
        return result
    
    def _analyze_image(self, file_path: Path, prompt: str) -> VisionAnalysisResult:
        """Analyze an image file"""
        
        try:
            # Read and encode image
            with open(file_path, 'rb') as f:
                image_data = f.read()
            
            # Create image part for Gemini
            image_part = {
                "mime_type": mimetypes.guess_type(str(file_path))[0] or "image/jpeg",
                "data": image_data
            }
            
            # Call Gemini API
            response = self.model.generate_content([
                prompt,
                image_part
            ])
            
            # Parse response
            analysis_text = response.text
            return self._parse_analysis_response(analysis_text, file_path, 'image')
            
        except Exception as e:
            raise Exception(f"Image analysis failed: {e}")
    
    def _analyze_video(self, file_path: Path, prompt: str) -> VisionAnalysisResult:
        """Analyze a video file with intelligent sampling for long videos"""
        
        try:
            # Check video duration and create sample if needed
            video_to_analyze = self._prepare_video_for_analysis(file_path)
            
            # Upload video file (either original or sample)
            video_file = self.client.upload_file(str(video_to_analyze))
            
            # Wait for processing
            while video_file.state.name == "PROCESSING":
                print("📹 Processing video..." + (" (sample)" if video_to_analyze != file_path else ""))
                time.sleep(2)
                video_file = self.client.get_file(video_file.name)
            
            if video_file.state.name == "FAILED":
                raise Exception("Video processing failed")
            
            # Enhanced prompt for video analysis
            video_prompt = f"""
{prompt}

ADDITIONAL VIDEO ANALYSIS CONTEXT:
- This is a video file: {file_path.name}
- If this appears to be a sample/excerpt, note that in your analysis
- Look for: project identifiers, creative themes, people, settings, timestamps
- Pay attention to: visual style, production quality, content themes
- Consider: Is this raw footage, edited content, demo material, or creative work?

Focus on details that would help with project categorization and file organization.
"""
            
            # Analyze video
            response = self.model.generate_content([
                video_prompt,
                video_file
            ])
            
            analysis_text = response.text
            result = self._parse_analysis_response(analysis_text, file_path, 'video')
            
            # Clean up temporary sample file if created
            if video_to_analyze != file_path and video_to_analyze.exists():
                video_to_analyze.unlink()
            
            return result
            
        except Exception as e:
            raise Exception(f"Video analysis failed: {e}")
    
    def _prepare_video_for_analysis(self, file_path: Path) -> Path:
        """Prepare video for analysis - create sample if too long"""
        
        try:
            # Get video duration
            import subprocess
            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', 
                   '-of', 'csv=p=0', str(file_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                # Can't get duration, use original
                return file_path
            
            duration = float(result.stdout.strip())
            max_duration = 120  # 2 minutes
            
            if duration <= max_duration:
                # Video is short enough, use original
                return file_path
            
            print(f"📹 Video is {duration:.1f}s, creating {max_duration}s sample...")
            
            # Create intelligent sample - take from multiple points
            sample_path = self.cache_dir / f"sample_{file_path.stem}.mp4"
            
            # Create a 2-minute sample with clips from beginning, middle, and end
            sample_duration = max_duration / 3  # 40 seconds each
            
            # Beginning: 0 to 40s
            # Middle: middle-20s to middle+20s  
            # End: last 40s
            
            middle_start = max(duration/2 - sample_duration/2, sample_duration)
            end_start = max(duration - sample_duration, duration * 0.8)
            
            # Build ffmpeg command to concatenate clips
            filter_complex = (
                f"[0:v]trim=start=0:duration={sample_duration}[v1];"
                f"[0:v]trim=start={middle_start}:duration={sample_duration}[v2];"
                f"[0:v]trim=start={end_start}:duration={sample_duration}[v3];"
                f"[0:a]atrim=start=0:duration={sample_duration}[a1];"
                f"[0:a]atrim=start={middle_start}:duration={sample_duration}[a2];"
                f"[0:a]atrim=start={end_start}:duration={sample_duration}[a3];"
                f"[v1][a1][v2][a2][v3][a3]concat=n=3:v=1:a=1[outv][outa]"
            )
            
            cmd = [
                'ffmpeg', '-i', str(file_path), 
                '-filter_complex', filter_complex,
                '-map', '[outv]', '-map', '[outa]',
                '-y',  # Overwrite output
                str(sample_path)
            ]
            
            # Run ffmpeg
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and sample_path.exists():
                print(f"✅ Created intelligent video sample: {sample_path.name}")
                return sample_path
            else:
                print(f"⚠️ Failed to create sample, using original video")
                return file_path
                
        except Exception as e:
            print(f"⚠️ Error preparing video sample: {e}")
            return file_path
    
    def _parse_analysis_response(self, analysis_text: str, file_path: Path, media_type: str) -> VisionAnalysisResult:
        """Parse Gemini's analysis response into structured result"""
        
        # Extract structured information from response
        # This is a simplified parser - in production, you'd want more robust parsing
        
        lines = analysis_text.split('\n')
        
        # Default values
        content_type = media_type
        subjects = []
        context = ""
        text_content = ""
        confidence = 0.8  # Default confidence
        suggested_tags = []
        suggested_category = "visual_media"
        reasoning = []
        
        # Parse response (looking for structured sections)
        for line in lines:
            line = line.strip()
            
            if line.upper().startswith('CONTENT TYPE:'):
                content_type = line.split(':', 1)[1].strip()
            elif line.upper().startswith('MAIN SUBJECTS:'):
                subjects = [s.strip() for s in line.split(':', 1)[1].split(',')]
            elif line.upper().startswith('CONTEXT:'):
                context = line.split(':', 1)[1].strip()
            elif line.upper().startswith('TEXT CONTENT:'):
                text_content = line.split(':', 1)[1].strip()
            elif line.upper().startswith('ORGANIZATION CATEGORY:'):
                suggested_category = line.split(':', 1)[1].strip().lower().replace(' ', '_')
            elif line.upper().startswith('TAGS:'):
                tags_text = line.split(':', 1)[1].strip()
                suggested_tags = [t.strip() for t in tags_text.split(',')]
            elif line.upper().startswith('CONFIDENCE:'):
                try:
                    confidence_text = line.split(':', 1)[1].strip().rstrip('%')
                    confidence = float(confidence_text) / 100.0
                except:
                    confidence = 0.8
        
        # Generate reasoning
        reasoning = [
            f"Vision analysis identified content as: {content_type}",
            f"Main subjects detected: {', '.join(subjects[:3])}" if subjects else "No specific subjects identified",
            f"Confidence level: {confidence:.1%}"
        ]
        
        # Add filename-based context
        filename_lower = file_path.name.lower()
        if 'screenshot' in filename_lower:
            suggested_tags.append('screenshot')
            content_type = 'screenshot'
        if 'finn' in filename_lower or 'wolfhard' in filename_lower:
            suggested_tags.append('finn_wolfhard')
        
        return VisionAnalysisResult(
            success=True,
            description=analysis_text,
            content_type=content_type,
            subjects=subjects,
            context=context,
            text_content=text_content,
            confidence=confidence,
            suggested_tags=list(set(suggested_tags)),  # Remove duplicates
            suggested_category=suggested_category,
            reasoning=reasoning,
            technical_details={
                'file_type': media_type,
                'file_size': file_path.stat().st_size if file_path.exists() else 0,
                'analysis_timestamp': datetime.now().isoformat()
            }
        )
    
    def batch_analyze_files(self, file_paths: List[Path], context: str = 'general') -> List[VisionAnalysisResult]:
        """Analyze multiple files in ADHD-friendly batches"""
        
        if not file_paths:
            return []
        
        # Filter to supported files
        supported_files = [f for f in file_paths if self.can_process_file(f)]
        
        if not supported_files:
            print("📝 No files support vision analysis")
            return []
        
        print(f"👁️ Starting vision analysis of {len(supported_files)} files...")
        print(f"🧠 ADHD-friendly batch processing: max {self.batch_size} at a time")
        
        results = []
        
        # Process in batches
        for i in range(0, len(supported_files), self.batch_size):
            batch = supported_files[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(supported_files) + self.batch_size - 1) // self.batch_size
            
            print(f"\n🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} files)")
            
            batch_results = []
            for j, file_path in enumerate(batch, 1):
                print(f"   [{j}/{len(batch)}] Analyzing {file_path.name}...")
                
                result = self.analyze_visual_content(file_path, context)
                batch_results.append(result)
                
                if result.success:
                    print(f"       ✅ {result.content_type}: {result.confidence:.1%} confidence")
                    if result.subjects:
                        print(f"       👥 Subjects: {', '.join(result.subjects[:2])}")
                    if result.suggested_tags:
                        print(f"       🏷️  Tags: {', '.join(result.suggested_tags[:3])}")
                else:
                    print(f"       ❌ Failed: {result.description}")
                
                # Small delay to be respectful to API
                time.sleep(0.5)
            
            results.extend(batch_results)
            
            # ADHD-friendly pause between batches
            if batch_num < total_batches:
                print(f"   ⏸️  Pausing 2 seconds between batches...")
                time.sleep(2)
        
        # Summary
        successful = sum(1 for r in results if r.success)
        print(f"\n📊 Vision analysis complete: {successful}/{len(results)} files analyzed successfully")
        
        return results
    
    def _get_cached_analysis(self, file_path: Path) -> Optional[VisionAnalysisResult]:
        """Get cached analysis result if available and up-to-date"""
        
        cache_file = self.cache_dir / f"{file_path.name}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
            
            # Check if file has been modified since cache
            file_mtime = file_path.stat().st_mtime
            cache_mtime = cached_data.get('file_mtime', 0)
            
            if file_mtime > cache_mtime:
                return None  # File modified, cache invalid
            
            # Reconstruct VisionAnalysisResult
            return VisionAnalysisResult(
                success=cached_data['success'],
                description=cached_data['description'],
                content_type=cached_data['content_type'],
                subjects=cached_data['subjects'],
                context=cached_data['context'],
                text_content=cached_data['text_content'],
                confidence=cached_data['confidence'],
                suggested_tags=cached_data['suggested_tags'],
                suggested_category=cached_data['suggested_category'],
                reasoning=cached_data['reasoning'],
                technical_details=cached_data['technical_details']
            )
            
        except Exception:
            return None
    
    def _cache_analysis_result(self, file_path: Path, result: VisionAnalysisResult):
        """Cache analysis result for future use"""
        
        cache_file = self.cache_dir / f"{file_path.name}.json"
        
        try:
            cache_data = {
                'success': result.success,
                'description': result.description,
                'content_type': result.content_type,
                'subjects': result.subjects,
                'context': result.context,
                'text_content': result.text_content,
                'confidence': result.confidence,
                'suggested_tags': result.suggested_tags,
                'suggested_category': result.suggested_category,
                'reasoning': result.reasoning,
                'technical_details': result.technical_details,
                'file_mtime': file_path.stat().st_mtime,
                'cached_at': datetime.now().isoformat()
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
        except Exception as e:
            if self.detailed_logging:
                print(f"⚠️ Could not cache analysis for {file_path.name}: {e}")


def test_vision_analysis():
    """Test the vision analysis system"""
    
    print("👁️ Testing Gemini 2.5 Flash Vision Analysis")
    print("=" * 50)
    
    extractor = GeminiVisionExtractor()
    
    if not extractor.client:
        print("❌ Vision analysis not available (missing API key or library)")
        return
    
    # Find test files
    test_dirs = [
        Path.home() / "Downloads",
        Path.home() / "Desktop",
    ]
    
    test_files = []
    for test_dir in test_dirs:
        if test_dir.exists():
            # Look for images and videos
            for ext in extractor.supported_image_types.union(extractor.supported_video_types):
                files = list(test_dir.glob(f"*{ext}"))
                test_files.extend(files[:2])  # Max 2 files per extension
                
                if len(test_files) >= 5:  # Limit total test files
                    break
            if len(test_files) >= 5:
                break
    
    if not test_files:
        print("📝 No vision-compatible files found for testing")
        return
    
    print(f"📁 Testing with {len(test_files)} files:")
    for f in test_files:
        print(f"   📄 {f.name}")
    
    # Analyze files
    results = extractor.batch_analyze_files(test_files, context='general')
    
    # Show results
    print(f"\n📊 Vision Analysis Results:")
    for i, (file_path, result) in enumerate(zip(test_files, results), 1):
        print(f"\n[{i}] {file_path.name}")
        print(f"    ✅ Success: {result.success}")
        if result.success:
            print(f"    📋 Type: {result.content_type}")
            print(f"    🎯 Confidence: {result.confidence:.1%}")
            print(f"    🏷️  Tags: {', '.join(result.suggested_tags[:5])}")
            print(f"    📂 Category: {result.suggested_category}")
            if result.subjects:
                print(f"    👥 Subjects: {', '.join(result.subjects[:3])}")
        else:
            print(f"    ❌ Error: {result.description}")


if __name__ == '__main__':
    test_vision_analysis()