#!/usr/bin/env bash
# Claude Harness Workshop — macOS/Linux 설치 스크립트
# 사용법:
#   curl -fsSL https://raw.githubusercontent.com/<USER>/claude-harness-workshop/main/install/install.sh | bash
# 또는 저장소를 클론한 뒤:
#   bash install/install.sh

set -euo pipefail

echo "==== Claude Harness Workshop 설치 ===="

CLAUDE_DIR="$HOME/.claude"
STAMP=$(date +%Y%m%d-%H%M%S)
REPO_URL="https://github.com/imsebeom/claude-harness-workshop.git"
TMP_DIR="/tmp/claude-harness-workshop-$STAMP"

# 1. 기존 ~/.claude 백업
if [ -d "$CLAUDE_DIR" ]; then
  echo "[1/4] 기존 ~/.claude 백업 -> $CLAUDE_DIR.bak.$STAMP"
  mv "$CLAUDE_DIR" "$CLAUDE_DIR.bak.$STAMP"
else
  echo "[1/4] 기존 ~/.claude 없음. 새로 만듭니다."
fi

# 2. 워크숍 저장소 클론
echo "[2/4] 워크숍 저장소 클론 중..."
git clone --depth 1 "$REPO_URL" "$TMP_DIR" >/dev/null 2>&1

# 3. .claude 폴더에 필요한 파일만 복사
echo "[3/4] ~/.claude 구성 중..."
mkdir -p "$CLAUDE_DIR"
cp    "$TMP_DIR/CLAUDE.md"     "$CLAUDE_DIR/"
cp    "$TMP_DIR/settings.json" "$CLAUDE_DIR/"
cp -r "$TMP_DIR/skills"        "$CLAUDE_DIR/"
cp -r "$TMP_DIR/commands"      "$CLAUDE_DIR/"

# 4. 정리
rm -rf "$TMP_DIR"

echo ""
echo "==== 설치 완료 ===="
echo "다음을 확인하세요:"
echo "  1. claude --version"
echo "  2. claude  # 새 세션 시작 후 '안녕' 입력"
echo "  3. /help   # 사용 가능한 커맨드 확인"
echo ""
echo "기존 설정은 '$CLAUDE_DIR.bak.$STAMP' 에 백업되어 있습니다."
