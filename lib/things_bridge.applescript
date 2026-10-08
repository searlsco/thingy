on replaceText(findText, replacementText, sourceText)
	set oldDelimiters to AppleScript's text item delimiters
	set AppleScript's text item delimiters to findText
	set sourceItems to text items of sourceText
	set AppleScript's text item delimiters to replacementText
	set joinedText to sourceItems as text
	set AppleScript's text item delimiters to oldDelimiters
	return joinedText
end replaceText

on jsonString(aValue)
	if aValue is missing value then return "null"
	set escapedText to aValue as text
	set escapedText to my replaceText("\\", "\\\\", escapedText)
	set escapedText to my replaceText(quote, "\\\"", escapedText)
	set escapedText to my replaceText(return, "\\n", escapedText)
	set escapedText to my replaceText(linefeed, "\\n", escapedText)
	set escapedText to my replaceText(tab, "\\t", escapedText)
	set hexDigits to "0123456789abcdef"
	repeat with controlCode from 0 to 31
		if controlCode is not 9 and controlCode is not 10 and controlCode is not 13 then
			set hexByte to character ((controlCode div 16) + 1) of hexDigits & character ((controlCode mod 16) + 1) of hexDigits
			set escapedText to my replaceText(character id controlCode, "\\u00" & hexByte, escapedText)
		end if
	end repeat
	return quote & escapedText & quote
end jsonString

on pad2(aNumber)
	set numberText to aNumber as integer as text
	if (count numberText) is 1 then return "0" & numberText
	return numberText
end pad2

on dateOnly(aDate)
	if aDate is missing value then return "null"
	set yearText to year of aDate as integer as text
	set monthText to my pad2(month of aDate as integer)
	set dayText to my pad2(day of aDate as integer)
	return my jsonString(yearText & "-" & monthText & "-" & dayText)
end dateOnly

on parseIsoDate(dateText)
	if (count dateText) is not 10 then error "date must be YYYY-MM-DD: " & dateText
	set oldDelimiters to AppleScript's text item delimiters
	set AppleScript's text item delimiters to "-"
	set dateParts to text items of dateText
	set AppleScript's text item delimiters to oldDelimiters
	if (count dateParts) is not 3 then error "date must be YYYY-MM-DD: " & dateText

	set parsedDate to current date
	set day of parsedDate to 1
	set year of parsedDate to item 1 of dateParts as integer
	set month of parsedDate to item 2 of dateParts as integer
	set day of parsedDate to item 3 of dateParts as integer
	set time of parsedDate to 0
	if (my dateOnly(parsedDate)) is not (my jsonString(dateText)) then error "invalid date: " & dateText
	return parsedDate
end parseIsoDate

on bucketFor(taskId)
	tell application "Things3"
		repeat with listName in {"Inbox", "Today", "Upcoming", "Someday", "Anytime"}
			-- Filter in Things instead of serializing every id in a large list.
			set matches to count of (to dos of list (listName as text) whose id is taskId)
			if matches is greater than 0 then return listName as text
		end repeat
	end tell
	return ""
end bucketFor

on taskJson(taskRef, taskBucket)
	tell application "Things3"
		set taskId to id of taskRef
		set taskStatus to status of taskRef as text
		set taskName to name of taskRef
		set taskNotes to notes of taskRef
		set taskTags to tag names of taskRef
		set taskDueDate to due date of taskRef
		set taskActivationDate to activation date of taskRef

		set projectJson to "null"
		try
			set taskProject to project of taskRef
			if taskProject is not missing value then set projectJson to "{\"id\":" & my jsonString(id of taskProject) & ",\"name\":" & my jsonString(name of taskProject) & "}"
		end try

		set areaJson to "null"
		try
			set taskArea to area of taskRef
			if taskArea is not missing value then set areaJson to "{\"id\":" & my jsonString(id of taskArea) & ",\"name\":" & my jsonString(name of taskArea) & "}"
		end try
	end tell

	if taskBucket is "" then set taskBucket to my bucketFor(taskId)
	return "{\"id\":" & my jsonString(taskId) & ¬
		",\"status\":" & my jsonString(taskStatus) & ¬
		",\"title\":" & my jsonString(taskName) & ¬
		",\"notes\":" & my jsonString(taskNotes) & ¬
		",\"tags\":" & my jsonString(taskTags) & ¬
		",\"project\":" & projectJson & ¬
		",\"area\":" & areaJson & ¬
		",\"bucket\":" & my jsonString(taskBucket) & ¬
		",\"activationDate\":" & my dateOnly(taskActivationDate) & ¬
		",\"deadline\":" & my dateOnly(taskDueDate) & "}"
end taskJson

on listJson(listName)
	set resultJson to "["
	set needsComma to false
	tell application "Things3"
		set listTasks to to dos of list listName whose status is open
	end tell
	repeat with taskRef in listTasks
		if needsComma then set resultJson to resultJson & ","
		set resultJson to resultJson & my taskJson(taskRef, listName)
		set needsComma to true
	end repeat
	return resultJson & "]"
end listJson

on searchJson(queryText)
	if queryText is "" then error "search query must not be empty"
	tell application "Things3"
		ignoring case
			set matchedTasks to every to do whose status is open and (name contains queryText or notes contains queryText)
		end ignoring
	end tell
	set resultJson to "["
	set needsComma to false
	repeat with taskRef in matchedTasks
		if needsComma then set resultJson to resultJson & ","
		set resultJson to resultJson & my taskJson(taskRef, "")
		set needsComma to true
	end repeat
	return resultJson & "]"
end searchJson

on containersJson()
	-- Fetch unfiltered properties once. Repeating a whose filter makes Things
	-- repeatedly resolve project objects; filter the returned statuses locally.
	tell application "Things3"
		set areaIds to id of every area
		set areaNames to name of every area
		set projectIds to id of every project
		set projectNames to name of every project
		set projectStatuses to status of every project
	end tell

	set resultJson to "{\"areas\":["
	repeat with areaIndex from 1 to count areaIds
		if areaIndex is greater than 1 then set resultJson to resultJson & ","
		set resultJson to resultJson & "{\"id\":" & my jsonString(item areaIndex of areaIds) & ",\"name\":" & my jsonString(item areaIndex of areaNames) & "}"
	end repeat

	set resultJson to resultJson & "],\"projects\":["
	set needsComma to false
	repeat with projectIndex from 1 to count projectIds
		if (item projectIndex of projectStatuses as text) is "open" then
			set parentAreaJson to "null"
			-- Bulk area getters omit missing parents, so resolve each by its exact id.
			tell application "Things3"
				set parentArea to area of project id (item projectIndex of projectIds)
				if parentArea is not missing value then
					set parentId to id of parentArea
				else
					set parentId to missing value
				end if
			end tell
			if parentId is not missing value then
				repeat with areaIndex from 1 to count areaIds
					if item areaIndex of areaIds is parentId then
						set parentAreaJson to "{\"id\":" & my jsonString(parentId) & ",\"name\":" & my jsonString(item areaIndex of areaNames) & "}"
						exit repeat
					end if
				end repeat
			end if
			if needsComma then set resultJson to resultJson & ","
			set resultJson to resultJson & "{\"id\":" & my jsonString(item projectIndex of projectIds) & ",\"name\":" & my jsonString(item projectIndex of projectNames) & ",\"area\":" & parentAreaJson & "}"
			set needsComma to true
		end if
	end repeat
	return resultJson & "]}"
end containersJson

on showJson(taskId)
	tell application "Things3"
		set taskRef to to do id taskId
	end tell
	return my taskJson(taskRef, "")
end showJson

-- Resolve destinations and dates before any mutation, including insertion.
on validateChange(destinationKind, destinationId, whenValue, deadlineValue)
	set destinationRef to missing value
	tell application "Things3"
		if destinationKind is "project" then
			set destinationRef to project id destinationId
			get id of destinationRef
		else if destinationKind is "area" then
			set destinationRef to area id destinationId
			get id of destinationRef
		else if destinationKind is not "standalone" then
			error "destination kind must be project, area, or standalone"
		end if
	end tell
	set scheduledDate to missing value
	if whenValue is "today" then
		set scheduledDate to current date
	else if whenValue is not "inbox" and whenValue is not "anytime" and whenValue is not "someday" then
		set scheduledDate to my parseIsoDate(whenValue)
	end if
	set deadlineDate to missing value
	if deadlineValue is not "" and deadlineValue is not "none" then set deadlineDate to my parseIsoDate(deadlineValue)
	return {destinationRef, scheduledDate, deadlineDate}
end validateChange

on applyChange(taskId, destinationKind, destinationId, whenValue, deadlineValue)
	set validated to my validateChange(destinationKind, destinationId, whenValue, deadlineValue)
	tell application "Things3"
		set taskRef to to do id taskId

		if destinationKind is "project" then
			set project of taskRef to item 1 of validated
		else if destinationKind is "area" then
			set area of taskRef to item 1 of validated
		else if destinationKind is "standalone" then
			try
				delete project of taskRef
			end try
			try
				delete area of taskRef
			end try
		else
			error "destination kind must be project, area, or standalone"
		end if

		if whenValue is "today" then
			schedule taskRef for item 2 of validated
		else if whenValue is "inbox" then
			move taskRef to list "Inbox"
		else if whenValue is "anytime" then
			move taskRef to list "Anytime"
		else if whenValue is "someday" then
			move taskRef to list "Someday"
		else
			schedule taskRef for item 2 of validated
		end if

		if deadlineValue is "none" then
			set due date of taskRef to ""
		else if deadlineValue is not "" then
			set due date of taskRef to item 3 of validated
		end if
	end tell

	delay 0.2
	return my showJson(taskId)
end applyChange

on completeTask(taskId)
	tell application "Things3"
		set status of to do id taskId to completed
	end tell
	return my showJson(taskId)
end completeTask

on appendNotes(taskId, addition)
	tell application "Things3"
		set taskRef to to do id taskId
		set existingNotes to notes of taskRef
		if existingNotes is "" then
			set notes of taskRef to addition
		else
			set notes of taskRef to existingNotes & linefeed & linefeed & addition
		end if
	end tell
	return my showJson(taskId)
end appendNotes

-- Capture the inserted object's id before notes and scheduling trigger UI work.
-- Set notes after insertion so creation can return its id first.
on createEmptyTask(taskTitle)
	tell application "Things3"
		set taskRef to make new to do with properties {name:taskTitle}
		return "{\"id\":" & my jsonString(id of taskRef) & "}"
	end tell
end createEmptyTask

on configureCreatedTask(taskId, taskNotes, destinationKind, destinationId, whenValue)
	set validated to my validateChange(destinationKind, destinationId, whenValue, "")
	tell application "Things3"
		set taskRef to to do id taskId
		set notes of taskRef to taskNotes
		if destinationKind is "project" then
			set project of taskRef to item 1 of validated
		else if destinationKind is "area" then
			set area of taskRef to item 1 of validated
		else if destinationKind is not "standalone" then
			error "destination kind must be project, area, or standalone"
		end if
		if whenValue is "today" then
			schedule taskRef for item 2 of validated
		else if whenValue is "inbox" then
			move taskRef to list "Inbox"
		else if whenValue is "anytime" then
			move taskRef to list "Anytime"
		else if whenValue is "someday" then
			move taskRef to list "Someday"
		else
			schedule taskRef for item 2 of validated
		end if
	end tell
	return "{\"id\":" & my jsonString(taskId) & "}"
end configureCreatedTask

on createTask(taskTitle, taskNotes, destinationKind, destinationId, whenValue)
	my validateChange(destinationKind, destinationId, whenValue, "")
	tell application "Things3"
		set taskRef to make new to do with properties {name:taskTitle}
		set newId to id of taskRef
	end tell
	my configureCreatedTask(newId, taskNotes, destinationKind, destinationId, whenValue)
	return my showJson(newId)
end createTask

on createProject(projectTitle, projectNotes, areaId)
	set parentRef to missing value
	tell application "Things3"
		if areaId is not "" then
			set parentRef to area id areaId
			get id of parentRef
		end if
		set projectRef to make new project with properties {name:projectTitle, notes:projectNotes}
		if areaId is not "" then set area of projectRef to parentRef
		return "{\"id\":" & my jsonString(id of projectRef) & ",\"name\":" & my jsonString(name of projectRef) & "}"
	end tell
end createProject

on cancelTask(taskId)
	tell application "Things3"
		set status of to do id taskId to canceled
	end tell
	return my showJson(taskId)
end cancelTask

on run argv
	if (count argv) is 0 then error "usage: thingy inbox|today|search|containers|show|apply|complete|append-notes|create|create-empty|configure-created|create-project|cancel"
	set commandName to item 1 of argv
	if commandName is "inbox" then
		return my listJson("Inbox")
	else if commandName is "today" then
		return my listJson("Today")
	else if commandName is "search" then
		if (count argv) is not 2 then error "usage: search QUERY"
		return my searchJson(item 2 of argv)
	else if commandName is "containers" then
		return my containersJson()
	else if commandName is "show" then
		if (count argv) is not 2 then error "usage: show ITEM_ID"
		return my showJson(item 2 of argv)
	else if commandName is "apply" then
		if (count argv) is not 6 then error "usage: apply ITEM_ID DESTINATION_KIND DESTINATION_ID WHEN DEADLINE"
		return my applyChange(item 2 of argv, item 3 of argv, item 4 of argv, item 5 of argv, item 6 of argv)
	else if commandName is "complete" then
		if (count argv) is not 2 then error "usage: complete ITEM_ID"
		return my completeTask(item 2 of argv)
	else if commandName is "append-notes" then
		if (count argv) is not 3 then error "usage: append-notes ITEM_ID TEXT"
		return my appendNotes(item 2 of argv, item 3 of argv)
	else if commandName is "create-empty" then
		if (count argv) is not 2 then error "usage: create-empty TITLE"
		return my createEmptyTask(item 2 of argv)
	else if commandName is "configure-created" then
		if (count argv) is not 6 then error "usage: configure-created ITEM_ID NOTES DESTINATION_KIND DESTINATION_ID WHEN"
		return my configureCreatedTask(item 2 of argv, item 3 of argv, item 4 of argv, item 5 of argv, item 6 of argv)
	else if commandName is "create" then
		if (count argv) is not 6 then error "usage: create TITLE NOTES DESTINATION_KIND DESTINATION_ID WHEN"
		return my createTask(item 2 of argv, item 3 of argv, item 4 of argv, item 5 of argv, item 6 of argv)
	else if commandName is "create-project" then
		if (count argv) is not 4 then error "usage: create-project TITLE NOTES AREA_ID"
		return my createProject(item 2 of argv, item 3 of argv, item 4 of argv)
	else if commandName is "cancel" then
		if (count argv) is not 2 then error "usage: cancel ITEM_ID"
		return my cancelTask(item 2 of argv)
	else
		error "unknown command: " & commandName
	end if
end run
