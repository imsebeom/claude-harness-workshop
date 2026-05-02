---
name: md
description: "다양한 문서를 AI가 읽기 좋은 마크다운으로 변환. /md [파일경로 또는 URL]. 지원: PDF, HWP, HWPX, DOCX (기존), PPTX, XLSX, CSV, HTML, JSON, XML, WAV, MP3, EPUB, ZIP (MarkItDown). 오디오는 gemini -p로 전사. YouTube URL은 video-transcript 위임. 이미지 AI 설명 자동 생성."
---

# 마크다운 변환 스킬

다양한 문서/파일/URL을 AI가 읽기 좋은 마크다운으로 변환한다.
텍스트 추출 + 이미지 추출 + Claude CLI 이미지 설명까지 자동화.

## 스크립트 위치

- `~/.claude/skills/md/scripts/pdf_to_md.py` — PDF → MD
- `~/.claude/skills/md/scripts/doc_to_md.py` — HWP/HWPX/DOCX → MD
- `~/.claude/skills/md/scripts/markitdown_to_md.py` — 추가 포맷 → MD (MarkItDown 기반)
- `~/.claude/skills/md/scripts/fill_image_desc_claude.py` — Claude CLI 이미지 설명
- `~/.claude/skills/video-transcript/scripts/video_to_md.py` — YouTube URL → MD (yt-dlp 자막)

## 지원 포맷 및 스크립트 매핑

| 확장자 | 스크립트 | 비고 |
|--------|----------|------|
| `.pdf` | `pdf_to_md.py` | 이미지 추출, 섹션 분할 지원 |
| `.hwp` | `doc_to_md.py` | 1차: 한컴 COM SaveAs(HWPX) → 순수 파이썬 hwpx 파서(표·이미지 보존 최상). 2차(폴백): 한컴 COM SaveAs(PDF) → `pdf_to_md.py` 위임(한컴 일부 빌드의 HWPX 자동화 회귀 버그 회피용). 3차(폴백): pyhwp 순수 파이썬(한컴·LibreOffice 無, 표는 `<표>` placeholder). 실패 시 자동 폴백 |
| `.hwpx` | `doc_to_md.py` | LibreOffice 경유 |
| `.docx` | `doc_to_md.py` | python-docx 직접 처리 |
| `.pptx` | `markitdown_to_md.py` | 슬라이드별 텍스트+이미지 참조 |
| `.xlsx`, `.xls` | `markitdown_to_md.py` | 시트별 마크다운 테이블 |
| `.csv` | `markitdown_to_md.py` | 원문 텍스트 |
| `.html`, `.htm` | `markitdown_to_md.py` | HTML → 마크다운 (구조 보존) |
| `.json` | `markitdown_to_md.py` | 원문 텍스트 |
| `.xml` | `markitdown_to_md.py` | 원문 텍스트 |
| `.wav`, `.mp3`, `.m4a`, `.ogg`, `.flac` | `markitdown_to_md.py` | `gemini -p` 헤드리스 전사 (무료, Max/Gemini CLI 구독 한도 내) |
| `.epub` | `markitdown_to_md.py` | 전자책 텍스트 추출 |
| `.zip` | `markitdown_to_md.py` | 내부 파일 텍스트 추출 |
| YouTube URL | `video_to_md.py` (video-transcript) | yt-dlp 기반. 업로드 자막 우선 → 자동 생성 자막 폴백. MarkItDown보다 자동 자막 커버리지 우수 |
| 일반 웹 URL (http/https, YouTube 제외) | Scrapling 직접 처리 | **WebFetch 사용 금지** — AI가 요약·압축해 원문 손실 발생 |

## 의존성

### 기존 (PDF/HWP/HWPX/DOCX)
- `PyMuPDF` (fitz) — PDF 처리
- `python-docx` — DOCX 처리
- `Pillow` — 이미지 처리
- `LibreOffice` — HWPX → DOCX 변환
- `pywin32` + 한컴 오피스 — HWP → HWPX 또는 PDF 변환 (Windows 전용, 1·2차 경로)
- `pyhwp` — HWP → 텍스트 폴백 (한컴·LibreOffice 없이 동작). `pip install pyhwp`
- 환경변수 `MD_DOC_BACKEND`로 백엔드 강제 가능: `hancom`(1차만) / `hancom_pdf`(2차만) / `pyhwp`(3차만). 비워두면 자동 폴백
- (선택) `C:\HwpAutoModule\FilePathCheckerModule.dll` + 레지스트리 `HKCU\SOFTWARE\HNC\HwpAutomation\Modules\FilePathCheckerModule` 등록 — 한컴 자동화 보안 dialog 우회. DLL은 `pip install pyhwpx` 후 패키지 안에서 복사 가능
- Claude CLI (`claude -p`) — 이미지 설명 (Max 구독 포함, 추가 비용 없음)

### 추가 (MarkItDown + 오디오 전사)
- `markitdown[all]` — PPTX/Excel/HTML 등 처리
- `gemini` CLI — 오디오 전사용 (`@파일경로` 프롬프트로 직접 전달, 별도 STT 설치 불필요)
- `ffmpeg` — 오디오 포맷 변환에 필요 (winget으로 설치됨)

### YouTube URL (video-transcript 스킬 위임)
- `yt-dlp` — 자막 다운로드 (업로드 자막 + 자동 생성 자막)
- Claude API 키 (선택) — 자막 텍스트의 LLM 구조화용. `~/.claude/apikeys/claude` 또는 `ANTHROPIC_API_KEY`. 없으면 원문 그대로 저장.

## Step 1: 입력 확인

사용자가 제공한 파일 경로 또는 URL을 확인한다.

- 파일이 존재하는지 확인
- 확장자 확인 → 어느 스크립트로 처리할지 결정:
  - `.pdf` → `pdf_to_md.py`
  - `.hwp`, `.hwpx`, `.docx` → `doc_to_md.py`
  - `.pptx`, `.xlsx`, `.xls`, `.csv`, `.html`, `.htm`, `.json`, `.xml`, `.wav`, `.mp3`, `.m4a`, `.ogg`, `.epub`, `.zip` → `markitdown_to_md.py`
  - YouTube URL (`youtube.com/watch`, `youtu.be/`, `youtube.com/shorts/` 등) → **Step 3-Y** (`video_to_md.py` — video-transcript 스킬 위임)
  - 일반 웹 URL (http/https, YouTube 제외) → **Step 3-W** (Scrapling)
- 여러 파일이면 목록으로 정리 (같은 스크립트끼리 묶어서 처리)
- 출력 디렉토리: 기본값은 원본 파일과 같은 위치에 `md/` 폴더

## Step 2: 변환 옵션 확인

사용자에게 다음 옵션을 확인한다 (명시하지 않으면 기본값 사용):

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| 출력 디렉토리 | `<원본위치>/md/` | MD 파일 저장 위치 |
| 이미지 설명 | 생성함 | Claude CLI로 이미지 설명 추가 여부 |
| 이미지 맥락 | 자동 감지 | 이미지 설명 시 맥락 (예: "초등 5학년 과학 교사용 지도서") |
| 최소 이미지 면적 | 100,000px | 이보다 작은 이미지는 설명 생략 |
| PDF 분할 | 없음 | 대용량 PDF를 섹션별로 나눌 때 JSON 설정 |
| 병렬 워커 수 | 10 | Claude CLI 병렬 수 |
| Claude 모델 | sonnet | 이미지 설명용 모델 |

### PDF 분할 설정 (대용량 PDF용)

하나의 PDF를 여러 MD로 나눌 때, 분할 설정 JSON 파일을 만든다:

```json
[
  {"start": 0, "end": 43, "name": "총론", "prefix": "총론"},
  {"start": 44, "end": 116, "name": "1단원_제목", "prefix": "1단원"}
]
```

- `start`/`end`: 0-indexed PDF 페이지 번호 (inclusive)
- `name`: 출력 MD 파일명 (확장자 제외)
- `prefix`: 이미지 파일명 접두어

분할 설정은 사용자가 직접 제공하거나, 목차를 확인하여 Claude가 생성한다.

## Step 3: 텍스트 + 이미지 추출

### PDF 파일

```bash
python "~/.claude/skills/md/scripts/pdf_to_md.py" "<pdf_path>" \
  -o "<output_dir>" \
  --min-img-size 200 \
  --min-img-area 0
```

분할이 있는 경우:
```bash
python "~/.claude/skills/md/scripts/pdf_to_md.py" "<pdf_path>" \
  -o "<output_dir>" \
  -s "<split_config.json>" \
  --min-img-size 200
```

### HWP / HWPX / DOCX 파일

```bash
python "~/.claude/skills/md/scripts/doc_to_md.py" "<file_path>" \
  -o "<output_dir>"
```

`.hwp`는 Windows + 한컴 오피스 + `pywin32`가 필요하다. 변환 폴백 체인:
1. **한컴 COM `SaveAs(HWPX)`** → 순수 파이썬 hwpx 파서 (표·이미지·서식 보존 최상)
2. **한컴 COM `SaveAs(PDF)`** → `pdf_to_md.py` 위임 (한컴 일부 빌드의 HWPX 자동화 회귀 버그를 회피하기 위한 폴백; 같은 빌드에서 PDF SaveAs는 정상 동작함이 확인됨)
3. **`pyhwp`** 순수 파이썬 (한컴·LibreOffice 무관, 표는 `<표>` placeholder)

폴백은 자동. 강제 단일 백엔드는 `MD_DOC_BACKEND` 환경변수로:
- `hancom` — 1차만, 실패 시 RuntimeError
- `hancom_pdf` — 2차만 (HWPX 회귀 버그가 있는 환경에서 시간 절약)
- `pyhwp` — 3차만 (한컴 없는 환경)

### 추가 포맷 (PPTX, XLSX, CSV, HTML, JSON, XML, 오디오, EPUB, ZIP)

```bash
python "~/.claude/skills/md/scripts/markitdown_to_md.py" "<file>" \
  -o "<output_dir>"
```

여러 파일을 한 번에:
```bash
python "~/.claude/skills/md/scripts/markitdown_to_md.py" \
  "file1.pptx" "file2.xlsx" \
  -o "<output_dir>"
```

> **YouTube URL은 여기서 처리하지 않는다.** MarkItDown의 YouTube 처리는 자동 생성 자막 커버리지가 부실하므로, 반드시 Step 3-Y(`video_to_md.py`)로 위임한다.

### Step 3-Y: YouTube URL (video-transcript 스킬 위임)

YouTube 계열 URL(`youtube.com/watch`, `youtu.be/`, `youtube.com/shorts/`, `m.youtube.com/...`)은 `/video-transcript` 스킬의 `video_to_md.py`에 위임한다. yt-dlp로 업로드 자막 우선 → 자동 생성 자막 폴백 → VTT 파싱 순으로 처리한다.

```bash
python "~/.claude/skills/video-transcript/scripts/video_to_md.py" "<YouTube URL>" \
  -o "<output_dir>/<파일명>.md" \
  -l ko
```

옵션:
- `-l ko` — 자막 언어 고정. 미지정 시 `ko, ko-KR, en, en-US, ja` 순으로 탐색
- `--no-llm` — LLM 구조화 비활성화(원문 자막 텍스트 그대로 저장). 기본은 Claude API로 섹션 헤딩·키워드 부여
- `-o` 생략 시 영상 제목 기반 파일명으로 현재 디렉토리에 저장

출력 디렉토리는 /md의 기본 규칙(`<원본위치>/md/`)에 맞추려면 `-o`로 명시 전달한다. 이미지가 없으므로 Step 4(이미지 설명)는 건너뛴다.

**자막 미제공 영상**: 스크립트가 exit code 2로 실패하면 자막이 없는 영상이므로 STT가 필요하다. yt-dlp로 오디오만 추출(`-x --audio-format mp3`)한 뒤 `markitdown_to_md.py`의 오디오 경로(`gemini -p` 전사)로 재처리하도록 안내한다.

### Step 3-W: 일반 웹 URL (Scrapling)

> **WebFetch 사용 금지**: WebFetch는 내부 AI가 콘텐츠를 요약·압축하므로 원문 손실이 발생한다. 일반 웹 URL에는 반드시 Scrapling을 사용한다.
> YouTube URL은 이 경로를 사용하지 않고 `markitdown_to_md.py`를 유지한다 (자막 추출 목적).

```python
PYTHONIOENCODING=utf-8 python - <<'EOF'
from scrapling import StealthyFetcher
from bs4 import BeautifulSoup
import pathlib, re, datetime

url = "<URL>"
out_dir = pathlib.Path("<output_dir>")
out_dir.mkdir(parents=True, exist_ok=True)

# 파일명: 도메인_경로 기반으로 자동 생성
slug = re.sub(r'[^\w-]', '_', url.split('//')[1])[:80]
out_path = out_dir / f"{slug}.md"

page = StealthyFetcher().fetch(url)
soup = BeautifulSoup(page.html, "html.parser")

# 불필요한 태그 제거
for tag in soup(["script", "style", "nav", "header", "footer",
                  "aside", "form", "noscript", "iframe"]):
    tag.decompose()

# 본문 추출 — article > main > body 순으로 시도
body = soup.find("article") or soup.find("main") or soup.find("body")

# 제목 추출
title = soup.find("h1")
title_text = title.get_text(strip=True) if title else url

# 마크다운 조립
lines = [
    f"# {title_text}",
    f"> 출처: {url}",
    f"> 수집일: {datetime.date.today().isoformat()}",
    "",
]
if body:
    # 태그별 마크다운 변환
    for el in body.find_all(["h1","h2","h3","h4","p","li","blockquote"]):
        t = el.get_text(strip=True)
        if not t:
            continue
        tag = el.name
        if tag == "h1": lines.append(f"# {t}")
        elif tag == "h2": lines.append(f"## {t}")
        elif tag == "h3": lines.append(f"### {t}")
        elif tag == "h4": lines.append(f"#### {t}")
        elif tag == "blockquote": lines.append(f"> {t}")
        elif tag == "li": lines.append(f"- {t}")
        else: lines.append(t)
        lines.append("")

md = "\n".join(lines)
out_path.write_text(md, encoding="utf-8")
print(f"추출 완료: {len(md):,}자 → {out_path}")
EOF
```

추출 후 생성된 `.md` 파일을 Read로 열어 본문이 온전한지 확인한다.
- 광고·메뉴 잔재가 많으면 CSS 선택자를 좁혀 재추출 (예: `soup.find("div", class_="article-body")`)
- Scrapling 실패 시 Playwright로 폴백 (CLAUDE.md 웹 접근 폴백 2단 참조)
- 웹 URL은 이미지가 없으므로 Step 4(이미지 설명)는 건너뛴다.

### 여러 파일 일괄 처리

여러 PDF/문서를 처리할 때는 각 파일에 대해 위 명령을 순차 실행한다.
같은 출력 디렉토리를 쓰면 images/ 폴더가 공유된다.
추가 포맷 파일은 `markitdown_to_md.py`로 묶어서 한 번에 처리 가능.

## Step 4: 이미지 설명 (선택)

Claude CLI(`claude -p`)로 이미지 설명을 생성한다. Max 구독에 포함되어 추가 비용 없음.

```bash
python "~/.claude/skills/md/scripts/fill_image_desc_claude.py" "<md_dir>" \
  -c "<맥락 설명>" \
  -w 10 \
  --model sonnet \
  --min-area 100000
```

- `<md_dir>`: Step 3에서 생성된 md/ 디렉토리
- `-w 10`: 병렬 워커 수 (기본: 10, Max 요금제 rate limit 고려)
- `--model sonnet`: 한글 OCR 정확도 높음 (기본값). haiku로 낮출 수도 있음
- 진행 파일(`image_desc_progress.json`)이 자동 생성되어 중단 후 재시작 가능
- **비용: 0원** (Max 구독에 포함)

### 이미지 설명 없이 진행

사용자가 이미지 설명을 원하지 않으면 Step 4를 건너뛴다.
이 경우 MD에 `![IMG_001](images/...)` 플레이스홀더만 남는다.

## Step 5: 결과 확인

완료 후 다음을 확인하고 사용자에게 보고한다:

1. 생성된 MD 파일 수
2. 추출된 이미지 수
3. 이미지 설명 수 (Step 4 진행 시)
4. 출력 디렉토리 위치
5. 샘플 MD 파일 앞부분 미리보기 (선택)

## 출력 구조

```
<output_dir>/
  파일명1.md
  파일명2.md
  images/
    파일명1_p1_001.png
    파일명1_p1_002.jpeg
    ...
  image_desc_progress.json  (이미지 설명 진행 파일)
```

## 오류 처리

- **PyMuPDF 미설치**: `pip install PyMuPDF` 안내
- **python-docx 미설치**: `pip install python-docx` 안내
- **LibreOffice 미설치**: HWPX 변환 불가, LibreOffice 설치 안내
- **한컴/pywin32 미설치**: HWP 변환 불가. 한컴 오피스 설치 + `pip install pywin32` 안내. macOS/Linux에서는 .hwpx로 먼저 저장 후 다시 시도
- **markitdown 미설치**: `pip install 'markitdown[all]'` 안내
- **ffmpeg 미설치**: MP3/M4A 오디오 변환 실패 (WAV는 ffmpeg 없이 동작)
- **gemini CLI 미설치/인증 실패**: 오디오 전사 실패. `npm i -g @google/gemini-cli` 설치 후 최초 1회 로그인 필요
- **Claude CLI 오류/rate limit**: progress 파일이 있으므로 재실행하면 이어서 진행
- **Rate limit (429)**: 자동 백오프 내장, 워커 수를 줄여서 재시도
- **대용량 PDF (300p+)**: 반드시 분할 설정 사용 권장
- **이미지 파일 빈 결과**: MarkItDown은 LLM 없이 이미지→텍스트 불가. 이미지 OCR은 Claude CLI 이미지 설명 사용

## 하지 말 것

- 원본 문서의 내용을 창작하거나 변형하지 말 것
- 텍스트 추출 결과를 요약하거나 편집하지 말 것 (있는 그대로 MD에 넣기)
- 이미지 설명을 직접 작성하지 말 것 (반드시 Claude CLI 또는 Gemini API 사용)
