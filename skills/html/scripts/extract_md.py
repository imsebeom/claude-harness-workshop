"""PDF → Markdown 추출 (PyMuPDF 기반).

raw.txt와 비교해 페이지 구분자를 '## Page N' 마크다운 헤딩으로 바꾼다.
LLM이 페이지 경계를 헤딩으로 인지하므로 챕터 분할에 더 적게 일한다.
도형·이미지는 extract_figures.py가 별도로 처리한다.

/md 스킬도 PDF는 PyMuPDF로 처리하므로(pdf_to_md.py), /md 결과 md와
같은 본문 추출 결과가 나온다 — /md로 만든 md를 /html이 그대로
재사용하는 흐름이 자연스럽게 성립한다.

사용법: python extract_md.py <pdf_path> <out_md_path>
"""

import sys
from pathlib import Path

import fitz


def main():
    if len(sys.argv) < 3:
        print("usage: extract_md.py <pdf> <out.md>")
        sys.exit(1)
    pdf, out = sys.argv[1], sys.argv[2]
    doc = fitz.open(pdf)
    buf = []
    for i, page in enumerate(doc):
        buf.append(f"## Page {i + 1}\n")
        buf.append(page.get_text())
        buf.append("")
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(buf)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"extracted {len(doc)} pages, {len(text)} chars -> {out}")


if __name__ == "__main__":
    main()
