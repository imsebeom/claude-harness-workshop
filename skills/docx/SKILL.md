---
name: docx
description: ".docx 파일이 관련된 모든 작업에 이 스킬을 사용한다. 문서 생성, 읽기, 편집, 템플릿 기반 작성, 텍스트 추출, 서식 분석 등을 포함한다. 사용자가 '문서', '워드', 'docx', '원고'를 언급하거나 .docx 파일명을 참조할 때 트리거한다."
---

# DOCX 스킬

## Quick Reference

| 작업 | 방법 |
|------|------|
| 텍스트 추출/읽기 | `python -m markitdown document.docx` 또는 python-docx로 직접 읽기 |
| 서식/스타일 분석 | [analyzing.md](analyzing.md) 참조 |
| 템플릿 기반 문서 생성 | [template-writing.md](template-writing.md) 참조 |
| 새 문서 생성 | [creating.md](creating.md) 참조 |

---

## 핵심 원칙: 템플릿 기반 작성

**기존 docx 파일을 템플릿으로 사용하는 것을 항상 우선한다.**

새 Document()로 빈 문서를 만들면 글꼴·크기·간격 등을 모두 수동으로 지정해야 하고, 원본과 불일치가 발생하기 쉽다. 대신:

1. **기존 문서(템플릿)를 `Document(template_path)`로 열기**
2. **기존 내용(단락, 테이블)을 제거** — 스타일 정의는 보존됨
3. **템플릿의 스타일(Heading, Normal 등)을 그대로 사용**하여 내용 작성
4. 글꼴·크기는 템플릿에서 상속되므로, **명시적 지정은 최소화**

```python
from docx import Document

def open_template(template_path):
    doc = Document(template_path)
    for p in doc.paragraphs:
        p._element.getparent().remove(p._element)
    for t in doc.tables:
        t._element.getparent().remove(t._element)
    return doc
```

---

## 읽기/분석

```bash
# 텍스트 추출 (빠른 확인)
python -m markitdown document.docx

# 서식 분석 (스타일, 글꼴, 크기 확인)
python scripts/analyze_styles.py document.docx
```

---

## 문서 생성 워크플로

### 템플릿이 있는 경우 (권장)

**[template-writing.md](template-writing.md) 참조.**

1. 템플릿 docx의 스타일 분석 (`analyze_styles.py`)
2. `open_template()`로 스타일만 상속
3. `doc.add_heading()`, `doc.add_paragraph()` 등으로 내용 작성
4. 필요시 `set_font(run, size)` 헬퍼로 크기만 명시적 지정
5. 저장

### 템플릿이 없는 경우

**[creating.md](creating.md) 참조.**

1. `Document()`로 새 문서 생성
2. Normal 스타일에 기본 글꼴/크기 설정
3. 각 요소별 글꼴/크기 명시적 지정
4. 저장

---

## 글꼴 설정 헬퍼

python-docx에서 한국어 글꼴을 정확히 적용하려면 `eastAsia` 속성도 설정해야 한다:

```python
from docx.oxml.ns import qn

def set_font(run, font_name, size=None):
    run.font.name = font_name
    run.element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
    if size:
        run.font.size = size
```

---

## 핵심 원칙: 표(Table) 생성

**표를 만들 때 반드시 autofit을 해제하고 열 너비를 직접 설정한다.**

`doc.add_table()`만 사용하면 자동너비(autofit)가 적용되어 열 너비가 균등 배분되며, 의도한 레이아웃이 깨진다. 반드시 `create_table()` 헬퍼 또는 동등한 처리를 적용할 것.

→ 상세 코드와 `create_table()` 헬퍼: [creating.md](creating.md) "표 생성 필수 패턴" 섹션 참조

---

## 주의사항

- **LibreOffice가 설치되어 있어** docx → PDF 변환 가능: `soffice --headless --convert-to pdf document.docx`
- python-docx의 `add_heading(level=N)` 스타일과 템플릿의 Heading 스타일이 매핑되는지 확인할 것
- 템플릿에 없는 스타일(예: 'List Bullet')을 사용하면 `KeyError` 발생 — `List Paragraph` 등 템플릿에 존재하는 스타일을 사용
- EMU ↔ pt 변환: 1pt = 12700 EMU
