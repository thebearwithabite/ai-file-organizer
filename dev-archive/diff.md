# Code Review
- Review the diff, report on issues, bugs, and improvements. 
- End with a concise markdown table of any issues found, their solutions, and a risk assessment for each issue if applicable.
- Use emojis to convey the severity of each issue.

## Diffdiff --git a/AI Organizer Admin.app/Contents/Info.plist b/AI Organizer Admin.app/Contents/Info.plist
deleted file mode 100644
index 2344898..0000000
--- a/AI Organizer Admin.app/Contents/Info.plist	
+++ /dev/null
@@ -1,44 +0,0 @@
-<?xml version="1.0" encoding="UTF-8"?>
-<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
-<plist version="1.0">
-<dict>
-    <key>CFBundleExecutable</key>
-    <string>AI_Organizer_Admin</string>
-    <key>CFBundleIdentifier</key>
-    <string>com.ryanthomson.ai-organizer-admin</string>
-    <key>CFBundleName</key>
-    <string>AI Organizer Admin</string>
-    <key>CFBundleVersion</key>
-    <string>1.0</string>
-    <key>CFBundleShortVersionString</key>
-    <string>1.0</string>
-    <key>CFBundlePackageType</key>
-    <string>APPL</string>
-    <key>CFBundleSignature</key>
-    <string>????</string>
-    <key>LSMinimumSystemVersion</key>
-    <string>10.14</string>
-    <key>CFBundleDocumentTypes</key>
-    <array>
-        <dict>
-            <key>CFBundleTypeExtensions</key>
-            <array>
-                <string>pdf</string>
-                <string>docx</string>
-                <string>txt</string>
-                <string>mp3</string>
-                <string>wav</string>
-                <string>m4a</string>
-            </array>
-            <key>CFBundleTypeName</key>
-            <string>Organizable Files</string>
-            <key>CFBundleTypeRole</key>
-            <string>Viewer</string>
-        </dict>
-    </array>
-    <key>NSAppleScriptEnabled</key>
-    <true/>
-    <key>CFBundleIconFile</key>
-    <string>AppIcon</string>
-</dict>
-</plist>
\ No newline at end of file
diff --git a/AI Organizer Quick.app/Contents/Info.plist b/AI Organizer Quick.app/Contents/Info.plist
deleted file mode 100644
index 73dabe5..0000000
--- a/AI Organizer Quick.app/Contents/Info.plist	
+++ /dev/null
@@ -1,28 +0,0 @@
-<?xml version="1.0" encoding="UTF-8"?>
-<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
-<plist version="1.0">
-<dict>
-    <key>CFBundleExecutable</key>
-    <string>AI_Organizer_Quick</string>
-    <key>CFBundleIdentifier</key>
-    <string>com.ryanthomson.ai-organizer-quick</string>
-    <key>CFBundleName</key>
-    <string>AI Organizer Quick</string>
-    <key>CFBundleVersion</key>
-    <string>1.0</string>
-    <key>CFBundleShortVersionString</key>
-    <string>1.0</string>
-    <key>CFBundlePackageType</key>
-    <string>APPL</string>
-    <key>CFBundleSignature</key>
-    <string>????</string>
-    <key>LSMinimumSystemVersion</key>
-    <string>10.14</string>
-    <key>LSUIElement</key>
-    <true/>
-    <key>NSAppleScriptEnabled</key>
-    <true/>
-    <key>CFBundleIconFile</key>
-    <string>AppIcon</string>
-</dict>
-</plist>
\ No newline at end of file
diff --git a/AI_Organizer_MenuBar.applescript b/AI_Organizer_MenuBar.applescript
index cbff09a..3ea1366 100644
--- a/AI_Organizer_MenuBar.applescript
+++ b/AI_Organizer_MenuBar.applescript
@@ -40,7 +40,7 @@ end run
 
 on quickSearch()
 	try
-		set searchQuery to text returned of (display dialog "Search your files:" default answer "" with title "AI Librarian" with icon note)
+		set searchQuery to text returned of (display dialog "Search your files:" default answer "" with title "AI Librarian")
 		if searchQuery is not "" then
 			
 			-- Show progress
@@ -50,8 +50,7 @@ on quickSearch()
 			set searchResults to do shell script searchCommand
 			
 			-- Show results in a clean format
-			display dialog searchResults with title "Search Results" buttons {"New Search", "Open Admin", "Close"} default button "Close" with icon note
-			
+			display dialog searchResults with title "Search Results" buttons {"New Search", "Open Admin", "Close"} default button "Close" 			
 			set buttonResult to button returned of result
 			if buttonResult is "New Search" then
 				quickSearch()
@@ -66,7 +65,7 @@ end quickSearch
 
 on quickOrganizeDownloads()
 	try
-		set modeChoice to choose from list {"👀 Preview Only", "✅ Organize Now"} with title "Organize Downloads" with prompt "Choose mode:" default items {"👀 Preview Only"} with icon note
+		set modeChoice to choose from list {"👀 Preview Only", "✅ Organize Now"} with title "Organize Downloads" with prompt "Choose mode:" default items {"👀 Preview Only"}
 		
 		if modeChoice is not false then
 			set selectedMode to item 1 of modeChoice
@@ -84,7 +83,7 @@ on quickOrganizeDownloads()
 			set organizeResults to do shell script organizeCommand
 			
 			if selectedMode is "👀 Preview Only" then
-				display dialog "Organization Preview:" & return & return & organizeResults with title "Preview Results" buttons {"Organize Now", "Close"} default button "Close" with icon note
+				display dialog "Organization Preview:" & return & return & organizeResults with title "Preview Results" buttons {"Organize Now", "Close"} default button "Close"
 				if button returned of result is "Organize Now" then
 					-- Run in live mode
 					display notification "Organizing Downloads folder..." with title "AI File Organizer" subtitle "Moving files..."
@@ -94,7 +93,7 @@ on quickOrganizeDownloads()
 				end if
 			else
 				display notification "Downloads organized!" with title "AI File Organizer" sound name "Glass"
-				display dialog "Organization Complete!" & return & return & organizeResults with title "Organization Results" buttons {"OK"} default button "OK" with icon note
+				display dialog "Organization Complete!" & return & return & organizeResults with title "Organization Results" buttons {"OK"} default button "OK"
 			end if
 		end if
 	on error errorMsg
@@ -104,7 +103,7 @@ end quickOrganizeDownloads
 
 on quickAnalyzeAudio()
 	try
-		set audioFile to choose file with prompt "Choose audio file to analyze:" of type {"public.audio"} with icon note
+		set audioFile to choose file with prompt "Choose audio file to analyze:" of type {"public.audio"}
 		set filePath to POSIX path of audioFile
 		set fileName to name of (info for audioFile)
 		
@@ -115,8 +114,7 @@ on quickAnalyzeAudio()
 		
 		display notification "Analysis complete!" with title "Audio AI" sound name "Glass"
 		
-		display dialog "Audio Analysis Results:" & return & return & analysisResults with title "Audio AI Analysis" buttons {"Analyze Another", "Close"} default button "Close" with icon note
-		
+		display dialog "Audio Analysis Results:" & return & return & analysisResults with title "Audio AI Analysis" buttons {"Analyze Another", "Close"} default button "Close"
 		if button returned of result is "Analyze Another" then
 			quickAnalyzeAudio()
 		end if
@@ -178,8 +176,7 @@ except:
 		
 		set statusResults to do shell script statusCommand
 		
-		display dialog statusResults with title "System Status" buttons {"Full Admin", "Refresh", "OK"} default button "OK" with icon note
-		
+		display dialog statusResults with title "System Status" buttons {"Full Admin", "Refresh", "OK"} default button "OK"
 		set buttonResult to button returned of result
 		if buttonResult is "Full Admin" then
 			do shell script "osascript " & quoted form of (organizerPath & "/AI_Organizer_Admin.applescript")
@@ -226,8 +223,7 @@ on showQuickHelp()
 • Search supports partial matches
 • System learns from your choices"
 	
-	display dialog helpText with title "AI File Organizer Help" buttons {"Open Full Admin", "Close"} default button "Close" with icon note
-	
+	display dialog helpText with title "AI File Organizer Help" buttons {"Open Full Admin", "Close"} default button "Close"
 	if button returned of result is "Open Full Admin" then
 		do shell script "osascript " & quoted form of (organizerPath & "/AI_Organizer_Admin.applescript")
 	end if
diff --git a/CLAUDE.md b/CLAUDE.md
index 5276b4b..4302be5 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -115,7 +115,7 @@ python interactive_organizer.py file "/path/to/document.pdf" --live
 
 ### Index New Content:
 ```bash
-python enhanced_librarian.py index --folder "/Users/user/Documents/NewProject"
+python enhanced_librarian.py index --folder "/Users/user/Documents/NewProject"
 python vector_librarian.py  # Index emails + documents with smart chunking
 ```
 
@@ -191,13 +191,99 @@ When working on this system:
 
 1. **User has ADHD** - organization systems must be low-friction and intuitive
 2. **Entertainment industry focus** - understand contracts, talent management, creative projects
-3. **Real files matter** - test with actual documents from `/Users/user/Documents/`
+3. **Real files matter** - test with actual documents from `/Users/user/Documents/`
 4. **macOS integration essential** - must work seamlessly within existing workflow
 5. **Privacy conscious** - all processing happens locally, no cloud uploads
 
 This isn't just a file organizer - it's an accessibility tool that makes information management possible for someone with ADHD working in a complex, document-heavy industry.
 
+## 🤖 **Claude Code Agent Integration**
+
+The following specialized agents are configured to work proactively and automatically with the AI File Organizer:
+
+### test-runner
+**Purpose**: Execute comprehensive test suites, validate functionality, ensure quality
+**Proactive Triggers**:
+- After any changes to core classification engine (`classification_engine.py`)
+- Before any git commits involving Python files
+- After modifying search functionality (`enhanced_librarian.py`, `vector_librarian.py`)
+- When interactive organizer logic changes (`interactive_organizer.py`)
+- After AppleScript GUI modifications
+
+### context-doc-manager
+**Purpose**: Keep documentation synchronized with codebase changes, maintain project coherence
+**Proactive Triggers**:
+- After adding new CLI tools or commands
+- When new file types or analysis features are added
+- After modifying Google Drive integration (`gdrive_cli.py`)
+- When ADHD-friendly features are updated
+- After creative AI or audio analysis enhancements
+
+### applescript-ui-expert
+**Purpose**: Enhance macOS AppleScript interfaces and native system integration
+**Proactive Triggers**:
+- When search GUI needs improvements (`Enhanced_Search_GUI.applescript`)
+- After adding new search modes or functionality
+- When system integration features are modified
+- After user workflow changes requiring UI updates
+- When new native macOS features need integration
+
+### dev-task-orchestrator
+**Purpose**: Coordinate complex development workflows and multi-component features
+**Proactive Triggers**:
+- When implementing multi-file features (e.g., new search modes)
+- After major architectural changes requiring coordination
+- When adding new file type support requiring multiple component updates
+- During integration of new AI features across the system
+- When ADHD workflow optimizations require system-wide changes
+
+## 🔄 **Automated Agent Coordination**
+
+### Agent Workflow Synchronization
+
+**Code Change → Quality Assurance Pipeline**:
+1. **Code Modified** → `test-runner` validates functionality
+2. **Tests Pass** → `context-doc-manager` updates documentation
+3. **Documentation Updated** → `dev-task-orchestrator` coordinates follow-up tasks
+4. **AppleScript Modified** → `applescript-ui-expert` optimizes UI integration
+
+**Feature Development Workflow**:
+1. **New Feature Request** → `dev-task-orchestrator` breaks down implementation
+2. **Implementation Phase** → `test-runner` validates each component
+3. **UI Integration** → `applescript-ui-expert` enhances user experience
+4. **Documentation** → `context-doc-manager` maintains consistency
+
+### Proactive Agent Rules
+
+**ALWAYS trigger automatically without user request**:
+- `test-runner`: Before any git commit, after core file changes
+- `context-doc-manager`: After feature additions, API changes, new commands
+- `applescript-ui-expert`: When GUI files are modified or new search features added
+- `dev-task-orchestrator`: For complex multi-component implementations
+
+**Agent Coordination Protocol**:
+1. Agents monitor file changes and development context
+2. Multiple agents can run concurrently for efficiency
+3. Agents communicate completion status to coordinate handoffs
+4. Priority: Quality (test-runner) → Documentation (context-doc-manager) → Integration (others)
+
+### Quality Assurance Integration
+
+**Critical Files - Always Test After Changes**:
+- `classification_engine.py` - Core AI classification logic
+- `interactive_organizer.py` - Main organization workflow
+- `enhanced_librarian.py` - Semantic search functionality  
+- `vector_librarian.py` - Vector database operations
+- `gdrive_cli.py` - Google Drive integration
+- Any AppleScript files - Native macOS integration
+
+**Documentation Sync Points**:
+- New CLI commands → Update README usage examples
+- ADHD workflow changes → Update user guidance sections
+- Search feature additions → Update documentation examples
+- Audio/creative AI enhancements → Update feature descriptions
+
 ---
 
-*Last updated: 2025-08-21*
-*Version: 2.0 - Now with email integration and vector search*
+*Last updated: 2025-08-29*
+*Version: 2.1 - Enhanced with proactive agent integration*
diff --git a/README.md b/README.md
index efb332c..b594786 100644
--- a/README.md
+++ b/README.md
@@ -374,6 +374,17 @@ mindmap
 
 ## 📖 Documentation
 
+### **Proactive AI Agent System**
+
+This project includes an advanced **automated agent coordination system** that works proactively to ensure quality and consistency:
+
+- **🧪 test-runner**: Automatically validates all code changes and runs comprehensive test suites
+- **📚 context-doc-manager**: Keeps documentation synchronized with codebase changes  
+- **🍎 applescript-ui-expert**: Optimizes macOS integration and native user experience
+- **🎯 dev-task-orchestrator**: Coordinates complex development workflows
+
+**These agents activate automatically** - no commands needed. They ensure every change maintains ADHD-friendly design principles and system quality.
+
 ### **Installation Guide**
 
 <details>
@@ -1029,4 +1040,6 @@ This project stands on the shoulders of giants:
 
 **Quick Links:** [Installation](#-quick-start) • [ADHD Guide](#-adhd-optimized-design) • [Audio Features](#-audioai-integration) • [Google Drive](#-google-drive-integration) • [Creative Tools](#-creative-ai-ecosystem)
 
+**Developer Documentation:** [CLAUDE.md](/Users/user/Github/ai-file-organizer/CLAUDE.md) • [Agent System](/Users/user/Github/ai-file-organizer/agents.md) • [Architecture](/Users/user/Github/ai-file-organizer/llm_librarian_architecture.md) • [Specifications](/Users/user/Github/ai-file-organizer/system_specifications_v2.md)
+
 </div>
\ No newline at end of file
diff --git a/gdrive_librarian.py b/gdrive_librarian.py
index c06c39b..588471e 100644
--- a/gdrive_librarian.py
+++ b/gdrive_librarian.py
@@ -117,8 +117,8 @@ class GoogleDriveLibrarian:
             return {}
     
     def upload_file(self, local_path: str, gdrive_folder: str = None, 
-                   new_name: str = None) -> Optional[str]:
-        """Upload file to Google Drive with AI classification"""
+                   new_name: str = None, auto_delete: bool = False) -> Optional[str]:
+        """Upload file to Google Drive with AI classification and optional auto-deletion"""
         if not self.authenticated:
             print("❌ Not authenticated with Google Drive")
             return None
@@ -128,6 +128,9 @@ class GoogleDriveLibrarian:
             print(f"❌ File not found: {local_path}")
             return None
         
+        # Store file size for logging before upload
+        file_size_mb = local_file.stat().st_size / (1024 * 1024)
+        
         try:
             # Quick classification for emergency upload
             print(f"🤔 Classifying: {local_file.name}")
@@ -170,9 +173,25 @@ class GoogleDriveLibrarian:
             
             print(f"✅ Uploaded: {file_name} → {gdrive_folder}")
             print(f"   File ID: {file_result.get('id')}")
-            print(f"   Size: {int(file_result.get('size', 0)) / (1024*1024):.1f} MB")
+            print(f"   Size: {file_size_mb:.1f} MB")
             print(f"   Classification: {category} ({confidence:.1f}%)")
             
+            # Log metadata for this upload operation (before deletion)
+            try:
+                self._log_metadata_operation(local_file, gdrive_folder, category, confidence, file_size_mb)
+            except Exception as e:
+                print(f"⚠️  Metadata logging failed: {e}")
+            
+            # Auto-delete local file after successful upload
+            if auto_delete:
+                try:
+                    local_file.unlink()
+                    print(f"🗑️  Deleted local file: {local_file.name}")
+                    print(f"💾 Freed {file_size_mb:.1f} MB of local space")
+                except Exception as e:
+                    print(f"❌ Could not delete local file: {e}")
+                    print(f"⚠️  Manual deletion required: {local_path}")
+            
             return file_result.get('id')
             
         except HttpError as error:
@@ -238,24 +257,18 @@ class GoogleDriveLibrarian:
                     print(f"   🎯 Classification: {category} ({confidence:.1f}%)")
                     print(f"   💾 Would free: {size_mb:.1f} MB")
                     
+                    results["uploaded"] += 1  # Count as would-be uploaded
                     results["space_freed"] += size_mb
                     
                 except Exception as e:
                     print(f"   ❌ Classification error: {e}")
                     results["errors"] += 1
             else:
-                # Actually upload
-                file_id = self.upload_file(str(file_path))
+                # Actually upload with auto-deletion enabled
+                file_id = self.upload_file(str(file_path), auto_delete=True)
                 if file_id:
                     results["uploaded"] += 1
                     results["space_freed"] += size_mb
-                    
-                    # Delete local file after successful upload
-                    try:
-                        file_path.unlink()
-                        print(f"   🗑️  Deleted local copy")
-                    except Exception as e:
-                        print(f"   ⚠️  Could not delete local file: {e}")
                 else:
                     results["errors"] += 1
         
@@ -322,6 +335,40 @@ class GoogleDriveLibrarian:
         
         return mapping.get(category, "Reference Material")
     
+    def _log_metadata_operation(self, local_file: Path, gdrive_folder: str, category: str, confidence: float, size_mb: float):
+        """Log upload operation to metadata system for tracking"""
+        try:
+            # Import metadata generator
+            from metadata_generator import MetadataGenerator
+            
+            # Create metadata entry for the upload operation
+            metadata_gen = MetadataGenerator(str(self.base_dir))
+            
+            # Analyze the file before upload (if it still exists)
+            if local_file.exists():
+                metadata = metadata_gen.analyze_file_comprehensive(local_file)
+                
+                # Add Google Drive specific metadata
+                metadata.update({
+                    'gdrive_upload': True,
+                    'gdrive_folder': gdrive_folder,
+                    'gdrive_category': category,
+                    'gdrive_confidence': confidence,
+                    'upload_timestamp': datetime.now().isoformat(),
+                    'organization_status': 'Uploaded_to_GDrive',
+                    'space_freed_mb': size_mb
+                })
+                
+                # Save to metadata database
+                success = metadata_gen.save_file_metadata(metadata)
+                if success:
+                    print(f"   📊 Logged metadata for tracking")
+                else:
+                    print(f"   ⚠️  Metadata logging to database failed")
+            
+        except Exception as e:
+            print(f"   ⚠️  Metadata logging error: {e}")
+    
     def get_storage_info(self) -> Dict:
         """Get Google Drive storage information"""
         if not self.authenticated:
diff --git a/llm_librarian_architecture.md b/llm_librarian_architecture.md
index aaede05..e3d24c4 100644
--- a/llm_librarian_architecture.md
+++ b/llm_librarian_architecture.md
@@ -275,29 +275,37 @@ timeline = lib.temporal_search("last month", context="creative")
 
 ## 🛠️ Implementation Phases
 
+### Automated Quality Assurance
+Each phase leverages **proactive agent coordination** to ensure quality:
+
+- **🧪 test-runner**: Validates each component before phase advancement
+- **📚 context-doc-manager**: Updates architecture documentation as implementation evolves
+- **🍎 applescript-ui-expert**: Ensures ADHD-friendly interface design
+- **🎯 dev-task-orchestrator**: Coordinates complex multi-component implementations
+
 ### Phase 1: Foundation (Week 1)
 - [ ] Basic file indexing system
-- [ ] Metadata extraction pipeline
+- [ ] Metadata extraction pipeline  
 - [ ] Simple text search
-- [ ] **TEST:** Index 1000 files in <1 hour
+- [ ] **TEST:** Index 1000 files in <1 hour (automated via test-runner)
 
 ### Phase 2: Intelligence (Week 2)
 - [ ] Embedding generation
 - [ ] Vector similarity search
 - [ ] Query parsing logic
-- [ ] **TEST:** Query response <2 seconds
+- [ ] **TEST:** Query response <2 seconds (automated via test-runner)
 
 ### Phase 3: Optimization (Week 3)
 - [ ] Smart caching system
 - [ ] Incremental indexing
 - [ ] Performance monitoring
-- [ ] **TEST:** Memory usage <4GB
+- [ ] **TEST:** Memory usage <4GB (continuous monitoring)
 
 ### Phase 4: Advanced Features (Week 4)
 - [ ] Relationship discovery
-- [ ] Temporal queries
+- [ ] Temporal queries  
 - [ ] Result ranking
-- [ ] **TEST:** Search accuracy >85%
+- [ ] **TEST:** Search accuracy >85% (automated validation)
 
 ## 🎯 Success Metrics
 
diff --git a/metadata_generator.py b/metadata_generator.py
index 97bcc48..4c39d1f 100644
--- a/metadata_generator.py
+++ b/metadata_generator.py
@@ -112,7 +112,15 @@ class MetadataGenerator:
     def _init_tracking_db(self):
         """Initialize SQLite database for tracking file metadata"""
         with sqlite3.connect(self.db_path) as conn:
-            conn.execute("""
+            # First, create the table with the current schema
+            self._create_tables(conn)
+            
+            # Then, migrate any missing columns
+            self._migrate_database_schema(conn)
+    
+    def _create_tables(self, conn):
+        """Create database tables with full schema"""
+        conn.execute("""
                 CREATE TABLE IF NOT EXISTS file_metadata (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     file_path TEXT UNIQUE,
@@ -152,6 +160,15 @@ class MetadataGenerator:
                     enhanced_filename TEXT,
                     organization_status TEXT,
                     
+                    -- Google Drive integration
+                    gdrive_upload BOOLEAN DEFAULT 0,
+                    gdrive_folder TEXT,
+                    gdrive_file_id TEXT,
+                    gdrive_category TEXT,
+                    gdrive_confidence REAL,
+                    upload_timestamp TEXT,
+                    space_freed_mb REAL,
+                    
                     -- Audio/Video specific (when applicable)
                     duration_seconds REAL,
                     audio_bitrate INTEGER,
@@ -165,7 +182,7 @@ class MetadataGenerator:
                 )
             """)
             
-            conn.execute("""
+        conn.execute("""
                 CREATE TABLE IF NOT EXISTS processing_sessions (
                     session_id TEXT PRIMARY KEY,
                     start_time TEXT,
@@ -179,7 +196,38 @@ class MetadataGenerator:
                 )
             """)
             
+        conn.commit()
+    
+    def _migrate_database_schema(self, conn):
+        """Migrate existing database to include Google Drive columns"""
+        try:
+            # Check if the gdrive_upload column exists
+            cursor = conn.execute("PRAGMA table_info(file_metadata)")
+            columns = [row[1] for row in cursor.fetchall()]
+            
+            # Add missing Google Drive columns
+            gdrive_columns = {
+                'gdrive_upload': 'BOOLEAN DEFAULT 0',
+                'gdrive_folder': 'TEXT',
+                'gdrive_file_id': 'TEXT', 
+                'gdrive_category': 'TEXT',
+                'gdrive_confidence': 'REAL',
+                'upload_timestamp': 'TEXT',
+                'space_freed_mb': 'REAL'
+            }
+            
+            for col_name, col_type in gdrive_columns.items():
+                if col_name not in columns:
+                    try:
+                        conn.execute(f"ALTER TABLE file_metadata ADD COLUMN {col_name} {col_type}")
+                        print(f"   ✅ Added column: {col_name}")
+                    except sqlite3.Error as e:
+                        print(f"   ⚠️  Could not add column {col_name}: {e}")
+            
             conn.commit()
+            
+        except sqlite3.Error as e:
+            print(f"   ⚠️  Database migration error: {e}")
     
     def analyze_file_comprehensive(self, file_path: Path) -> Dict[str, Any]:
         """Perform comprehensive analysis of a single file"""
diff --git a/system_specifications_v2.md b/system_specifications_v2.md
index 0458244..d8e7ed9 100644
--- a/system_specifications_v2.md
+++ b/system_specifications_v2.md
@@ -126,20 +126,28 @@ if "Payment Report" in filename:
     add_tags(["Financial", "Refinery", "Business"])
 ```
 
-## 🧪 Testing FMGMTework
+## 🧪 Testing Framework & Agent Coordination
+
+### Proactive Testing System
+This system includes **automated agents** that ensure continuous quality without manual intervention:
+
+- **🧪 test-runner**: Automatically executes comprehensive test suites after code changes
+- **📚 context-doc-manager**: Maintains documentation consistency with implementation
+- **🍎 applescript-ui-expert**: Ensures ADHD-friendly UI design principles
+- **🎯 dev-task-orchestrator**: Coordinates complex multi-component implementations
 
 ### Test Categories
-1. **Unit Tests:** Individual components
-2. **Integration Tests:** Component interactions  
-3. **User Experience Tests:** Real workflow validation
-4. **Performance Tests:** Speed and resource usage
-5. **Accuracy Tests:** Organization and search precision
+1. **Unit Tests:** Individual components (automated via test-runner)
+2. **Integration Tests:** Component interactions (automated via test-runner)
+3. **User Experience Tests:** Real workflow validation (guided by applescript-ui-expert)
+4. **Performance Tests:** Speed and resource usage (monitored continuously)
+5. **Accuracy Tests:** Organization and search precision (validated automatically)
 
 ### Testing Schedule
-- **After each feature completion**
-- **Before phase transitions**
-- **Weekly performance benchmarks**
-- **Monthly user experience reviews**
+- **After each feature completion** (agents trigger automatically)
+- **Before phase transitions** (agent coordination validates readiness)
+- **Weekly performance benchmarks** (automated monitoring)
+- **Monthly user experience reviews** (ADHD-friendly validation)
 
 ### Success Metrics
 - **Organization Accuracy:** >90% correct classifications
