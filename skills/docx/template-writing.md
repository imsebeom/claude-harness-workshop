# 템플릿 기반 DOCX 작성

기존 docx 파일을 템플릿으로 사용하여 문서를 생성하는 방법.

## 왜 템플릿을 쓰는가?

- **스타일 일관성**: 글꼴, 크기, 간격, 색상 등이 템플릿에서 자동 상속
- **수동 지정 최소화**: Heading, Normal 등 스타일 정의를 새로 만들 필요 없음
- **규격 준수**: 출판사, 회사 등의 양식을 정확히 따를 수 있음

## 워크플로

### 1단계: 템플릿 분석

```bash
python scripts/analyze_styles.py template.docx
```

확인할 것:
- 어떤 Heading 레벨이 있는지 (Heading 1~6)
- 각 Heading의 글꼴과 크기
- Normal(본문)의 글꼴과 크기
- 사용 가능한 스타일 목록 (List Bullet이 있는지, List Paragraph가 있는지 등)
- Table Grid 등 표 스타일

### 2단계: 템플릿 열기 + 내용 제거

```python
from docx import Document

def open_template(template_path):
    """템플릿 열고 기존 내용 제거 (스타일 정의는 보존)"""
    doc = Document(template_path)
    for p in doc.paragraphs:
        p._element.getparent().remove(p._element)
    for t in doc.tables:
        t._element.getparent().remove(t._element)
    return doc
```

### 3단계: 스타일 매핑 정의

템플릿의 Heading 레벨과 문서 구조를 매핑:

```python
# 예: 제이펍 양식
# level 1 → Heading 2 (Chapter/파트)   → 14pt
# level 2 → Heading 3 (Lesson)        → 12pt
# level 3 → Heading 4 ([중] 중제목)    → 12pt
# level 4 → Heading 5 ([소] 소제목)    → 10pt

def h(doc, text, level):
    style_level = level + 1  # 문서 구조 → Heading 스타일 매핑
    heading = doc.add_heading(text, level=style_level)
    # 필요시 글꼴/크기 명시적 지정
    for run in heading.runs:
        set_font(run, size)
    return heading
```

### 4단계: 내용 작성

```python
doc = open_template('template.docx')

h(doc, '파트 제목', 1)
para(doc, '본문 텍스트...')
bullet(doc, '불릿 항목')
note_box(doc, 'Tip', '팁 내용')
screenshot_box(doc, 'filename.png', '캡션')

doc.save('output.docx')
```

## 헬퍼 함수 패턴

### 글꼴 설정

```python
from docx.oxml.ns import qn

FONT_NAME = '맑은 고딕 Semilight'  # 템플릿에서 확인한 글꼴

def set_font(run, size=None):
    run.font.name = FONT_NAME
    run.element.rPr.rFonts.set(qn('w:eastAsia'), FONT_NAME)
    if size:
        run.font.size = size
```

### 불릿 (List Paragraph)

일부 템플릿에 'List Bullet' 스타일이 없을 수 있음. 'List Paragraph'를 사용:

```python
def bullet(doc, text):
    p = doc.add_paragraph(style='List Paragraph')
    p.paragraph_format.left_indent = Cm(1)
    run = p.add_run('• ' + text)
    set_font(run, FONT_SIZE['body'])
    return p
```

### 표 생성 (autofit 해제 필수)

템플릿 기반이든 새 문서든, 표 생성 시 반드시 `create_table()` 헬퍼를 사용한다.
→ [creating.md](creating.md) "표 생성 필수 패턴" 섹션의 `create_table()` 참조

```python
# 예: 3열 표 — 항목(4cm) / 내용(10cm) / 비고(2cm)
tbl = create_table(doc, rows=5, col_widths_cm=[4.0, 10.0, 2.0])
```

### 빈 박스 (스크린샷 자리)

```python
def screenshot_box(doc, filename, caption):
    table = create_table(doc, rows=1, col_widths_cm=[16.0])
    # 표 높이 설정...
    # 캡션 추가...
```

### 이미지 삽입

```python
def insert_image(doc, img_path, filename, caption, width=None):
    if os.path.exists(img_path):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.add_picture(img_path, width=width)
        # 캡션 추가...
    else:
        screenshot_box(doc, filename, caption + ' (이미지 없음)')
```

## 흔한 문제와 해결

| 문제 | 원인 | 해결 |
|------|------|------|
| `KeyError: "no style with name 'List Bullet'"` | 템플릿에 해당 스타일 없음 | `analyze_styles.py`로 사용 가능한 스타일 확인 후 대체 |
| 한글 글꼴 미적용 | `eastAsia` 속성 미설정 | `set_font()` 헬퍼에서 `qn('w:eastAsia')` 설정 |
| 제목 크기 불일치 | python-docx 기본 Heading 크기 사용 | 명시적으로 `run.font.size` 지정 |
| 새 문서에서 스타일 부족 | `Document()`는 최소 스타일만 포함 | 템플릿 기반으로 전환 |
