# Claude Harness Workshop — Windows 설치 스크립트
# 사용법:
#   irm https://raw.githubusercontent.com/<USER>/claude-harness-workshop/main/install/install.ps1 | iex
# 또는 저장소를 클론한 뒤:
#   .\install\install.ps1

$ErrorActionPreference = "Stop"

Write-Host "==== Claude Harness Workshop 설치 ====" -ForegroundColor Cyan

$ClaudeDir = Join-Path $env:USERPROFILE ".claude"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RepoUrl = "https://github.com/CHANGEME/claude-harness-workshop.git"
$TempDir = Join-Path $env:TEMP "claude-harness-workshop-$Stamp"

# 1. 기존 ~/.claude 백업
if (Test-Path $ClaudeDir) {
    $Backup = "$ClaudeDir.bak.$Stamp"
    Write-Host "[1/4] 기존 ~/.claude 백업 -> $Backup" -ForegroundColor Yellow
    Rename-Item -Path $ClaudeDir -NewName (Split-Path $Backup -Leaf)
} else {
    Write-Host "[1/4] 기존 ~/.claude 없음. 새로 만듭니다." -ForegroundColor Yellow
}

# 2. 워크숍 저장소 클론
Write-Host "[2/4] 워크숍 저장소 클론 중..." -ForegroundColor Yellow
git clone --depth 1 $RepoUrl $TempDir | Out-Null

# 3. .claude 폴더에 필요한 파일만 복사
Write-Host "[3/4] ~/.claude 구성 중..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $ClaudeDir | Out-Null
Copy-Item -Path (Join-Path $TempDir "CLAUDE.md")     -Destination $ClaudeDir -Force
Copy-Item -Path (Join-Path $TempDir "settings.json") -Destination $ClaudeDir -Force
Copy-Item -Path (Join-Path $TempDir "skills")        -Destination $ClaudeDir -Recurse -Force
Copy-Item -Path (Join-Path $TempDir "commands")      -Destination $ClaudeDir -Recurse -Force

# 4. 정리
Remove-Item -Recurse -Force $TempDir

Write-Host ""
Write-Host "==== 설치 완료 ====" -ForegroundColor Green
Write-Host "다음을 확인하세요:" -ForegroundColor Cyan
Write-Host "  1. claude --version"
Write-Host "  2. claude  # 새 세션 시작 후 '안녕' 입력"
Write-Host "  3. /help   # 사용 가능한 커맨드 확인"
Write-Host ""
Write-Host "기존 설정은 '$ClaudeDir.bak.$Stamp' 에 백업되어 있습니다." -ForegroundColor Gray
