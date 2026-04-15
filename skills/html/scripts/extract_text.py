"""PDF 전체 텍스트를 페이지 구분자와 함께 raw.txt로 추출.

사용법: python extract_text.py <pdf_path> <out_path>
"""
import sys
import fitz


def main():
    if len(sys.argv) < 3:
        print("usage: extract_text.py <pdf> <out.txt>")
        sys.exit(1)
    pdf, out = sys.argv[1], sys.argv[2]
    doc = fitz.open(pdf)
    buf = []
    for i, p in enumerate(doc):
        buf.append(f"=== PAGE {i + 1} ===")
        buf.append(p.get_text())
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(buf))
    print(f"extracted {len(doc)} pages, {sum(len(x) for x in buf)} chars -> {out}")


if __name__ == "__main__":
    main()
