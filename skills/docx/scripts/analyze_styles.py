"""DOCX 문서의 스타일, 글꼴, 크기를 분석하는 스크립트"""
import sys
from docx import Document
from docx.oxml.ns import qn
from docx.enum.style import WD_STYLE_TYPE

def analyze(path):
    doc = Document(path)

    print(f'=== {path} ===\n')

    # 1. 사용 가능한 스타일 목록
    print('--- PARAGRAPH 스타일 ---')
    for s in doc.styles:
        if s.type == WD_STYLE_TYPE.PARAGRAPH:
            sz = f'{s.font.size.pt}pt' if s.font and s.font.size else 'inherit'
            print(f'  {s.style_id:25s} | name={s.name:25s} | size={sz}')

    print('\n--- TABLE 스타일 ---')
    for s in doc.styles:
        if s.type == WD_STYLE_TYPE.TABLE:
            print(f'  {s.style_id:25s} | name={s.name}')

    # 2. 단락별 실제 서식
    print(f'\n--- 단락별 서식 (총 {len(doc.paragraphs)}개) ---')
    for i, p in enumerate(doc.paragraphs):
        if not p.text.strip():
            continue
        style = p.style.name if p.style else 'None'
        for j, r in enumerate(p.runs):
            if not r.text.strip():
                continue
            fname = r.font.name or 'inherit'
            fsize = f'{r.font.size.pt}pt' if r.font.size else 'inherit'
            ea = 'inherit'
            rpr = r.element.find(qn('w:rPr'))
            if rpr is not None:
                rfonts = rpr.find(qn('w:rFonts'))
                if rfonts is not None:
                    ea_val = rfonts.get(qn('w:eastAsia'))
                    if ea_val:
                        ea = ea_val
            text = r.text[:50]
            print(f'  p[{i:3d}] r[{j}] style={style:20s} | font={fname:22s} | ea={ea:22s} | size={fsize:8s} | {text}')

    print(f'\n--- 테이블: {len(doc.tables)}개 ---')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python analyze_styles.py <file.docx>')
        sys.exit(1)
    analyze(sys.argv[1])
