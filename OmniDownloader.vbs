' OmniDownloader - Silent Windows Desktop App Launcher
' Launches the desktop application without any black console command prompt window.
Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objShell = CreateObject("WScript.Shell")

strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
strBatPath = strScriptDir & "\OmniDownloader.bat"

' Run OmniDownloader.bat with window style 0 (completely hidden console)
objShell.Run """" & strBatPath & """", 0, False
