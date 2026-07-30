$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
pytest @args
