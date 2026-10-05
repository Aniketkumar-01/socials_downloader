# Quick alias to publish_release.ps1
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$ScriptDir\publish_release.ps1"
