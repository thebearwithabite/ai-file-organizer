-- AI File Organizer - Quick Search from Menubar
-- User Thomson's Quick File Search Tool

-- Configuration
set pythonPath to "/Users/user/py312_env/bin/python"
set librarianPath to "/Users/user/Github/ai-file-organizer/librarian.py"

-- Quick search with minimal interface
try
	-- Get search term with a simpler dialog
	set searchQuery to text returned of (display dialog "🔍 Quick File Search:" with title "AI File Organizer" default answer "" buttons {"Cancel", "Search"} default button "Search")
	
	if searchQuery is not "" then
		-- Run search with fewer results for speed
		set searchCommand to pythonPath & " " & quoted form of librarianPath & " search " & quoted form of searchQuery & " --limit 5"
		set searchResults to do shell script searchCommand
		
		-- Extract just the file names and paths for quick results
		set quickResults to extractQuickResults(searchResults)
		
		if quickResults is not "" then
			-- Show quick results with option to see more
			display dialog "🔍 Quick Results:" & return & return & quickResults with title "Search: " & searchQuery buttons {"Open First", "Full Results", "Done"} default button "Done" with icon note
			
			set buttonPressed to button returned of result
			
			if buttonPressed is "Open First" then
				-- Open the first result's folder
				set firstPath to getFirstResultPath(searchResults)
				if firstPath is not "" then
					tell application "Finder"
						reveal POSIX file firstPath
					end tell
				end if
			else if buttonPressed is "Full Results" then
				-- Show full search interface
				do shell script "osascript " & quoted form of "/Users/user/Github/ai-file-organizer/File_Search_GUI.applescript" & " &"
			end if
		else
			display dialog "❌ No results found for: " & searchQuery with title "AI File Organizer" buttons {"Try Again", "Done"} default button "Try Again"
			if button returned of result is "Try Again" then
				-- Restart the search
				do shell script "osascript " & quoted form of "/Users/user/Github/ai-file-organizer/Quick_Search_Menubar.applescript" & " &"
			end if
		end if
	end if
	
on error errMsg number errNum
	if errNum is not -128 then -- User didn't cancel
		display notification "❌ Search error: " & errMsg with title "AI File Organizer"
	end if
end try

-- Extract quick results (just filenames)
on extractQuickResults(rawResults)
	try
		set resultLines to paragraphs of rawResults
		set quickText to ""
		set resultCount to 0
		
		repeat with currentLine in resultLines
			set lineText to currentLine as string
			
			if lineText starts with "[" and lineText contains "]" and lineText contains "📄" then
				set resultCount to resultCount + 1
				if resultCount ≤ 3 then -- Show only top 3 for quick view
					-- Extract just the filename
					set startPos to (offset of "📄 " in lineText) + 2
					set fileName to text startPos thru end of lineText
					set quickText to quickText & resultCount & ". " & fileName & return
				end if
			end if
		end repeat
		
		if resultCount > 3 then
			set quickText to quickText & "... and " & (resultCount - 3) & " more"
		end if
		
		return quickText
		
	on error
		return ""
	end try
end extractQuickResults

-- Get first result path (reused function)
on getFirstResultPath(rawResults)
	try
		set resultLines to paragraphs of rawResults
		repeat with currentLine in resultLines
			set lineText to currentLine as string
			if lineText contains "📍 Full Path:" then
				return text ((offset of "📍 Full Path: " in lineText) + 14) thru end of lineText
			end if
		end repeat
		return ""
	on error
		return ""
	end try
end getFirstResultPath