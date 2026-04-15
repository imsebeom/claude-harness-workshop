---
name: html
description: PDF·DOCX·HWPX 등 기존 문서를 모바일 친화적인 HTML ebook으로 변환하는 스킬. 단일 index.html로 출력하며 Pretendard 웹폰트, 다크모드, 진행률 바, 드로어/사이드 TOC, 글자 크기 조절(A-/A+), 본문 삽입용 벡터 도형 추출을 제공한다. PDF 원본에 포함된 벡터 다이어그램·워크시트를 밀도 기반 클러스터링으로 잘라내어 본문에 인라인 배치한다. 트리거 - "HTML ebook으로 만들어줘", "모바일 뷰어로 변환", "PDF를 웹페이지로", "문서를 egpt로 배포".
---

# HTML ebook 변환 스킬

PDF 등 기존 문서를 모바일 친화적인 단일 HTML 파일로 변환한다. 서적·가이드북 등 분량이 있는 문서에 적합하다.

## 트리거
- "이 PDF를 모바일 HTML로 만들어줘"
- "문서를 HTML ebook으로 변환"
- "egpt에 올릴 HTML로"
- "웹 뷰어 페이지로"

## 원칙
- **단일 `index.html`** + `figs/` 하위 폴더 (선택) 구조. 외부 CDN은 Pretendard 웹폰트만 허용.
- **출력 언어는 한국어가 기본**이다. 원문이 영어·기타 외국어면 **전체 본문을 한국어로 번역**해 배치한다. 사용자가 명시적으로 "원문 유지" 또는 "영어 그대로"라고 요청했을 때만 원문 언어를 유지한다.
  - 번역 톤: 학술/가이드북 스타일의 자연스러운 '-다' 체. 번역투 금지.
  - 핵심 용어는 **첫 등장 시 "한국어(English)" 병기**, 이후에는 한국어만 사용.
  - 프레임워크·표준 약어(TPACK, UDL, STEAM, API 등)는 그대로 유지.
  - 인용 표기 `(Author, Year)`와 참고문헌(APA 등)은 **원문 그대로** 두고 섹션 제목("참고문헌")만 번역.
  - 표(Table)의 헤더·셀 내용도 번역하되, 인명·연도·약어는 유지. 캡션은 "표 1", "그림 1" 형식.
- 본문은 **요약하지 않는다**. 번역 시에도 원문의 모든 문단을 빠짐없이 옮긴다.
- 이모지·장식 기호 지양. semantic HTML 사용.
- PDF 페이지 전체를 이미지로 붙이지 말 것. **벡터 드로잉을 클러스터링해 도형만 추출**하여 인라인 삽입한다.
- **출처 표기 필수**. 항상 본문 상단(목차 아래)에 원문 출처 바를 노출한다.
  - 원문이 웹페이지면 `source_url`을 `render_shell()`에 넘긴다 → 클릭 시 새 탭으로 열림.
  - 원문이 로컬 파일(PDF/HWPX 등)이면 `source_file`을 넘긴다 → 파일을 출력 폴더에 함께 복사하고 다운로드 링크로 노출. (배포 시 같은 경로에 있어야 함)
  - 원문 종류가 특수하면 `source_label`로 라벨 변경 ("원본 PDF" 등).

## 작업 흐름

### 1. 소스 문서 준비
- PDF면 그대로 진행.
- DOCX / HWPX 등은 `/hwpx` 또는 `/pdf` 스킬로 먼저 PDF로 변환한다.
- 출력 폴더: `C:/Users/hccga/Desktop/code/<프로젝트명>/`

### 2. 텍스트 추출
```bash
PYTHONIOENCODING=utf-8 python "C:/Users/hccga/.claude/skills/html/scripts/extract_text.py" <pdf_path> <project_dir>/raw.txt
```
- 페이지 구분자(`=== PAGE N ===`)를 포함한 `raw.txt` 생성.
- 분량이 크면 (>100KB) 이후 HTML 조립을 **general-purpose 에이전트에 위임**해 본문 컨텍스트를 보호한다.

### 3. 벡터 도형 추출
```bash
PYTHONIOENCODING=utf-8 python "C:/Users/hccga/.claude/skills/html/scripts/extract_figures.py" <pdf_path> <project_dir>/figs
```
- 각 페이지에서 `get_drawings()`로 경로 bbox를 얻고 인접한 것끼리 병합.
- **단어 밀도(words/100²pt)**가 4.8 이하면 도형으로 판정(텍스트 컬럼 제외).
- 인근 텍스트 블록을 라벨로 편입해 캡션/라벨까지 포함.
- 장식 필터: 단어수<12 AND 크기<400×400 → 제외.
- 출력: `figs/fig_p<NN>_<idx>.png` + `_meta.json`
- 추출 후 반드시 Read로 몇 장 샘플 확인하고, 장식이 남아 있으면 `_meta.json`에서 제거한다.

### 4. HTML 조립
`scripts/html_shell.py`를 import하여 뼈대를 가져오거나, 직접 raw.txt를 파싱해 섹션(`<section class="chapter accent-*">`)에 배치한다.

필수 구성 요소:
- `<meta name="viewport" content="width=device-width,initial-scale=1">`
- Pretendard CDN: `https://cdn.jsdelivr.net/gh/orioncactus/pretendard@latest/dist/web/static/pretendard.min.css`
- CSS 변수 `--fs-scale`로 body font-size 제어 (A-/A+ 버튼이 7단계로 토글, localStorage 저장)
- 읽기 진행률 바(fixed top)
- 드로어 TOC (모바일) / sticky sidebar TOC (≥1100px)
- 맨 위로 플로팅 버튼
- `prefers-color-scheme: dark` 대응
- 장별 accent 색상(6색 순환)

피겨 삽입 규칙:
- `<figure class="book-fig">` 카드 사용. 클릭 시 `target="_blank"`로 원본 열기.
- 각 장 말미 또는 관련 단락 직후에 삽입.
- 부록(워크시트 묶음)은 `<div class="chapter-figures fig-grid">`로 데스크톱 2열 그리드 배치.

본문 분량이 클 때는 **general-purpose 에이전트에 HTML 조립을 위임**한다:
- 에이전트에게 raw.txt 경로, figs 경로, 메타 정보, html_shell.py 경로를 전달
- 원문 언어가 외국어면 **한국어 번역 지시를 명시**(톤·용어 병기 규칙 포함)
- 원문을 빠짐없이 옮기되 요약 금지 명시
- 200단어 이하 보고서만 받아서 컨텍스트 보호

### 5. 검증
- 파일 크기 확인 (`ls -lh`)
- 주요 섹션 h2 수 확인 (프롤로그+장+부록)
- 브라우저(Chrome MCP)로 열어 모바일 뷰(360px) 스크롤·TOC·글자 크기·피겨 확인

### 6. 배포 (선택)
사용자가 요청하면 `/egpt <폴더명>` 스킬로 Firebase Hosting 하위 경로 배포.

## 의존성
- `fitz` (PyMuPDF) — 텍스트·드로잉 추출, 피겨 렌더링
- 브라우저(선택) — 모바일 뷰 검증용

## 스크립트 참조
- `scripts/extract_text.py` — PDF → raw.txt (페이지 구분자 포함)
- `scripts/extract_figures.py` — 벡터 드로잉 클러스터링 + 라벨 편입 + 밀도 필터
- `scripts/html_shell.py` — HTML 뼈대(CSS/JS) 생성 함수

## 튜닝 노트
- 2-up 스프레드 PDF는 각 드로잉이 half-page 프레임에 묶일 수 있다. `gap` 값을 10~12 사이로 유지.
- 워크시트 페이지는 단어수 60~90이지만 밀도는 2 미만이다. 임계값 4.8은 TPACK 벤다이어그램(밀도 2.4)과 텍스트 컬럼(밀도 6~9)을 잘 구분한다.
- 페이지 전체 배경 사각형은 `width/height > page*0.9`로 제외.
- 클러스터 크기 하한은 `90×70pt`로 설정. 더 작으면 아이콘·장식.
