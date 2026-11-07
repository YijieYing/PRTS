on run argv
	-- argv: subject, plain-text file, recipient, html file
	set subj to item 1 of argv
	set bodyText to read (POSIX file (item 2 of argv)) as «class utf8»
	set rcpt to item 3 of argv
	set htmlText to read (POSIX file (item 4 of argv)) as «class utf8»
	tell application "Mail"
		set m to make new outgoing message with properties {subject:subj, content:bodyText, visible:false}
		set html content of m to htmlText
		tell m to make new to recipient at end of to recipients with properties {address:rcpt}
		send m
	end tell
end run
