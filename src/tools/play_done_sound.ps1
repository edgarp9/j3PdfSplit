[CmdletBinding()]
param(
    [string]$Path = "C:\Users\dolco\Music\222.wav"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    throw "Audio file not found: $Path"
}

$extension = [System.IO.Path]::GetExtension($Path)
if ($extension -ne ".wav") {
    throw "Only .wav files are supported: $Path"
}

$resolvedPath = (Resolve-Path -LiteralPath $Path).Path
$player = [System.Media.SoundPlayer]::new($resolvedPath)
$player.Load()
$player.PlaySync()
