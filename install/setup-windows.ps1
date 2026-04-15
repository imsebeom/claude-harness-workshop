# Windows 편의 셋팅 — PATH + 우클릭 메뉴
#
# 이 스크립트는 두 가지를 한다.
#   1. User PATH에 %USERPROFILE%\.local\bin 을 영구 추가한다.
#      → 이후 새 CMD/PowerShell 창에서 'claude' 한 단어로 실행 가능.
#   2. 탐색기 우클릭 메뉴에 "Open Claude Code here" 항목을 등록한다.
#      → 아무 폴더를 우클릭하면 그 폴더에서 바로 Claude Code가 뜬다.
#
# 사용법 (관리자 권한 불필요):
#   powershell -ExecutionPolicy Bypass -File .\install\setup-windows.ps1
#
# 기존 Claude Code 세션 안에서 부탁하는 방법:
#   "setup-windows.ps1을 실행해 줘"
#   (클로드가 알아서 PowerShell로 호출해 준다)

$ErrorActionPreference = "Stop"

$ClaudeExe = Join-Path $env:USERPROFILE ".local\bin\claude.exe"
$ClaudeBin = Split-Path $ClaudeExe

Write-Host "==== Claude Code Windows 편의 셋팅 ====" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $ClaudeExe)) {
    Write-Host "❌ claude.exe를 찾을 수 없습니다: $ClaudeExe" -ForegroundColor Red
    Write-Host "   먼저 https://code.claude.com 의 Windows 인스톨러를 실행했는지 확인하세요." -ForegroundColor Yellow
    exit 1
}

Write-Host "claude.exe 위치: $ClaudeExe" -ForegroundColor Gray
Write-Host ""

# ──────────────────────────────────────────────────────────────────────
# 1. PATH에 ~/.local/bin 추가 (User scope, 영구)
# ──────────────────────────────────────────────────────────────────────
Write-Host "[1/2] PATH 업데이트..." -ForegroundColor Yellow

$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ([string]::IsNullOrEmpty($currentPath)) {
    $currentPath = ""
}

if ($currentPath -like "*$ClaudeBin*") {
    Write-Host "     이미 추가되어 있음" -ForegroundColor Gray
} else {
    $newPath = if ($currentPath) { "$currentPath;$ClaudeBin" } else { $ClaudeBin }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "     ✓ User PATH에 $ClaudeBin 추가" -ForegroundColor Green
    Write-Host "     (새 CMD/PowerShell 창을 열어야 반영됨)" -ForegroundColor Gray
}

Write-Host ""

# ──────────────────────────────────────────────────────────────────────
# 2. 우클릭 컨텍스트 메뉴 등록
# ──────────────────────────────────────────────────────────────────────
Write-Host "[2/2] 우클릭 메뉴 'Open Claude Code here' 등록..." -ForegroundColor Yellow

function Register-ClaudeContext {
    param(
        [string]$BaseKey,
        [string]$PathToken  # %1 (폴더 아이콘) 또는 %V (폴더 빈 공간)
    )
    $key = "HKCU:\Software\Classes\$BaseKey\shell\ClaudeCode"
    $cmdKey = "$key\command"

    New-Item -Path $key -Force | Out-Null
    Set-ItemProperty -Path $key -Name "(Default)" -Value "Open Claude Code here"
    Set-ItemProperty -Path $key -Name "Icon" -Value $ClaudeExe

    New-Item -Path $cmdKey -Force | Out-Null
    $cmdValue = 'cmd.exe /k "cd /d "' + $PathToken + '" && "' + $ClaudeExe + '""'
    Set-ItemProperty -Path $cmdKey -Name "(Default)" -Value $cmdValue
}

# 폴더 아이콘 우클릭 (%1 = 해당 폴더 경로)
Register-ClaudeContext -BaseKey "Directory" -PathToken "%1"
Write-Host "     ✓ 폴더 아이콘 우클릭 메뉴 등록" -ForegroundColor Green

# 폴더 빈 공간 우클릭 (%V = 현재 보고 있는 폴더)
Register-ClaudeContext -BaseKey "Directory\Background" -PathToken "%V"
Write-Host "     ✓ 폴더 내부 빈 공간 우클릭 메뉴 등록" -ForegroundColor Green

Write-Host ""
Write-Host "==== 완료 ====" -ForegroundColor Cyan
Write-Host ""
Write-Host "다음 단계:" -ForegroundColor Cyan
Write-Host "  1. 모든 CMD/PowerShell 창을 닫고 새로 연다 (PATH 갱신용)"
Write-Host "  2. 새 CMD 창에서 'claude'를 쳐서 실행되는지 확인"
Write-Host "  3. 파일 탐색기에서 아무 폴더나 우클릭 → 'Open Claude Code here'"
Write-Host ""

# ──────────────────────────────────────────────────────────────────────
# 우클릭 메뉴를 제거하고 싶을 때 참고용 주석
# ──────────────────────────────────────────────────────────────────────
# Remove-Item -Path "HKCU:\Software\Classes\Directory\shell\ClaudeCode" -Recurse
# Remove-Item -Path "HKCU:\Software\Classes\Directory\Background\shell\ClaudeCode" -Recurse
