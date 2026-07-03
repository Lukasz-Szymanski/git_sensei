# VHS Tape file for generating git-sensei demo GIF.
# Run with: vhs demo.tape
Output docs/demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 1200
Set Height 600
Set Theme "Dracula"

Type "git status"
Sleep 500ms
Enter
Sleep 1s

Type "sensei commit --split"
Sleep 500ms
Enter
Sleep 3s

# Confirm split
Type "y"
Sleep 500ms
Enter
Sleep 2s

# Approve first commit
Type "y"
Sleep 500ms
Enter
Sleep 2s

# Approve second commit
Type "y"
Sleep 500ms
Enter
Sleep 2s

Type "sensei stats"
Sleep 500ms
Enter
Sleep 2s
