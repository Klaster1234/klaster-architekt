<#
Instaluje Blender i FreeCAD, wgrywa wtyczki MCP, ustawia automatyczny start
serwerow i rejestruje oba konektory w Claude Code.

    powershell -ExecutionPolicy Bypass -File instalacja\instaluj.ps1

Po instalacji Blendera uzywaj skrotu "Blender z MCP.bat", bo serwer w Blenderze
nie startuje sam. FreeCAD startuje serwer sam, bo skrypt ustawia auto_start_rpc.
#>

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot

function Krok($t) { Write-Host "`n== $t" -ForegroundColor Cyan }

Krok "Blender i FreeCAD przez winget"
winget install -e --id BlenderFoundation.Blender --silent --accept-source-agreements --accept-package-agreements
winget install -e --id FreeCAD.FreeCAD          --silent --accept-source-agreements --accept-package-agreements

Krok "Wtyczka do Blendera"
$blender = Get-ChildItem "C:\Program Files\Blender Foundation" -Directory -ErrorAction SilentlyContinue |
           Sort-Object Name -Descending | Select-Object -First 1
if (-not $blender) { throw "nie znalazlem Blendera" }
$wersja  = ($blender.Name -replace "[^\d\.]", "")
$addons  = "$env:APPDATA\Blender Foundation\Blender\$wersja\scripts\addons"
New-Item -ItemType Directory -Force $addons | Out-Null
Invoke-WebRequest "https://raw.githubusercontent.com/ahujasid/blender-mcp/main/addon.py" `
                  -OutFile "$addons\blender_mcp_addon.py"
& "$($blender.FullName)\blender.exe" -b --python-expr @"
import bpy, addon_utils
addon_utils.enable('blender_mcp_addon', default_set=True, persistent=True)
bpy.ops.wm.save_userpref()
"@ | Out-Null

Krok "Wtyczka do FreeCAD"
$mod = "$env:APPDATA\FreeCAD\Mod"
New-Item -ItemType Directory -Force $mod | Out-Null
$tmp = Join-Path $env:TEMP "freecad-mcp"
if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
git clone --depth 1 https://github.com/neka-nat/freecad-mcp $tmp | Out-Null
Copy-Item "$tmp\addon\FreeCADMCP" $mod -Recurse -Force
'{ "remote_enabled": false, "allowed_ips": "127.0.0.1", "auto_start_rpc": true }' |
    Set-Content "$env:APPDATA\FreeCAD\freecad_mcp_settings.json" -Encoding utf8

Krok "Skrot Blendera z serwerem"
@"
@echo off
start "" "$($blender.FullName)\blender-launcher.exe" --python "$repo\instalacja\blender_mcp_start.py" %*
"@ | Set-Content "$repo\Blender z MCP.bat" -Encoding ascii

Krok "Konektory w Claude Code"
claude mcp add blender -s user -- uvx blender-mcp
claude mcp add freecad -s user -- uvx freecad-mcp

Write-Host "`nGotowe. Blender port 9876, FreeCAD port 9875." -ForegroundColor Green
Write-Host "Blendera odpalaj przez 'Blender z MCP.bat'. Sesje Claude Code zrestartuj." -ForegroundColor Green
