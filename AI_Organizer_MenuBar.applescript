-- AI File Organizer Menu Bar Helper
-- Quick access menu for common AI File Organizer functions
-- Appears as a menu bar item for instant access

property organizerPath : "/Users/user/Github/ai-file-organizer"
property pythonCommand : "/usr/bin/python3"

on run
	try
		set quickChoice to choose from list {"🔍 Quick Search", "📁 Organize Downloads", "🎵 Analyze Audio File", "📊 System Status", "⚙️ Full Admin Panel", "❓ Help"} with title "AI File Organizer" with prompt "Quick Actions:" OK button name "Go" cancel button name "Close" with empty selection allowed
		
		if quickChoice is false or quickChoice is {} then
			return -- User cancelled or nothing selected
		end if
		
		set selectedAction to item 1 of quickChoice
		
		if selectedAction is "🔍 Quick Search" then
			quickSearch()
		else if selectedAction is "📁 Organize Downloads" then
			quickOrganizeDownloads()
		else if selectedAction is "🎵 Analyze Audio File" then
			quickAnalyzeAudio()
		else if selectedAction is "📊 System Status" then
			quickSystemStatus()
		else if selectedAction is "⚙️ Full Admin Panel" then
			tell application "Script Editor"
				open (organizerPath & "/AI_Organizer_Admin.applescript")
			end tell
			delay 1
			do shell script "osascript " & quoted form of (organizerPath & "/AI_Organizer_Admin.applescript")
		else if selectedAction is "❓ Help" then
			showQuickHelp()
		end if
		
	on error errorMsg
		display notification "Error: " & errorMsg with title "AI File Organizer" sound name "Basso"
	end try
end run

on quickSearch()
	try
		set searchQuery to text returned of (display dialog "Search your files:" default answer "" with title "AI Librarian")
		if searchQuery is not "" then
			
			-- Show progress
			display notification "Searching for: " & searchQuery with title "AI File Organizer" subtitle "Searching..."
			
			set searchCommand to "cd " & quoted form of organizerPath & " && timeout 30s " & pythonCommand & " enhanced_librarian.py search " & quoted form of searchQuery & " --mode auto --limit 5"
			set searchResults to do shell script searchCommand
			
			-- Show results in a clean format
			display dialog searchResults with title "Search Results" buttons {"New Search", "Open Admin", "Close"} default button "Close" 			
			set buttonResult to button returned of result
			if buttonResult is "New Search" then
				quickSearch()
			else if buttonResult is "Open Admin" then
				do shell script "osascript " & quoted form of (organizerPath & "/AI_Organizer_Admin.applescript")
			end if
		end if
	on error errorMsg
		display notification "Search failed: " & errorMsg with title "AI File Organizer" sound name "Basso"
	end try
end quickSearch

on quickOrganizeDownloads()
	try
		set modeChoice to choose from list {"👀 Preview Only", "✅ Organize Now"} with title "Organize Downloads" with prompt "Choose mode:" default items {"👀 Preview Only"}
		
		if modeChoice is not false then
			set selectedMode to item 1 of modeChoice
			set dryRunFlag to ""
			
			if selectedMode is "👀 Preview Only" then
				set dryRunFlag to " --dry-run"
				display notification "Previewing Downloads organization..." with title "AI File Organizer" subtitle "Analyzing files..."
			else
				set dryRunFlag to " --live"
				display notification "Organizing Downloads folder..." with title "AI File Organizer" subtitle "Moving files..."
			end if
			
			set organizeCommand to "cd " & quoted form of organizerPath & " && timeout 60s " & pythonCommand & " interactive_organizer.py organize" & dryRunFlag
			set organizeResults to do shell script organizeCommand
			
			if selectedMode is "👀 Preview Only" then
				display dialog "Organization Preview:" & return & return & organizeResults with title "Preview Results" buttons {"Organize Now", "Close"} default button "Close"
				if button returned of result is "Organize Now" then
					-- Run in live mode
					display notification "Organizing Downloads folder..." with title "AI File Organizer" subtitle "Moving files..."
					set liveCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " interactive_organizer.py organize --live"
					set liveResults to do shell script liveCommand
					display notification "Downloads organized!" with title "AI File Organizer" sound name "Glass"
				end if
			else
				display notification "Downloads organized!" with title "AI File Organizer" sound name "Glass"
				display dialog "Organization Complete!" & return & return & organizeResults with title "Organization Results" buttons {"OK"} default button "OK"
			end if
		end if
	on error errorMsg
		display notification "Organization failed: " & errorMsg with title "AI File Organizer" sound name "Basso"
	end try
end quickOrganizeDownloads

on quickAnalyzeAudio()
	try
		set audioFile to choose file with prompt "Choose audio file to analyze:" of type {"public.audio"}
		set filePath to POSIX path of audioFile
		set fileName to name of (info for audioFile)
		
		display notification "Analyzing: " & fileName with title "Audio AI" subtitle "Running analysis..."
		
		set analysisCommand to "cd " & quoted form of organizerPath & " && timeout 30s " & pythonCommand & " audio_cli.py analyze " & quoted form of filePath
		set analysisResults to do shell script analysisCommand
		
		display notification "Analysis complete!" with title "Audio AI" sound name "Glass"
		
		display dialog "Audio Analysis Results:" & return & return & analysisResults with title "Audio AI Analysis" buttons {"Analyze Another", "Close"} default button "Close"
		if button returned of result is "Analyze Another" then
			quickAnalyzeAudio()
		end if
		
	on error errorMsg
		if errorMsg contains "User canceled" then
			return
		end if
		display notification "Analysis failed: " & errorMsg with title "Audio AI" sound name "Basso"
	end try
end quickAnalyzeAudio

on quickSystemStatus()
	try
		display notification "Gathering system status..." with title "AI File Organizer" subtitle "Checking databases..."
		
		set statusCommand to "cd " & quoted form of organizerPath & " && timeout 20s " & pythonCommand & " -c \"
import sqlite3
from pathlib import Path

base_dir = Path.home() / 'Documents' / 'AI_ORGANIZER_BASE'
metadata_dir = base_dir / '04_METADATA_SYSTEM'

print('🤖 System Status Summary')
print('=' * 30)

# Quick database check
db_files = [
    ('Classifications', metadata_dir / 'interactive_classification.db'),
    ('Audio AI', metadata_dir / 'audio_ai_analysis' / 'audio_ai_analysis.db'),
    ('Creative AI', metadata_dir / 'creative_ai_partner.db'),
    ('Vector DB', metadata_dir / 'vector_librarian.db')
]

online_count = 0
total_size = 0

for name, path in db_files:
    if path.exists():
        size_mb = path.stat().st_size / (1024 * 1024)
        total_size += size_mb
        online_count += 1
        print(f'✅ {name}: {size_mb:.1f}MB')
    else:
        print(f'❌ {name}: Offline')

print(f'📊 {online_count}/{len(db_files)} systems online')
print(f'💾 Total data: {total_size:.1f}MB')

# Recent activity
try:
    with sqlite3.connect(metadata_dir / 'interactive_classification.db') as conn:
        cursor = conn.execute(\\\"SELECT COUNT(*) FROM classifications WHERE classified_date > datetime('now', '-7 days')\\\")
        recent = cursor.fetchone()[0]
        print(f'📈 Files processed (7d): {recent}')
except:
    print('📈 Activity data: N/A')
\""
		
		set statusResults to do shell script statusCommand
		
		display dialog statusResults with title "System Status" buttons {"Full Admin", "Refresh", "OK"} default button "OK"
		set buttonResult to button returned of result
		if buttonResult is "Full Admin" then
			do shell script "osascript " & quoted form of (organizerPath & "/AI_Organizer_Admin.applescript")
		else if buttonResult is "Refresh" then
			quickSystemStatus()
		end if
		
	on error errorMsg
		display notification "Status check failed: " & errorMsg with title "AI File Organizer" sound name "Basso"
	end try
end quickSystemStatus

on showQuickHelp()
	set helpText to "🤖 AI File Organizer Quick Help

🔍 SEARCH:
• Quick Search - Search all your files
• Use natural language queries
• Searches documents, emails, audio transcripts

📁 ORGANIZATION:
• Preview mode shows what will happen
• Live mode actually moves files  
• Files organized by content type & project

🎵 AUDIO AI:
• Analyzes content type (music/speech/interview)
• Extracts technical details (quality, duration)
• Can transcribe speech to text

📊 SYSTEM STATUS:
• Shows database health
• Recent activity summary
• Performance metrics

⚙️ FULL ADMIN:
• Complete system administration
• All advanced features
• Maintenance tools

💡 TIPS:
• Use Preview mode first to test
• Audio analysis works best with clear recordings
• Search supports partial matches
• System learns from your choices"
	
	display dialog helpText with title "AI File Organizer Help" buttons {"Open Full Admin", "Close"} default button "Close"
	if button returned of result is "Open Full Admin" then
		do shell script "osascript " & quoted form of (organizerPath & "/AI_Organizer_Admin.applescript")
	end if
end showQuickHelp

-- Specific function calls for automation/shortcuts
on searchFiles(query)
	set searchCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " enhanced_librarian.py search " & quoted form of query & " --mode auto --limit 3"
	return do shell script searchCommand
end searchFiles

on organizeFolder(folderPath, liveMode)
	set modeFlag to ""
	if liveMode then
		set modeFlag to " --live"
	else
		set modeFlag to " --dry-run"
	end if
	
	set organizeCommand to "cd " & quoted form of organizerPath & " && " & pythonCommand & " interactive_organizer.py quick " & quoted form of folderPath & modeFlag
	return do shell script organizeCommand
end organizeFolder