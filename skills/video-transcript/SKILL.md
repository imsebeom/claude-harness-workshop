---
name: video-transcript
description: "영상 파일 또는 YouTube URL에서 음성을 추출하여 마크다운 파일을 생성하는 스킬. /video-transcript [경로 또는 URL] 형식으로 호출. 사용 시점 - (1) 강의/회의 영상을 텍스트로 변환할 때, (2) YouTube 영상 내용을 문서화할 때, (3) 영상 콘텐츠를 마크다운 검색 가능하게 만들 때, (4) 팟캐스트나 오디오 파일을 텍스트로 변환할 때."
---

# /video-transcript - 영상→텍스트 변환 워크플로우

입력 유형에 따라 두 경로로 분기한다.

- **YouTube URL** → yt-dlp 자막 기반 `video_to_md.py` (자막이 있으면 즉시 정제된 MD 생성, Whisper/STT 불필요)
- **로컬 영상·오디오 파일** → `gemini -p` 헤드리스 전사 (로컬 Whisper/OpenAI API 사용 안 함)

## Step 1: 입력 확인

사용자가 제공한 입력을 확인한다.

- **로컬 파일**: mp4, mkv, avi, mov, webm, mp3, wav, m4a, ogg, flac, wma 등
- **URL**: YouTube 등 yt-dlp 지원 URL

입력이 없으면 사용자에게 경로 또는 URL을 요청한다.

## Step 2: YouTube URL 분기 — yt-dlp 자막

YouTube 계열 URL이면 `/md` 스킬의 Step 3-Y와 동일하게 처리한다.

```bash
python "~/.claude/skills/video-transcript/scripts/video_to_md.py" "<URL>" \
  -o "<출력.md>" \
  -l ko
```

옵션:
- `-l ko`: 자막 언어 고정 (미지정 시 ko → en → ja 순 탐색)
- `--no-llm`: LLM 구조화 생략, 정제 평문만 저장

자막이 없는 영상은 스크립트가 exit code 2로 실패한다. 이 경우 Step 3로 폴백한다(yt-dlp로 오디오 추출 후 gemini -p).

## Step 3: 로컬 파일 / 자막 없는 영상 — gemini -p 전사

파일을 MP3/WAV 등 오디오 포맷으로 준비한 뒤 `markitdown_to_md.py`의 오디오 경로로 넘긴다. 이 경로는 내부적으로 `gemini -p "@파일 전사해줘"` 헤드리스 호출을 수행한다.

### ⚠️ Gemini CLI 인라인 크기 제한 (~20MB)

Gemini CLI의 `@파일` 참조는 약 20MB의 인라인 크기 제한이 있다. 이를 넘기면 Gemini가 전사 대신 "파일 읽기 제한 크기를 초과…분할하거나 압축하여…" 같은 **거부 메시지**를 돌려주는데, 스크립트가 이를 구분 못 하면 그 거부 메시지를 그대로 MD로 저장해 버린다.

`markitdown_to_md.py`는 이 상황을 두 겹으로 방어한다:

1. **사전 재인코딩**: 오디오가 19MB를 넘으면 ffmpeg로 mono 24kbps AAC m4a로 임시 재인코딩 후 Gemini에 넘긴다(30분 음성 기준 ~5MB).
2. **거부 감지**: 전사 결과에 refusal 패턴(`파일 읽기 제한`, `분할하거나 압축`, `20MB` 등)이 섞여 있으면 전사 실패로 간주하고 MD를 저장하지 않는다.

따라서 일반적으로는 원본을 그대로 넘겨도 된다. ffmpeg가 설치돼 있지 않거나 사전 재인코딩에 실패하면 경고 후 원본으로 시도하되, 실패 시 MD가 저장되지 않고 종료된다.

오디오 추출이 필요한 경우 (mp4 → mp3):
```bash
yt-dlp -x --audio-format mp3 -o "%(title)s.%(ext)s" "<URL>"
# 또는 로컬 영상:
ffmpeg -i "강의.mp4" -vn -acodec libmp3lame "강의.mp3"
```

오디오 → 마크다운:
```bash
python "~/.claude/skills/md/scripts/markitdown_to_md.py" "강의.mp3" \
  -o "<출력 디렉토리>" \
  --language ko
```

옵션:
- `--language ko`: 전사 언어 (기본 ko)
- `--gemini-model <name>`: Gemini 모델 오버라이드 (기본: CLI 기본값)

## Step 4: 결과 확인

1. stdout에 출력된 파일 경로 확인. 전사 실패 시 MD는 저장되지 않으며 스크립트의 "변환 성공: 0/1개" 줄로 확인 가능.
2. 생성된 마크다운을 Read로 열어 샘플 미리보기. 본문 첫 몇 줄에 refusal 패턴이 보이면 실패. (스크립트가 감지 못한 경계 케이스일 수 있으니 즉시 삭제·재시도 판단)
3. 필요 시 길이·언어 정보 보고.

### ⚠️ 모니터링 주의: 동명 MD 선존재 가능

출력 디렉토리에 **이미 `<오디오파일명>.md` 파일이 있을 수 있다** — 과거 실행 결과, 수동 작성, 또는 이전 실패(거부 감지 전 구버전)의 잔존일 수 있다. 스크립트는 매번 덮어쓰지만, 진행 중 상태를 "md 파일 존재 여부"로 판정하면 이미 있는 파일을 보고 "완료됐다"고 오판할 수 있다.

모니터링/완료 판정 원칙:
- **파일 존재만으로 완료를 단정하지 말 것.**
- 실행 전 기존 출력 파일의 mtime을 기록하거나, 일단 삭제·이동해두고 실행 → 실행 후 새 mtime 파일이 생겼는지로 확인.
- 가장 확실한 건 스크립트 **exit code + 마지막 stdout 줄**("변환 성공: N/M개")을 읽는 것. Monitor 루프를 쓸 땐 이 로그를 파싱해야지 존재 여부만 보면 안 된다.

## 의존성

- `yt-dlp` (YouTube 자막·오디오 다운로드)
- `ffmpeg` (로컬 영상 → 오디오 변환)
- `gemini` CLI: `npm i -g @google/gemini-cli` (최초 1회 로그인)
- `markitdown[all]` (오디오 전사 진입점)

## 오류 처리

- **FFmpeg 미설치**: 설치 안내
- **yt-dlp 미설치**: `pip install yt-dlp`
- **gemini 미설치/미로그인**: `npm i -g @google/gemini-cli` 후 최초 호출 시 로그인
- **파일 없음**: 경로 확인 요청
- **URL 접근 실패 / 자막 없음**: Step 3 폴백(오디오 추출 → gemini 전사)
