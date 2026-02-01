-- AI File Organizer Admin Interface
-- Native macOS administration interface for the AI File Organizer system
-- Provides full system management with native UI elements

property organizerPath : "/Users/user/Github/ai-file-organizer"
property pythonCommand : "/usr/bin/python3"

-- Main admin interface
on run
	try
		set adminChoice to choose from list {"🔍 Search & Librarian", "🗂️ File Organization", "🎵 Audio AI Analysis", "🎭 Creative AI Tools", "🏷️ Tagging System", "📊 System Status", "⚙️ System Maintenance"} with title "AI File Organizer Admin" with prompt "Choose an administration area:" default items {"📊 System Status"} OK button name "Open" cancel button name "Quit"
		
		if adminChoice is false then
			return -- User cancelled
		end if
		
		set selectedArea to item 1 of adminChoice
		
		if selectedArea is "🔍 Search & Librarian" then
			showLibrarianInterface()
		else if selectedArea is "🗂️ File Organization" then
			showOrganizationInterface()
		else if selectedArea is "🎵 Audio AI Analysis" then
			showAudioInterface()
		else if selectedArea is "🎭 Creative AI Tools" then
			showCreativeInterface()
		else if selectedArea is "🏷️ Tagging System" then
			showTaggingInterface()
		else if selectedArea is "📊 System Status" then
			showSystemStatus()
		else if selectedArea is "⚙️ System Maintenance" then
			showMaintenanceInterface()
		end if
		
	on error errorMsg
		display alert "Admin Interface Error" message errorMsg as critical
	end try
end run

-- === LIBRARIAN & SEARCH INTERFACE ===
on showLibrarianInterface()
	set librarianChoice to choose from list {"🔍 Quick Search", "🧠 Semantic Search", "📧 Email Search", "📝 Index New Content", "📊 Search Statistics", "🔄 Rebuild Vector Database"} with title "Librarian & Search Admin" with prompt "Choose a librarian function:" OK button name "Execute" cancel button name "Back"
	
	if librarianChoice is false then
		run -- Go back to main menu
		return
	end if
	
	set selectedFunction to item 1 of librarianChoice
	
	if selectedFunction is "🔍 Quick Search" then
		performQuickSearch()
	else if selectedFunction is "🧠 Semantic Search" then
		performSemanticSearch()
	else if selectedFunction is "📧 Email Search" then
		performEmailSearch()
	else if selectedFunction is "📝 Index New Content" then
		indexNewContent()
	else if selectedFunction is "📊 Search Statistics" then
		showSearchStats()
	else if selectedFunction is "🔄 Rebuild Vector Database" then
		rebuildVectorDB()
	end if
end showLibrarianInterface

on performQuickSearch()
	set searchQuery to text returned of (display dialog "Enter search query:" default answer "" with title "Quick Search")
	if searchQuery is not "" then
		set searchCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " enhanced_librarian.py search " & quoted form of searchQuery & " --mode fast"
		set searchResults to do shell script searchCommand
		
		display dialog searchResults with title "Search Results" buttons {"New Search", "OK"} default button "OK"
		if button returned of result is "New Search" then
			performQuickSearch()
		end if
	end if
end performQuickSearch

on performSemanticSearch()
	set searchQuery to text returned of (display dialog "Enter semantic search query:" default answer "" with title "Semantic Search")
	if searchQuery is not "" then
		display dialog "Running semantic search... This may take a moment." with title "Processing" giving up after 2
		
		set searchCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " enhanced_librarian.py search " & quoted form of searchQuery & " --mode semantic"
		set searchResults to do shell script searchCommand
		
		display dialog searchResults with title "Semantic Search Results" buttons {"New Search", "OK"} default button "OK"
		if button returned of result is "New Search" then
			performSemanticSearch()
		end if
	end if
end performSemanticSearch

on performEmailSearch()
	set emailQuery to text returned of (display dialog "Enter email search query:" default answer "" with title "Email Search")
	if emailQuery is not "" then
		display dialog "Searching emails... This may take a moment." with title "Processing" giving up after 2
		
		set emailCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " enhanced_librarian.py search " & quoted form of emailQuery & " --mode email"
		set emailResults to do shell script emailCommand
		
		display dialog emailResults with title "Email Search Results" buttons {"New Search", "OK"} default button "OK"
		if button returned of result is "New Search" then
			performEmailSearch()
		end if
	end if
end performEmailSearch

on indexNewContent()
	set folderChoice to choose folder with prompt "Choose folder to index:" default location (path to documents folder)
	set folderPath to POSIX path of folderChoice
	
	display dialog "Indexing folder: " & folderPath & return & return & "This will add all supported files to the searchable database. Continue?" with title "Index New Content" buttons {"Cancel", "Index"} default button "Index"
	
	if button returned of result is "Index" then
		display dialog "Indexing content... This may take several minutes." with title "Indexing" giving up after 3
		
		set indexCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " enhanced_librarian.py index --folder " & quoted form of folderPath
		set indexResults to do shell script indexCommand
		
		display dialog "Indexing Complete!" & return & return & indexResults with title "Indexing Results" buttons {"OK"} default button "OK"
	end if
end indexNewContent

on showSearchStats()
	set statsCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " enhanced_librarian.py stats"
	set statsResults to do shell script statsCommand
	
	display dialog statsResults with title "Search Statistics" buttons {"Refresh", "OK"} default button "OK"
	if button returned of result is "Refresh" then
		showSearchStats()
	end if
end showSearchStats

on rebuildVectorDB()
	display dialog "This will rebuild the entire vector database. This process may take 10-30 minutes depending on your content volume. Continue?" with title "Rebuild Vector Database" buttons {"Cancel", "Rebuild"} default button "Cancel"
	
	if button returned of result is "Rebuild" then
		display dialog "Rebuilding vector database... This will take a while. Check Terminal for progress." with title "Rebuilding" giving up after 5
		
		set rebuildCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " vector_librarian.py"
		do shell script rebuildCommand
		
		display dialog "Vector database rebuild complete!" with title "Rebuild Complete" buttons {"OK"} default button "OK"
	end if
end rebuildVectorDB

-- === FILE ORGANIZATION INTERFACE ===
on showOrganizationInterface()
	set orgChoice to choose from list {"📁 Organize Downloads", "📄 Organize Specific File", "🗂️ Organize Custom Folder", "📊 Organization Stats", "🔄 Process Staging Area", "⚙️ Organization Settings"} with title "File Organization Admin" with prompt "Choose an organization function:" OK button name "Execute" cancel button name "Back"
	
	if orgChoice is false then
		run -- Go back to main menu
		return
	end if
	
	set selectedFunction to item 1 of orgChoice
	
	if selectedFunction is "📁 Organize Downloads" then
		organizeDownloads()
	else if selectedFunction is "📄 Organize Specific File" then
		organizeSpecificFile()
	else if selectedFunction is "🗂️ Organize Custom Folder" then
		organizeCustomFolder()
	else if selectedFunction is "📊 Organization Stats" then
		showOrganizationStats()
	else if selectedFunction is "🔄 Process Staging Area" then
		processStagingArea()
	else if selectedFunction is "⚙️ Organization Settings" then
		showOrganizationSettings()
	end if
end showOrganizationInterface

on organizeDownloads()
	set modeChoice to choose from list {"🔍 Preview (Dry Run)", "✅ Execute (Live Mode)"} with title "Organize Downloads" with prompt "Choose organization mode:" default items {"🔍 Preview (Dry Run)"}
	
	if modeChoice is not false then
		set selectedMode to item 1 of modeChoice
		set dryRunFlag to ""
		if selectedMode is "🔍 Preview (Dry Run)" then
			set dryRunFlag to " --dry-run"
		else
			set dryRunFlag to " --live"
		end if
		
		display dialog "Organizing Downloads folder..." with title "Processing" giving up after 2
		
		set organizeCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " interactive_organizer.py organize" & dryRunFlag
		set organizeResults to do shell script organizeCommand
		
		display dialog organizeResults with title "Organization Results" buttons {"OK"} default button "OK"
	end if
end organizeDownloads

on organizeSpecificFile()
	set fileChoice to choose file with prompt "Choose file to organize:" default location (path to downloads folder)
	set filePath to POSIX path of fileChoice
	
	set modeChoice to choose from list {"🔍 Preview (Dry Run)", "✅ Execute (Live Mode)"} with title "Organize File" with prompt "Choose organization mode:" default items {"🔍 Preview (Dry Run)"}
	
	if modeChoice is not false then
		set selectedMode to item 1 of modeChoice
		set dryRunFlag to ""
		if selectedMode is "🔍 Preview (Dry Run)" then
			set dryRunFlag to " --dry-run"
		else
			set dryRunFlag to " --live"
		end if
		
		display dialog "Organizing file: " & (name of (info for fileChoice)) & "..." with title "Processing" giving up after 2
		
		set organizeCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " interactive_organizer.py file " & quoted form of filePath & dryRunFlag
		set organizeResults to do shell script organizeCommand
		
		display dialog organizeResults with title "Organization Results" buttons {"OK"} default button "OK"
	end if
end organizeSpecificFile

on organizeCustomFolder()
	set folderChoice to choose folder with prompt "Choose folder to organize:" default location (path to documents folder)
	set folderPath to POSIX path of folderChoice
	
	set modeChoice to choose from list {"🔍 Preview (Dry Run)", "✅ Execute (Live Mode)"} with title "Organize Folder" with prompt "Choose organization mode:" default items {"🔍 Preview (Dry Run)"}
	
	if modeChoice is not false then
		set selectedMode to item 1 of modeChoice
		set dryRunFlag to ""
		if selectedMode is "🔍 Preview (Dry Run)" then
			set dryRunFlag to " --dry-run"
		else
			set dryRunFlag to " --live"
		end if
		
		display dialog "Organizing folder: " & folderPath & "..." with title "Processing" giving up after 2
		
		set organizeCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " interactive_organizer.py quick " & quoted form of folderPath & dryRunFlag
		set organizeResults to do shell script organizeCommand
		
		display dialog organizeResults with title "Organization Results" buttons {"OK"} default button "OK"
	end if
end organizeCustomFolder

on showOrganizationStats()
	set statsCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " learning_stats.py"
	set statsResults to do shell script statsCommand
	
	display dialog statsResults with title "Organization Statistics" buttons {"Refresh", "OK"} default button "OK"
	if button returned of result is "Refresh" then
		showOrganizationStats()
	end if
end showOrganizationStats

on processStagingArea()
	display dialog "This will process all files in the staging area with interactive classification. Continue?" with title "Process Staging" buttons {"Cancel", "Process"} default button "Process"
	
	if button returned of result is "Process" then
		set stagingCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " staging_monitor.py"
		set stagingResults to do shell script stagingCommand
		
		display dialog stagingResults with title "Staging Results" buttons {"OK"} default button "OK"
	end if
end processStagingArea

-- === AUDIO AI INTERFACE ===
on showAudioInterface()
	set audioChoice to choose from list {"🎵 Analyze Audio File", "📁 Analyze Audio Folder", "🔍 Search Audio Files", "📊 Audio Statistics", "🎙️ Transcribe Audio"} with title "Audio AI Admin" with prompt "Choose an audio function:" OK button name "Execute" cancel button name "Back"
	
	if audioChoice is false then
		run -- Go back to main menu
		return
	end if
	
	set selectedFunction to item 1 of audioChoice
	
	if selectedFunction is "🎵 Analyze Audio File" then
		analyzeAudioFile()
	else if selectedFunction is "📁 Analyze Audio Folder" then
		analyzeAudioFolder()
	else if selectedFunction is "🔍 Search Audio Files" then
		searchAudioFiles()
	else if selectedFunction is "📊 Audio Statistics" then
		showAudioStats()
	else if selectedFunction is "🎙️ Transcribe Audio" then
		transcribeAudio()
	end if
end showAudioInterface

on analyzeAudioFile()
	set audioFile to choose file with prompt "Choose audio file to analyze:" of type {"public.audio"}
	set filePath to POSIX path of audioFile
	
	set optionsChoice to choose from list {"📊 Basic Analysis", "📝 With Transcription", "🔧 Technical Details"} with title "Analysis Options" with prompt "Choose analysis type:" default items {"📊 Basic Analysis"}
	
	if optionsChoice is not false then
		set selectedOption to item 1 of optionsChoice
		set analysisFlags to ""
		
		if selectedOption is "📝 With Transcription" then
			set analysisFlags to " --transcribe"
		else if selectedOption is "🔧 Technical Details" then
			set analysisFlags to " --details"
		end if
		
		display dialog "Analyzing audio file... This may take a moment." with title "Processing" giving up after 3
		
		set analysisCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " audio_cli.py analyze " & quoted form of filePath & analysisFlags
		set analysisResults to do shell script analysisCommand
		
		display dialog analysisResults with title "Audio Analysis Results" buttons {"OK"} default button "OK"
	end if
end analyzeAudioFile

on analyzeAudioFolder()
	set audioFolder to choose folder with prompt "Choose folder containing audio files:"
	set folderPath to POSIX path of audioFolder
	
	set transcribeChoice to choose from list {"Without Transcription", "With Transcription"} with title "Transcription Option" with prompt "Include transcription for speech files?" default items {"Without Transcription"}
	
	set transcribeFlag to ""
	if transcribeChoice is not false and item 1 of transcribeChoice is "With Transcription" then
		set transcribeFlag to " --transcribe"
	end if
	
	display dialog "Analyzing all audio files in folder... This may take several minutes." with title "Processing" giving up after 3
	
	set analysisCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " audio_cli.py directory " & quoted form of folderPath & transcribeFlag
	set analysisResults to do shell script analysisCommand
	
	display dialog analysisResults with title "Audio Folder Analysis Results" buttons {"OK"} default button "OK"
end analyzeAudioFolder

on searchAudioFiles()
	set searchQuery to text returned of (display dialog "Enter audio search query:" default answer "" with title "Audio Search")
	if searchQuery is not "" then
		set searchCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " audio_cli.py search " & quoted form of searchQuery
		set searchResults to do shell script searchCommand
		
		display dialog searchResults with title "Audio Search Results" buttons {"New Search", "OK"} default button "OK"
		if button returned of result is "New Search" then
			searchAudioFiles()
		end if
	end if
end searchAudioFiles

on showAudioStats()
	set statsCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " audio_cli.py stats"
	set statsResults to do shell script statsCommand
	
	display dialog statsResults with title "Audio Statistics" buttons {"Refresh", "OK"} default button "OK"
	if button returned of result is "Refresh" then
		showAudioStats()
	end if
end showAudioStats

-- === CREATIVE AI INTERFACE ===
on showCreativeInterface()
	set creativeChoice to choose from list {"🎭 Analyze Creative File", "📁 Analyze Creative Folder", "🌌 Story Universe", "💡 Generate Ideas", "🎬 Project Overview", "👤 Character Search"} with title "Creative AI Admin" with prompt "Choose a creative function:" OK button name "Execute" cancel button name "Back"
	
	if creativeChoice is false then
		run -- Go back to main menu
		return
	end if
	
	set selectedFunction to item 1 of creativeChoice
	
	if selectedFunction is "🎭 Analyze Creative File" then
		analyzeCreativeFile()
	else if selectedFunction is "📁 Analyze Creative Folder" then
		analyzeCreativeFolder()
	else if selectedFunction is "🌌 Story Universe" then
		showUniverseInterface()
	else if selectedFunction is "💡 Generate Ideas" then
		generateCreativeIdeas()
	else if selectedFunction is "🎬 Project Overview" then
		showProjectOverview()
	else if selectedFunction is "👤 Character Search" then
		searchCharacters()
	end if
end showCreativeInterface

on analyzeCreativeFile()
	set creativeFile to choose file with prompt "Choose creative file to analyze:" of type {"public.text", "com.adobe.pdf", "org.openxmlformats.wordprocessingml.document"}
	set filePath to POSIX path of creativeFile
	
	display dialog "Analyzing creative content... This may take a moment." with title "Processing" giving up after 3
	
	set analysisCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " creative_cli.py analyze " & quoted form of filePath & " --details"
	set analysisResults to do shell script analysisCommand
	
	display dialog analysisResults with title "Creative Analysis Results" buttons {"OK"} default button "OK"
end analyzeCreativeFile

on analyzeCreativeFolder()
	set creativeFolder to choose folder with prompt "Choose folder containing creative files:"
	set folderPath to POSIX path of creativeFolder
	
	display dialog "Analyzing all creative files in folder... This may take several minutes." with title "Processing" giving up after 3
	
	set analysisCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " creative_cli.py directory " & quoted form of folderPath
	set analysisResults to do shell script analysisCommand
	
	display dialog analysisResults with title "Creative Folder Analysis Results" buttons {"OK"} default button "OK"
end analyzeCreativeFolder

on showUniverseInterface()
	set universeChoice to choose from list {"🏗️ Build Universe", "🌟 Universe Overview", "🔍 Explore Connections", "🎭 Story Clusters", "💡 Development Suggestions"} with title "Story Universe" with prompt "Choose universe function:" OK button name "Execute" cancel button name "Back"
	
	if universeChoice is not false then
		set selectedFunction to item 1 of universeChoice
		
		if selectedFunction is "🏗️ Build Universe" then
			set buildCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " universe_cli.py build"
			set buildResults to do shell script buildCommand
			display dialog buildResults with title "Universe Build Results" buttons {"OK"} default button "OK"
			
		else if selectedFunction is "🌟 Universe Overview" then
			set overviewCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " universe_cli.py overview --detailed"
			set overviewResults to do shell script overviewCommand
			display dialog overviewResults with title "Universe Overview" buttons {"OK"} default button "OK"
			
		else if selectedFunction is "🔍 Explore Connections" then
			set searchTerm to text returned of (display dialog "Enter character/element name:" default answer "" with title "Explore Connections")
			if searchTerm is not "" then
				set connectCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " universe_cli.py connections " & quoted form of searchTerm & " --context"
				set connectResults to do shell script connectCommand
				display dialog connectResults with title "Story Connections" buttons {"OK"} default button "OK"
			end if
			
		else if selectedFunction is "🎭 Story Clusters" then
			set clusterCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " universe_cli.py clusters --detailed"
			set clusterResults to do shell script clusterCommand
			display dialog clusterResults with title "Story Clusters" buttons {"OK"} default button "OK"
			
		else if selectedFunction is "💡 Development Suggestions" then
			set suggestCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " universe_cli.py suggest"
			set suggestResults to do shell script suggestCommand
			display dialog suggestResults with title "Development Suggestions" buttons {"OK"} default button "OK"
		end if
	end if
end showUniverseInterface

on generateCreativeIdeas()
	set ideaTypeChoice to choose from list {"Mixed Ideas", "Plot Twists", "Character Development", "Theme Exploration", "Crossover Concepts"} with title "Generate Ideas" with prompt "Choose idea type:" default items {"Mixed Ideas"}
	
	if ideaTypeChoice is not false then
		set selectedType to item 1 of ideaTypeChoice
		set ideaFlag to ""
		
		if selectedType is "Plot Twists" then
			set ideaFlag to " --type plot_twist"
		else if selectedType is "Character Development" then
			set ideaFlag to " --type character_development"
		else if selectedType is "Theme Exploration" then
			set ideaFlag to " --type theme_exploration"
		else if selectedType is "Crossover Concepts" then
			set ideaFlag to " --type crossover_concepts"
		end if
		
		display dialog "Generating creative ideas... This may take a moment." with title "Processing" giving up after 3
		
		-- Generate ideas using the creative idea generator
		set ideaCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " -c \"from creative_idea_generator import CreativeIdeaGenerator; gen = CreativeIdeaGenerator(); ideas = gen.generate_ideas('mixed' if '" & selectedType & "' == 'Mixed Ideas' else '" & selectedType & "'.lower().replace(' ', '_'), 3); [print(f'{i+1}. {idea.title}\\n   {idea.description}\\n   Tags: {\\', \\'.join(idea.genre_tags)}\\n') for i, idea in enumerate(ideas)]\""
		set ideaResults to do shell script ideaCommand
		
		display dialog ideaResults with title "Creative Ideas Generated" buttons {"Generate More", "OK"} default button "OK"
		if button returned of result is "Generate More" then
			generateCreativeIdeas()
		end if
	end if
end generateCreativeIdeas

-- === TAGGING INTERFACE ===
on showTaggingInterface()
	set taggingChoice to choose from list {"🏷️ Tag File", "📁 Tag Folder", "🔍 Search by Tags", "📊 Tag Statistics", "💡 Tag Suggestions"} with title "Tagging System Admin" with prompt "Choose a tagging function:" OK button name "Execute" cancel button name "Back"
	
	if taggingChoice is false then
		run -- Go back to main menu
		return
	end if
	
	set selectedFunction to item 1 of taggingChoice
	
	if selectedFunction is "🏷️ Tag File" then
		tagSingleFile()
	else if selectedFunction is "📁 Tag Folder" then
		tagFolder()
	else if selectedFunction is "🔍 Search by Tags" then
		searchByTags()
	else if selectedFunction is "📊 Tag Statistics" then
		showTagStats()
	else if selectedFunction is "💡 Tag Suggestions" then
		showTagSuggestions()
	end if
end showTaggingInterface

on tagSingleFile()
	set fileToTag to choose file with prompt "Choose file to tag:"
	set filePath to POSIX path of fileToTag
	
	set userTags to text returned of (display dialog "Enter custom tags (comma-separated):" default answer "" with title "Add Custom Tags")
	
	set tagCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " tagging_cli.py tag " & quoted form of filePath
	if userTags is not "" then
		set tagCommand to tagCommand & " --user-tags " & quoted form of userTags
	end if
	set tagCommand to tagCommand & " --suggestions"
	
	set tagResults to do shell script tagCommand
	
	display dialog tagResults with title "File Tagging Results" buttons {"OK"} default button "OK"
end tagSingleFile

on tagFolder()
	set folderToTag to choose folder with prompt "Choose folder to tag:"
	set folderPath to POSIX path of folderToTag
	
	display dialog "Tagging all supported files in folder... This may take several minutes." with title "Processing" giving up after 3
	
	set tagCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " tagging_cli.py directory " & quoted form of folderPath
	set tagResults to do shell script tagCommand
	
	display dialog tagResults with title "Folder Tagging Results" buttons {"OK"} default button "OK"
end tagFolder

on searchByTags()
	set tagQuery to text returned of (display dialog "Enter tags to search for (comma-separated):" default answer "" with title "Tag Search")
	if tagQuery is not "" then
		set searchCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " tagging_cli.py search " & quoted form of tagQuery
		set searchResults to do shell script searchCommand
		
		display dialog searchResults with title "Tag Search Results" buttons {"New Search", "OK"} default button "OK"
		if button returned of result is "New Search" then
			searchByTags()
		end if
	end if
end searchByTags

-- === SYSTEM STATUS & MAINTENANCE ===
on showSystemStatus()
	display dialog "Gathering system information..." with title "System Status" giving up after 2
	
	set statusCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " -c \"
import sqlite3
from pathlib import Path
import os

# Check databases
base_dir = Path.home() / 'Documents' / 'AI_ORGANIZER_BASE'
metadata_dir = Path.home() / 'Documents' / 'AI_METADATA_SYSTEM'

print('🤖 AI File Organizer System Status')
print('=' * 50)
print(f'📁 Base Directory: {base_dir}')
print(f'📊 Metadata Directory: {metadata_dir}')
print()

# Check database sizes
db_files = {
    'Interactive Classification': metadata_dir / 'interactive_classification.db',
    'Vector Database': metadata_dir / 'vector_librarian.db', 
    'Creative AI': metadata_dir / 'creative_ai_partner.db',
    'Audio AI': metadata_dir / 'audio_ai_analysis' / 'audio_ai_analysis.db',
    'Tagging System': metadata_dir / 'tagging_system' / 'tagging_system.db',
    'Story Universe': metadata_dir / 'story_universe' / 'story_universe.db'
}

print('📊 Database Status:')
total_size = 0
for name, path in db_files.items():
    if path.exists():
        size_mb = path.stat().st_size / (1024 * 1024)
        total_size += size_mb
        print(f'   ✅ {name}: {size_mb:.1f} MB')
    else:
        print(f'   ❌ {name}: Not found')

print(f'   📈 Total Database Size: {total_size:.1f} MB')
print()

# Check recent activity
try:
    with sqlite3.connect(metadata_dir / 'interactive_classification.db') as conn:
        cursor = conn.execute(\\\"SELECT COUNT(*) FROM classifications WHERE classified_date > datetime('now', '-7 days')\\\")
        recent_classifications = cursor.fetchone()[0]
        print(f'📈 Recent Activity (7 days):')
        print(f'   📄 Files classified: {recent_classifications}')
except:
    print('📈 Recent Activity: Database not accessible')
\""
	
	set statusResults to do shell script statusCommand
	
	set statusChoice to choose from list {"🔄 Refresh Status", "🧹 System Maintenance", "📊 Detailed Stats", "❌ Close"} with title "System Status" with prompt statusResults default items {"❌ Close"}
	
	if statusChoice is not false then
		set selectedAction to item 1 of statusChoice
		
		if selectedAction is "🔄 Refresh Status" then
			showSystemStatus()
		else if selectedAction is "🧹 System Maintenance" then
			showMaintenanceInterface()
		else if selectedAction is "📊 Detailed Stats" then
			showDetailedStats()
		end if
	end if
end showSystemStatus

on showMaintenanceInterface()
	set maintenanceChoice to choose from list {"🧹 Clean Temp Files", "📊 Optimize Databases", "🔄 Backup System", "📈 Export Statistics", "⚙️ Reset Preferences", "🔧 Rebuild Indexes"} with title "System Maintenance" with prompt "Choose maintenance task:" OK button name "Execute" cancel button name "Back"
	
	if maintenanceChoice is not false then
		set selectedTask to item 1 of maintenanceChoice
		
		if selectedTask is "🧹 Clean Temp Files" then
			display dialog "This will clean temporary files and caches. Continue?" with title "Clean Temp Files" buttons {"Cancel", "Clean"} default button "Clean"
			if button returned of result is "Clean" then
				set cleanCommand to "find /tmp -name '*ai_organizer*' -delete 2>/dev/null; find " & quoted form of organizerPath & " -name '*.pyc' -delete 2>/dev/null; echo 'Temporary files cleaned.'"
				set cleanResults to do shell script cleanCommand
				display dialog cleanResults with title "Cleanup Complete" buttons {"OK"} default button "OK"
			end if
			
		else if selectedTask is "📊 Optimize Databases" then
			display dialog "This will optimize all databases for better performance. Continue?" with title "Optimize Databases" buttons {"Cancel", "Optimize"} default button "Optimize"
			if button returned of result is "Optimize" then
				display dialog "Optimizing databases... This may take a few minutes." with title "Optimizing" giving up after 3
				set optimizeCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " -c \"
import sqlite3
from pathlib import Path
base_dir = Path.home() / 'Documents' / 'AI_ORGANIZER_BASE'
metadata_dir = Path.home() / 'Documents' / 'AI_METADATA_SYSTEM'
databases = list(metadata_dir.rglob('*.db'))
for db in databases:
    try:
        with sqlite3.connect(db) as conn:
            conn.execute('VACUUM')
            conn.execute('ANALYZE')
        print(f'Optimized: {db.name}')
    except Exception as e:
        print(f'Error optimizing {db.name}: {e}')
print('Database optimization complete.')
\""
				set optimizeResults to do shell script optimizeCommand
				display dialog optimizeResults with title "Optimization Complete" buttons {"OK"} default button "OK"
			end if
			
		else if selectedTask is "🔄 Backup System" then
			set backupFolder to choose folder with prompt "Choose backup destination:" default location (path to documents folder)
			set backupPath to POSIX path of backupFolder
			
			display dialog "Creating system backup... This may take several minutes." with title "Backing Up" giving up after 3
			set backupCommand to "cd " & quoted form of organizerPath & " && tar -czf " & quoted form of (backupPath & "ai_organizer_backup_" & (do shell script "date +%Y%m%d_%H%M%S") & ".tar.gz") & " --exclude='*.pyc' --exclude='__pycache__' ."
			do shell script backupCommand
			display dialog "Backup created successfully in " & backupPath with title "Backup Complete" buttons {"OK"} default button "OK"
		end if
	end if
end showMaintenanceInterface

on showDetailedStats()
	set detailedCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " -c \"
print('📊 Detailed System Statistics')
print('=' * 60)

# File organization stats
try:
    from learning_stats import LearningStatistics
    stats = LearningStatistics()
    recent_stats = stats.get_recent_performance()
    print('🗂️ Organization Performance:')
    print(f'   Files processed: {recent_stats.get(\\\"total_processed\\\", 0)}')
    print(f'   High confidence: {recent_stats.get(\\\"high_confidence\\\", 0)}')
    print(f'   Questions asked: {recent_stats.get(\\\"questions_asked\\\", 0)}')
except Exception as e:
    print(f'Organization stats error: {e}')

print()

# Audio analysis stats  
try:
    from audio_ai_analyzer import AudioAIAnalyzer
    analyzer = AudioAIAnalyzer()
    import sqlite3
    with sqlite3.connect(analyzer.db_path) as conn:
        cursor = conn.execute('SELECT COUNT(*), AVG(duration_seconds), AVG(confidence_score) FROM audio_analysis')
        audio_count, avg_duration, avg_confidence = cursor.fetchone()
        print('🎵 Audio Analysis Stats:')
        print(f'   Files analyzed: {audio_count or 0}')
        print(f'   Average duration: {(avg_duration or 0)/60:.1f} minutes')  
        print(f'   Average confidence: {(avg_confidence or 0):.2f}')
except Exception as e:
    print(f'Audio stats error: {e}')

print()

# Creative analysis stats
try:
    from creative_ai_partner import CreativeAIPartner
    partner = CreativeAIPartner()
    with sqlite3.connect(partner.db_path) as conn:
        cursor = conn.execute('SELECT COUNT(*) FROM file_analysis')
        creative_count = cursor.fetchone()[0]
        cursor = conn.execute('SELECT COUNT(DISTINCT project_identified) FROM file_analysis WHERE project_identified IS NOT NULL')
        project_count = cursor.fetchone()[0]
        print('🎭 Creative Analysis Stats:')
        print(f'   Creative files: {creative_count}')
        print(f'   Projects: {project_count}')
except Exception as e:
    print(f'Creative stats error: {e}')
\""
	
	set detailedResults to do shell script detailedCommand
	
	display dialog detailedResults with title "Detailed Statistics" buttons {"Export to File", "OK"} default button "OK"
	
	if button returned of result is "Export to File" then
		set exportPath to (path to desktop as string) & "AI_Organizer_Stats_" & (do shell script "date +%Y%m%d_%H%M%S") & ".txt"
		
		set exportFile to open for access file exportPath with write permission
		write detailedResults to exportFile
		close access exportFile
		
		display dialog "Statistics exported to:" & return & exportPath with title "Export Complete" buttons {"OK"} default button "OK"
	end if
end showDetailedStats

-- Quick launch functions for menu bar access
on launchQuickSearch()
	performQuickSearch()
end launchQuickSearch

on launchOrganizeDownloads()
	organizeDownloads()
end launchOrganizeDownloads

on launchSystemStatus()
	showSystemStatus()
end launchSystemStatus