-- AI File Organizer - System Status Interface
-- User Thomson's File Organization Status Tool

-- Configuration
set pythonPath to "/Users/user/py312_env/bin/python"
set librarianPath to "/Users/user/Github/ai-file-organizer/librarian.py"

-- Main execution
try
	-- Show progress
	display notification "Checking system status..." with title "AI File Organizer"
	
	-- Get system status
	set statusCommand to pythonPath & " " & quoted form of librarianPath & " status"
	set statusResults to do shell script statusCommand
	
	-- Format and show status
	set formattedStatus to formatStatusResults(statusResults)
	
	-- Show status dialog with action options
	display dialog formattedStatus with title "AI File Organizer - System Status" buttons {"Search Files", "Organize Files", "Index Content", "Done"} default button "Done" with icon note giving up after 60
	
	set buttonPressed to button returned of result
	
	-- Handle button actions
	if buttonPressed is "Search Files" then
		-- Launch search interface
		do shell script "osascript " & quoted form of "/Users/user/Github/ai-file-organizer/File_Search_GUI.applescript" & " &"
	else if buttonPressed is "Organize Files" then
		-- Run organization (dry run)
		display notification "Running file organization (dry run)..." with title "AI File Organizer"
		set organizeCommand to pythonPath & " " & quoted form of librarianPath & " organize --dry-run"
		set organizeResults to do shell script organizeCommand
		display dialog "📋 Organization Preview:" & return & return & organizeResults with title "File Organization Results" buttons {"OK"} default button "OK" with icon note
	else if buttonPressed is "Index Content" then
		-- Run content indexing
		display notification "Indexing content..." with title "AI File Organizer"
		set indexCommand to pythonPath & " " & quoted form of librarianPath & " index"
		set indexResults to do shell script indexCommand
		display dialog "📚 Indexing Complete:" & return & return & indexResults with title "Content Indexing Results" buttons {"OK"} default button "OK" with icon note
	end if
	
on error errMsg number errNum
	if errNum is not -128 then -- User didn't cancel
		display dialog "❌ Error: " & errMsg with title "Status Error" buttons {"OK"} default button "OK" with icon stop
	end if
end try

-- Format status results for display
on formatStatusResults(rawResults)
	try
		set resultLines to paragraphs of rawResults
		set formattedText to ""
		set inStatusSection to false
		
		repeat with currentLine in resultLines
			set lineText to currentLine as string
			
			-- Check for status section
			if lineText contains "System Status" then
				set inStatusSection to true
				set formattedText to formattedText & "📊 " & lineText & return & return
			else if inStatusSection then
				-- Format status lines
				if lineText contains "📝 Content Index:" then
					set formattedText to formattedText & lineText & return
				else if lineText contains "Files indexed:" or lineText contains "Success rate:" or lineText contains "Total content:" then
					set formattedText to formattedText & "    " & lineText & return
				else if lineText contains "⏰ Staging System:" then
					set formattedText to formattedText & return & lineText & return
				else if lineText contains "Active files:" or lineText contains "Ready to organize:" or lineText contains "Overdue files:" or lineText contains "Avg staging days:" then
					set formattedText to formattedText & "    " & lineText & return
				else if lineText contains "🔄 Last updated:" then
					set formattedText to formattedText & return & lineText & return
				end if
			end if
		end repeat
		
		if formattedText is "" then
			return "⚠️ Could not retrieve system status."
		else
			return formattedText
		end if
		
	on error
		return "⚠️ Could not format status properly." & return & return & rawResults
	end try
end formatStatusResults