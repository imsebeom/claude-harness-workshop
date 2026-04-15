---
name: video-transcript
description: "YouTube 등 자막이 있는 영상 URL에서 자막(업로드/자동 생성)을 내려받아 RAG용 마크다운 파일을 생성하는 스킬. 사용 시점 - (1) YouTube 영상 내용을 빠르게 문서화할 때, (2) 영상 콘텐츠를 RAG 검색 가능하게 만들 때, (3) 강의/튜토리얼 요약을 만들 때. yt-dlp 자막 기반이라 Whisper 같은 STT를 돌리지 않고 빠르게 처리됨."
license: Proprietary
---

# Video Transcript 스킬

YouTube 등에서 **yt-dlp**로 자막(업로드된 자막 우선, 없으면 자동 생성 자막)을 내려받아 RAG용 마크다운으로 저장합니다. **Whisper를 사용하지 않습니다.**

## 기능

- yt-dlp로 업로드 자막·자동 생성 자막 다운로드
- VTT → 평문 정제 (타임스탬프·중복 제거)
- (선택) Claude로 섹션·헤딩·키워드 구조화
- RAG 친화적 마크다운 출력

## 의존성

```bash
pip install yt-dlp requests
```

- **yt-dlp**: 자막 다운로드 (필수)
- **requests**: Claude 구조화 호출 (선택, `--no-llm`으로 생략 가능)

## 사용법

```
/video-transcript [URL]
```

### 옵션
- `-o, --output`: 출력 마크다운 경로 (기본: `<영상 제목>.md`)
- `-l, --language`: 자막 언어 (ko/en/ja 등, 기본: ko → en → ja 순 탐색)
- `--no-llm`: LLM 구조화 생략, 정제된 평문만 저장

### 예시
```bash
python video_to_md.py "https://www.youtube.com/watch?v=..." -o out.md -l ko
python video_to_md.py "https://www.youtube.com/watch?v=..." --no-llm
```

## 제한

- 자막이 없는 영상은 지원하지 않음 (에러 반환, exit code 2)
- 로컬 영상 파일·음성 파일은 지원하지 않음 (STT 없음)
- 자막이 필요한데 없는 경우: 다른 도구(브라우저 수동 복사 등)로 대체

## 출력 형식

```markdown
---
source: URL
title: 영상 제목
created: 생성일시
language: ko
type: video-transcript
---

# 제목

[구조화된 본문 또는 정제된 평문]
```

## 스크립트 위치

`~/.claude/skills/video-transcript/scripts/video_to_md.py`
