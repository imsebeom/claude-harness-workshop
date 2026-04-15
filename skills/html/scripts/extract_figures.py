"""PDF 각 페이지에서 벡터 드로잉을 클러스터링하여 도형 이미지로 추출.

사용법:
    python extract_figures.py <pdf_path> <out_dir> [--scale 2] [--skip 1,2,76]

추출 규칙
- 드로잉 bbox를 `gap`(기본 12pt)만큼 팽창시킨 뒤 겹치는 것끼리 병합.
- 병합 결과가 90×70pt 이상일 때 후보로 간주.
- 단어 밀도(words/100² pt)가 4.8 초과면 텍스트 컬럼으로 판단해 제외.
- 단어수가 100을 넘는 클러스터도 제외.
- 인근(20pt) 소형 텍스트 블록(면적 5만 pt² 이하)을 라벨로 편입.
- 장식 요소: `words<12 AND w<400 AND h<400`이면 제외.

출력: `<out_dir>/fig_p<NN>_<idx>.png` + `_meta.json`
"""
import argparse
import json
import os
import fitz


def merge_rects(rects, gap=12):
    rects = [fitz.Rect(r) for r in rects]
    changed = True
    while changed:
        changed = False
        out = []
        used = [False] * len(rects)
        for i, r in enumerate(rects):
            if used[i]:
                continue
            cur = fitz.Rect(r)
            used[i] = True
            for j in range(i + 1, len(rects)):
                if used[j]:
                    continue
                exp = fitz.Rect(cur.x0 - gap, cur.y0 - gap, cur.x1 + gap, cur.y1 + gap)
                if exp.intersects(rects[j]):
                    cur |= rects[j]
                    used[j] = True
                    changed = True
            out.append(cur)
        rects = out
    return rects


def find_figures(page, gap=12, min_w=90, min_h=70, max_density=4.8, max_words=100):
    pr = page.rect
    drs = [d["rect"] for d in page.get_drawings() if d.get("rect")]
    drs = [
        r
        for r in drs
        if not (r.width > pr.width * 0.9 and r.height > pr.height * 0.9)
        and r.width > 3
        and r.height > 3
    ]
    merged = merge_rects(drs, gap=gap)
    merged = [r for r in merged if r.width > min_w and r.height > min_h]

    words = page.get_text("words")
    blocks = page.get_text("blocks")

    picks = []
    for r in merged:
        n = 0
        for w in words:
            wr = fitz.Rect(w[:4])
            if r.contains(wr.tl) and r.contains(wr.br):
                n += 1
        dens = n / ((r.width * r.height) / 10000)
        if n > max_words or dens > max_density:
            continue
        expanded = fitz.Rect(r)
        for b in blocks:
            br = fitz.Rect(b[:4])
            check = fitz.Rect(r.x0 - 20, r.y0 - 15, r.x1 + 20, r.y1 + 15)
            if check.intersects(br) and br.get_area() < 50000:
                union = expanded | br
                if union.get_area() < expanded.get_area() * 1.5:
                    expanded = union
        picks.append((expanded, r, n, round(dens, 2)))

    picks.sort(key=lambda c: -c[0].get_area())
    final = []
    for e, r, n, d in picks:
        overlap = False
        for fe, _, _, _ in final:
            if e.intersects(fe):
                ov = (e & fe).get_area() / min(e.get_area(), fe.get_area())
                if ov > 0.6:
                    overlap = True
                    break
        if not overlap:
            final.append((e, r, n, d))
    final.sort(key=lambda c: (c[0].y0, c[0].x0))
    return final


def is_decorative(r, n, min_words=12, min_size=400):
    return n < min_words and r.width < min_size and r.height < min_size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("out_dir")
    ap.add_argument("--scale", type=float, default=2.0)
    ap.add_argument("--skip", default="", help="제외할 페이지 번호 (쉼표 구분)")
    ap.add_argument("--keep-decorative", action="store_true")
    args = ap.parse_args()

    skip = {int(x) for x in args.skip.split(",") if x.strip()}
    os.makedirs(args.out_dir, exist_ok=True)
    for f in os.listdir(args.out_dir):
        if f.endswith(".png") or f == "_meta.json":
            os.remove(os.path.join(args.out_dir, f))

    doc = fitz.open(args.pdf)
    mat = fitz.Matrix(args.scale, args.scale)
    meta = []
    for pno in range(1, len(doc) + 1):
        if pno in skip:
            continue
        page = doc[pno - 1]
        figs = find_figures(page)
        for idx, (e, r, n, d) in enumerate(figs):
            if not args.keep_decorative and is_decorative(e, n):
                continue
            pad = 10
            clip = fitz.Rect(
                max(0, e.x0 - pad),
                max(0, e.y0 - pad),
                min(page.rect.width, e.x1 + pad),
                min(page.rect.height, e.y1 + pad),
            )
            pix = page.get_pixmap(clip=clip, matrix=mat, alpha=False)
            fn = f"fig_p{pno:02d}_{idx}.png"
            pix.save(os.path.join(args.out_dir, fn))
            meta.append(
                {
                    "page": pno,
                    "idx": idx,
                    "file": fn,
                    "words": n,
                    "density": d,
                    "w": int(e.width),
                    "h": int(e.height),
                }
            )

    with open(os.path.join(args.out_dir, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    total = sum(
        os.path.getsize(os.path.join(args.out_dir, f))
        for f in os.listdir(args.out_dir)
        if f.endswith(".png")
    )
    print(f"figures: {len(meta)} | size: {total / 1024 / 1024:.2f} MB -> {args.out_dir}")


if __name__ == "__main__":
    main()
