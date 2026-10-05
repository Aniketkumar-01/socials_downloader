' Creates a Desktop Shortcut for OmniDownloader on Windows
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strDesktop = WshShell.SpecialFolders("Desktop")
strScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
strTarget = strScriptDir & "\OmniDownloader.vbs"

Set oShellLink = WshShell.CreateShortcut(strDesktop & "\OmniDownloader.lnk")
oShellLink.TargetPath = strTarget
oShellLink.WorkingDirectory = strScriptDir
oShellLink.Description = "Universal Video & Playlist Downloader"
oShellLink.WindowStyle = 7 ' Minimized/Hidden launch

' If an icon exists or use Edge/shell32 icon
If fso.FileExists(strScriptDir & "\assets\app.ico") Then
    oShellLink.IconLocation = strScriptDir & "\assets\app.ico, 0"
Else
    oShellLink.IconLocation = "shell32.dll, 220" ' Native download arrow icon
End If

oShellLink.Save

WScript.Echo "Success! Desktop shortcut created: " & strDesktop & "\OmniDownloader.lnk"
