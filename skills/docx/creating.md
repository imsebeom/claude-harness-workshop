# 새 DOCX 문서 생성

템플릿 없이 빈 문서를 생성하는 방법. **가능하면 템플릿 방식을 우선 사용할 것.**

## 기본 패턴

```python
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn

doc = Document()

# 기본 스타일 설정
style = doc.styles['Normal']
style.font.name = '맑은 고딕'
style.font.size = Pt(10)
style.element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')

# Heading 스타일도 개별 설정 필요
for level in range(1, 7):
    heading_style = doc.styles[f'Heading {level}']
    heading_style.font.name = '맑은 고딕'
    heading_style.element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')

# 내용 작성
doc.add_heading('제목', level=1)
p = doc.add_paragraph()
run = p.add_run('본문 텍스트')
run.font.name = '맑은 고딕'
run.element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')

doc.save('output.docx')
```

## 표 생성 필수 패턴 (autofit 해제 + 직접 너비 설정)

> **`doc.add_table()`만 단독 사용 금지.** 반드시 아래 `create_table()` 헬퍼를 사용하거나, 동등한 처리를 적용해야 한다.

python-docx의 `add_table()`은 기본적으로 autofit이 켜져 있어 열 너비가 균등 배분된다.
Word/LibreOffice 모두에서 의도한 열 너비를 정확히 반영하려면 **4가지를 모두 설정**해야 한다:

1. **`tbl.autofit = False`** — python-docx 레벨 autofit 해제
2. **`tblLayout` = fixed** — XML 레벨 자동 너비 조정 비활성화
3. **`tblGrid`에 `gridCol` 너비** — LibreOffice가 이 값으로 열 너비를 결정 (핵심!)
4. **각 셀의 `tcW`** — Word 호환용

### `create_table()` 헬퍼 (필수 사용)

```python
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

def create_table(doc, rows, col_widths_cm, style='Table Grid'):
    """autofit 해제 + 열 너비 직접 설정된 표를 생성한다.

    Args:
        doc: Document 객체
        rows: 행 수
        col_widths_cm: 각 열 너비 리스트 (cm 단위). 예: [4.0, 8.0, 4.0]
        style: 표 스타일 (기본 'Table Grid')

    Returns:
        Table 객체
    """
    cols = len(col_widths_cm)
    tbl = doc.add_table(rows=rows, cols=cols, style=style)

    # 1) python-docx 레벨 autofit 해제
    tbl.autofit = False

    tblPr = tbl._tbl.tblPr

    # 2) 전체 테이블 너비 고정 (dxa 단위) — 기존 tblW 제거 후 설정
    for old in tblPr.findall(qn('w:tblW')):
        tblPr.remove(old)
    total_twips = int(sum(col_widths_cm) * 567)
    tblW = OxmlElement('w:tblW')
    tblW.set(qn('w:w'), str(total_twips))
    tblW.set(qn('w:type'), 'dxa')
    tblPr.append(tblW)

    # 3) 레이아웃 fixed — 기존 tblLayout 제거 후 설정
    for old in tblPr.findall(qn('w:tblLayout')):
        tblPr.remove(old)
    tblLayout = OxmlElement('w:tblLayout')
    tblLayout.set(qn('w:type'), 'fixed')
    tblPr.append(tblLayout)

    # 4) tblGrid — LibreOffice가 실제 열 너비를 이것으로 결정
    for old_grid in tbl._tbl.findall(qn('w:tblGrid')):
        tbl._tbl.remove(old_grid)
    tblGrid = OxmlElement('w:tblGrid')
    for w_cm in col_widths_cm:
        gridCol = OxmlElement('w:gridCol')
        gridCol.set(qn('w:w'), str(int(w_cm * 567)))
        tblGrid.append(gridCol)
    tbl._tbl.insert(list(tbl._tbl).index(tblPr) + 1, tblGrid)

    # 5) 각 셀에도 tcW 설정 — 기존 tcW 제거 후 설정 (Word 호환)
    for i, w_cm in enumerate(col_widths_cm):
        twips = str(int(w_cm * 567))
        for row in tbl.rows:
            tc = row.cells[i]._tc
            tcPr = tc.get_or_add_tcPr()
            for old in tcPr.findall(qn('w:tcW')):
                tcPr.remove(old)
            tcW = parse_xml(
                f'<w:tcW {nsdecls("w")} w:w="{twips}" w:type="dxa"/>'
            )
            tcPr.append(tcW)

    return tbl
```

### 사용 예시

```python
# 3열 표: 항목(4cm) / 내용(10cm) / 비고(2cm) = 총 16cm
tbl = create_table(doc, rows=5, col_widths_cm=[4.0, 10.0, 2.0])

# 헤더 채우기
tbl.cell(0, 0).text = '항목'
tbl.cell(0, 1).text = '내용'
tbl.cell(0, 2).text = '비고'

# 데이터 채우기
tbl.cell(1, 0).text = '이름'
tbl.cell(1, 1).text = '홍길동'
```

### 열 너비 가이드라인

A4 문서(좌우 여백 각 2.54cm)의 사용 가능 너비: **약 15.92cm**

| 레이아웃 | 열 너비 예시 |
|---------|-------------|
| 2열 (라벨+값) | `[4.0, 12.0]` |
| 3열 (번호+내용+비고) | `[2.0, 11.0, 3.0]` |
| 4열 균등 | `[4.0, 4.0, 4.0, 4.0]` |
| 5열 (좁은 열 포함) | `[3.5, 8.0, 2.5, 1.0, 1.0]` |

### 셀 내부 여백 제거 (좁은 열용)

열 너비가 매우 좁을 때(1cm 이하) 셀 내부 여백을 0으로 설정하면 글자가 들어간다:

```python
def set_cell_zero_margin(cell):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for side in ('top', 'left', 'bottom', 'right'):
        el = OxmlElement(f'w:{side}')
        el.set(qn('w:w'), '0')
        el.set(qn('w:type'), 'dxa')
        tcMar.append(el)
    tcPr.append(tcMar)
```

### 단위 변환

- **cm → twips(dxa)**: `int(cm * 567)` (1cm ≈ 567 twips)
- **inches → twips**: `int(inches * 1440)`

## 주의사항

- `Document()` 빈 문서는 최소한의 스타일만 포함
- 한국어 글꼴은 반드시 `eastAsia` 속성도 설정
- 각 Heading 레벨의 크기를 명시적으로 지정해야 함
- 표 스타일('Table Grid')은 기본 포함되어 있음
- 'List Bullet' 스타일은 기본 포함되어 있음 (빈 문서 한정)
- **표 생성 시 반드시 `create_table()` 헬퍼 사용** — `doc.add_table()` 단독 사용 금지
