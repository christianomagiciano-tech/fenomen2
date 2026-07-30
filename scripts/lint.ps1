$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
ruff check backend
