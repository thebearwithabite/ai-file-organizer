-- Enhanced AI File Organizer - GUI Search with Semantic Capabilities
-- User Thomson's Enhanced File Search Tool

-- Configuration
set pythonPath to "/Users/user/py312_env/bin/python"
set librarianPath to "/Users/user/Github/ai-file-organizer/enhanced_librarian.py"

-- Main search dialog with mode selection
try
	-- Show enhanced search dialog with mode options
	set searchQuery to text returned of (display dialog "🧠 Enhanced AI File Search" with title "Enhanced File Organizer" default answer "" buttons {"Cancel", "Search"} default button "Search" with icon note)
	
	if searchQuery is not "" then
		-- Ask for search mode
		set searchMode to button returned of (display dialog "Choose search mode for: " & searchQuery with title "Search Mode" buttons {"Fast", "Semantic", "Auto"} default button "Auto" with icon note)
		
		-- Convert button to mode parameter
		if searchMode is "Fast" then
			set modeParam to "fast"
		else if searchMode is "Semantic" then
			set modeParam to "semantic"
		else
			set modeParam to "auto"
		end if
		
		-- Show progress with mode info
		display notification ("Searching with " & searchMode & " mode...") with title "Enhanced AI Search"
		
		-- Run the enhanced search
		set searchCommand to pythonPath & " " & quoted form of librarianPath & " search " & quoted form of searchQuery & " --mode " & modeParam & " --limit 10"
		set searchResults to do shell script searchCommand
		
		-- Parse and format results
		set formattedResults to formatEnhancedResults(searchResults)
		
		-- Show results with enhanced info
		display dialog formattedResults with title ("Enhanced Results: " & searchQuery) buttons {"Index More", "New Search", "Done"} default button "Done" with icon note giving up after 45
		
		set buttonPressed to button returned of result
		
		-- Handle button actions
		if buttonPressed is "New Search" then
			-- Restart search
			do shell script "osascript " & quoted form of "/Users/user/Github/ai-file-organizer/Enhanced_Search_GUI.applescript" & " &"
		else if buttonPressed is "Index More" then
			-- Run semantic indexing
			display notification "Indexing files for better semantic search..." with title "Enhanced AI Search"
			set indexCommand to pythonPath & " " & quoted form of librarianPath & " index"
			try
				do shell script indexCommand
				display notification "✅ Indexing complete! Try searching again." with title "Enhanced AI Search"
			on error
				display notification "⚠️ Indexing failed. Check system." with title "Enhanced AI Search"
			end try
		end if
	end if
	
on error errMsg number errNum
	if errNum is not -128 then -- User didn't cancel
		display dialog "❌ Enhanced Search Error: " & errMsg with title "Search Error" buttons {"OK"} default button "OK" with icon stop
	end if
end try

-- Format enhanced search results for display
on formatEnhancedResults(rawResults)
	try
		set resultLines to paragraphs of rawResults
		set formattedText to ""
		set resultCount to 0
		set isInResults to false
		set semanticMode to false
		
		-- Check if semantic search was used
		repeat with currentLine in resultLines
			set lineText to currentLine as string
			if lineText contains "🧠 Semantic:" then
				set semanticMode to true
				exit repeat
			end if
		end repeat
		
		repeat with currentLine in resultLines
			set lineText to currentLine as string
			
			-- Check if we're in the results section
			if lineText contains "Found" and lineText contains "results:" then
				set isInResults to true
				set formattedText to formattedText & lineText & return & return
			else if isInResults then
				-- Format individual results with enhanced info
				if lineText starts with "[" and lineText contains "]" then
					set resultCount to resultCount + 1
					if resultCount ≤ 5 then -- Limit to 5 results for readability
						set formattedText to formattedText & lineText & return
					end if
				else if lineText contains "📊" or lineText contains "🧠" or lineText contains "🏷️" or lineText contains "📅" then
					if resultCount ≤ 5 then
						set formattedText to formattedText & "    " & lineText & return
					end if
				else if lineText contains "📝 Summary:" then
					if resultCount ≤ 5 then
						-- Show summary for semantic results
						set formattedText to formattedText & "    " & lineText & return
					end if
				else if lineText contains "🔍 Match:" then
					if resultCount ≤ 5 then
						-- Truncate long match text
						set matchText to lineText
						if length of matchText > 100 then
							set matchText to (characters 1 thru 97 of matchText as string) & "..."
						end if
						set formattedText to formattedText & "    " & matchText & return & return
					end if
				end if
			end if
		end repeat
		
		if resultCount > 5 then
			set formattedText to formattedText & return & "... and " & (resultCount - 5) & " more results" & return
		end if
		
		-- Add semantic search info
		if semanticMode then
			set formattedText to formattedText & return & "🧠 Semantic search used - AI understood content meaning!"
		end if
		
		if formattedText is "" then
			return "❌ No results found." & return & return & "💡 Try:" & return & "• Different keywords" & return & "• Semantic mode for content understanding" & return & "• Index more files first"
		else
			return formattedText
		end if
		
	on error
		return "⚠️ Could not format results properly." & return & return & rawResults
	end try
end formatEnhancedResults