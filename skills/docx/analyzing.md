# DOCX 서식/스타일 분석

기존 docx 문서의 글꼴, 크기, 스타일을 분석하는 방법.

## 1. 스타일 분석 스크립트

```bash
python scripts/analyze_styles.py document.docx
```

출력 예:

```
=== 스타일 목록 ===
Heading 2  | size=16.0pt
Heading 3  | size=12.0pt
Normal     | size=None (inherit)

=== 단락별 실제 서식 ===
p[ 0] style=Heading 2 | font=맑은 고딕 Semilight | size=14.0pt | Chapter 01. 챕터 제목...
p[ 1] style=Normal    | font=맑은 고딕 Semilight | size=10.0pt | 본문 텍스트...
```

## 2. 수동 분석 (python-docx)

```python
from docx import Document
from docx.oxml.ns import qn

doc = Document('document.docx')

for i, p in enumerate(doc.paragraphs):
    if not p.text.strip():
        continue
    style = p.style.name
    for r in p.runs:
        if not r.text.strip():
            continue
        # run 레벨 글꼴
        font_name = r.font.name
        font_size = f'{r.font.size.pt}pt' if r.font.size else 'inherit'
        # eastAsia 글꼴
        rpr = r.element.find(qn('w:rPr'))
        ea = None
        if rpr is not None:
            rfonts = rpr.find(qn('w:rFonts'))
            if rfonts is not None:
                ea = rfonts.get(qn('w:eastAsia'))
        print(f'p[{i}] style={style} | font={font_name} | ea={ea} | size={font_size}')
```

## 3. 확인해야 할 핵심 항목

| 항목 | 확인 방법 |
|------|-----------|
| 글꼴 이름 | `run.font.name` + `rFonts[@w:eastAsia]` |
| 글꼴 크기 | `run.font.size` (EMU) → `.pt`로 변환 |
| 스타일 매핑 | `paragraph.style.name` → Heading 2, Normal 등 |
| 볼드/이탤릭 | `run.bold`, `run.italic` |
| 색상 | `run.font.color.rgb` |
| 사용 가능한 스타일 | `doc.styles` 순회 — 스타일이 없으면 KeyError 발생 |

## 4. EMU ↔ pt 변환

```
1pt = 12700 EMU
예: 177800 EMU = 177800 / 12700 = 14pt
```
