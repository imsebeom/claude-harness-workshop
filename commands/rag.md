---
name: rag
description: "다양한 문서를 RAG용 마크다운으로 변환. /rag [파일경로 또는 URL]. 지원: PDF, HWP, HWPX, DOCX (기존), PPTX, XLSX, CSV, HTML, JSON, XML, WAV, MP3, YouTube URL, EPUB, ZIP (MarkItDown). 이미지 AI 설명 자동 생성."
---

# RAG 마크다운 변환 스킬

다양한 문서/파일/URL을 RAG 검색에 최적화된 마크다운으로 변환한다.
텍스트 추출 + 이미지 추출 + Claude CLI 이미지 설명까지 자동화.

## 스크립트 위치

- `C:\Users\hccga\.claude\skills\rag\scripts\pdf_to_md.py` — PDF → MD
- `C:\Users\hccga\.claude\skills\rag\scripts\doc_to_md.py` — HWP/HWPX/DOCX → MD
- `C:\Users\hccga\.claude\skills\rag\scripts\markitdown_to_md.py` — 추가 포맷 → MD (MarkItDown 기반)
- `C:\Users\hccga\.claude\skills\rag\scripts\fill_image_desc_claude.py` — Claude CLI 이미지 설명

## 지원 포맷 및 스크립트 매핑

| 확장자 | 스크립트 | 비고 |
|--------|----------|------|
| `.pdf` | `pdf_to_md.py` | 이미지 추출, 섹션 분할 지원 |
| `.hwp` | `doc_to_md.py` | 1차: Windows + 한컴 오피스 COM → .hwpx 임시 변환 (표·이미지 보존). 2차(폴백): pyhwp(순수 파이썬) → 텍스트 직접 추출 (한컴 無). 실패 시 자동 폴백 |
| `.hwpx` | `doc_to_md.py` | LibreOffice 경유 |
| `.docx` | `doc_to_md.py` | python-docx 직접 처리 |
| `.pptx` | `markitdown_to_md.py` | 슬라이드별 텍스트+이미지 참조 |
| `.xlsx`, `.xls` | `markitdown_to_md.py` | 시트별 마크다운 테이블 |
| `.csv` | `markitdown_to_md.py` | 원문 텍스트 |
| `.html`, `.htm` | `markitdown_to_md.py` | HTML → 마크다운 (구조 보존) |
| `.json` | `markitdown_to_md.py` | 원문 텍스트 |
| `.xml` | `markitdown_to_md.py` | 원문 텍스트 |
| `.wav`, `.mp3`, `.m4a`, `.ogg`, `.flac` | `markitdown_to_md.py` | Whisper turbo 음성인식 (로컬, 무료) |
| `.epub` | `markitdown_to_md.py` | 전자책 텍스트 추출 |
| `.zip` | `markitdown_to_md.py` | 내부 파일 텍스트 추출 |
| YouTube URL | `markitdown_to_md.py` | 제목+설명+자막 추출 |

## 의존성

### 기존 (PDF/HWP/HWPX/DOCX)
- `PyMuPDF` (fitz) — PDF 처리
- `python-docx` — DOCX 처리
- `Pillow` — 이미지 처리
- `LibreOffice` — HWPX → DOCX 변환
- `pywin32` + 한컴 오피스 — HWP → HWPX 변환 (Windows 전용, 1차 경로)
- `pyhwp` — HWP → 텍스트 폴백 (한컴·LibreOffice 없이 동작). `pip install pyhwp`. 강제: `RAG_DOC_BACKEND=pyhwp`
- Claude CLI (`claude -p`) — 이미지 설명 (Max 구독 포함, 추가 비용 없음)

### 추가 (MarkItDown + Whisper)
- `markitdown[all]` — PPTX/Excel/HTML/YouTube 등 처리
- `openai-whisper` — 오디오 음성인식 (turbo 모델, 로컬 실행, 무료)
- `ffmpeg` — 오디오 포맷 변환에 필요 (winget으로 설치됨)

## Step 1: 입력 확인

사용자가 제공한 파일 경로 또는 URL을 확인한다.

- 파일이 존재하는지 확인
- 확장자 확인 → 어느 스크립트로 처리할지 결정:
  - `.pdf` → `pdf_to_md.py`
  - `.hwp`, `.hwpx`, `.docx` → `doc_to_md.py`
  - `.pptx`, `.xlsx`, `.xls`, `.csv`, `.html`, `.htm`, `.json`, `.xml`, `.wav`, `.mp3`, `.m4a`, `.ogg`, `.epub`, `.zip` → `markitdown_to_md.py`
  - YouTube URL → `markitdown_to_md.py`
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
python "C:\Users\hccga\.claude\skills\rag\scripts\pdf_to_md.py" "<pdf_path>" \
  -o "<output_dir>" \
  --min-img-size 200 \
  --min-img-area 0
```

분할이 있는 경우:
```bash
python "C:\Users\hccga\.claude\skills\rag\scripts\pdf_to_md.py" "<pdf_path>" \
  -o "<output_dir>" \
  -s "<split_config.json>" \
  --min-img-size 200
```

### HWP / HWPX / DOCX 파일

```bash
python "C:\Users\hccga\.claude\skills\rag\scripts\doc_to_md.py" "<file_path>" \
  -o "<output_dir>"
```

`.hwp`는 Windows + 한컴 오피스 + `pywin32`가 필요하다. 한컴 COM(`HWPFrame.HwpObject`)으로 `.hwpx`를 임시 생성한 뒤 기존 HWPX 파이프라인으로 처리한다.

### 추가 포맷 (PPTX, XLSX, CSV, HTML, JSON, XML, 오디오, EPUB, ZIP, YouTube)

```bash
python "C:\Users\hccga\.claude\skills\rag\scripts\markitdown_to_md.py" "<file_or_url>" \
  -o "<output_dir>"
```

여러 파일/URL을 한 번에:
```bash
python "C:\Users\hccga\.claude\skills\rag\scripts\markitdown_to_md.py" \
  "file1.pptx" "file2.xlsx" "https://youtu.be/xxxx" \
  -o "<output_dir>"
```

### 여러 파일 일괄 처리

여러 PDF/문서를 처리할 때는 각 파일에 대해 위 명령을 순차 실행한다.
같은 출력 디렉토리를 쓰면 images/ 폴더가 공유된다.
추가 포맷 파일은 `markitdown_to_md.py`로 묶어서 한 번에 처리 가능.

## Step 4: 이미지 설명 (선택)

Claude CLI(`claude -p`)로 이미지 설명을 생성한다. Max 구독에 포함되어 추가 비용 없음.

```bash
python "C:\Users\hccga\.claude\skills\rag\scripts\fill_image_desc_claude.py" "<md_dir>" \
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
- **Claude CLI 오류/rate limit**: progress 파일이 있으므로 재실행하면 이어서 진행
- **Rate limit (429)**: 자동 백오프 내장, 워커 수를 줄여서 재시도
- **대용량 PDF (300p+)**: 반드시 분할 설정 사용 권장
- **이미지 파일 빈 결과**: MarkItDown은 LLM 없이 이미지→텍스트 불가. 이미지 OCR은 Claude CLI 이미지 설명 사용

## 하지 말 것

- 원본 문서의 내용을 창작하거나 변형하지 말 것
- 텍스트 추출 결과를 요약하거나 편집하지 말 것 (있는 그대로 MD에 넣기)
- 이미지 설명을 직접 작성하지 말 것 (반드시 Claude CLI 또는 Gemini API 사용)
