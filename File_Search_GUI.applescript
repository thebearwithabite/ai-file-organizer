-- AI File Organizer - GUI Search Interface
-- User Thomson's File Search Tool

-- Configuration
set pythonPath to "/Users/user/py312_env/bin/python"
set librarianPath to "/Users/user/Github/ai-file-organizer/librarian.py"

-- Main execution
try
		-- Show search dialog
		set searchQuery to text returned of (display dialog "🔍 AI File Search" with title "File Organizer" default answer "" buttons {"Cancel", "Search"} default button "Search" with icon note)
		
		if searchQuery is not "" then
			-- Show progress
			display notification "Searching your files..." with title "AI File Organizer"
			
			-- Run the search
			set searchCommand to pythonPath & " " & quoted form of librarianPath & " search " & quoted form of searchQuery & " --limit 10"
			set searchResults to do shell script searchCommand
			
			-- Parse and format results
			set formattedResults to formatSearchResults(searchResults)
			
			-- Show results in a nice dialog
			display dialog formattedResults with title "Search Results: " & searchQuery buttons {"New Search", "Open Folder", "Done"} default button "Done" with icon note giving up after 30
			
			set buttonPressed to button returned of result
			
			-- Handle button actions
			if buttonPressed is "New Search" then
				run
			else if buttonPressed is "Open Folder" then
				-- Get the first result path and open its folder
				set firstResultPath to getFirstResultPath(searchResults)
				if firstResultPath is not "" then
					tell application "Finder"
						reveal POSIX file firstResultPath
					end tell
				end if
			end if
		end if
		
on error errMsg number errNum
	if errNum is not -128 then -- User didn't cancel
		display dialog "❌ Error: " & errMsg with title "Search Error" buttons {"OK"} default button "OK" with icon stop
	end if
end try

-- Format search results for display
on formatSearchResults(rawResults)
	try
		set resultLines to paragraphs of rawResults
		set formattedText to ""
		set resultCount to 0
		set isInResults to false
		
		repeat with currentLine in resultLines
			set lineText to currentLine as string
			
			-- Check if we're in the results section
			if lineText contains "Found" and lineText contains "results:" then
				set isInResults to true
				set formattedText to formattedText & lineText & return & return
			else if isInResults then
				-- Format individual results
				if lineText starts with "[" and lineText contains "]" then
					set resultCount to resultCount + 1
					if resultCount ≤ 5 then -- Limit to 5 results for readability
						set formattedText to formattedText & lineText & return
					end if
				else if lineText contains "📂" or lineText contains "📊" or lineText contains "📅" then
					if resultCount ≤ 5 then
						set formattedText to formattedText & "    " & lineText & return
					end if
				else if lineText contains "🔍 Match:" then
					if resultCount ≤ 5 then
						-- Truncate long match text
						set matchText to lineText
						if length of matchText > 80 then
							set matchText to (characters 1 thru 77 of matchText as string) & "..."
						end if
						set formattedText to formattedText & "    " & matchText & return & return
					end if
				end if
			end if
		end repeat
		
		if resultCount > 5 then
			set formattedText to formattedText & return & "... and " & (resultCount - 5) & " more results" & return
		end if
		
		if formattedText is "" then
			return "❌ No results found. Try different keywords."
		else
			return formattedText
		end if
		
	on error
		return "⚠️ Could not format results properly." & return & return & rawResults
	end try
end formatSearchResults

-- Extract first result path for opening
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

-- Alternative: Quick search from clipboard
on quickSearch()
	try
		set clipboardText to the clipboard as string
		if clipboardText is not "" then
			set searchCommand to pythonPath & " " & quoted form of librarianPath & " search " & quoted form of clipboardText & " --limit 5"
			set searchResults to do shell script searchCommand
			display notification searchResults with title "Quick Search: " & clipboardText
		end if
	on error
		display notification "❌ Could not search clipboard text" with title "AI File Organizer"
	end try
end quickSearch