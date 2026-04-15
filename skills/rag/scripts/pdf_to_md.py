#!/usr/bin/env python3
"""
pdf_to_md.py — PDF → Markdown 변환 (RAG용)

사용법:
  python pdf_to_md.py <pdf_path> [옵션]

옵션:
  -o, --output DIR        출력 디렉토리 (기본: PDF와 같은 위치에 md/)
  -s, --split JSON_FILE   분할 설정 JSON (섹션별 페이지 범위)
  -p, --prefix PREFIX     이미지 파일명 접두어 (기본: PDF 파일명)
  --min-img-size PX       최소 이미지 크기 (기본: 200)
  --min-img-area PX       최소 이미지 면적 (기본: 0, 제한 없음)

분할 설정 JSON 예시:
  [
    {"start": 0, "end": 43, "name": "총론", "prefix": "총론"},
    {"start": 44, "end": 116, "name": "1단원_제목", "prefix": "1단원"}
  ]
  start/end는 0-indexed PDF 페이지 번호.
"""

import fitz
import os
import re
import json
import argparse
from pathlib import Path


MIN_IMG_SIZE = 200


def extract_images_from_page(doc, page, img_prefix, page_num, images_dir, min_size, min_area):
    """페이지에서 의미 있는 이미지를 추출하고 플레이스홀더 목록 반환."""
    placeholders = []
    image_list = page.get_images(full=True)

    smask_xrefs = set()
    for img_info in image_list:
        smask = img_info[1]
        if smask > 0:
            smask_xrefs.add(smask)

    seen_xrefs = set()
    img_idx = 0

    for img_info in image_list:
        xref = img_info[0]
        if xref in seen_xrefs or xref in smask_xrefs:
            continue
        seen_xrefs.add(xref)

        try:
            base_image = doc.extract_image(xref)
        except Exception:
            continue

        if not base_image or not base_image.get("image"):
            continue

        width = base_image["width"]
        height = base_image["height"]

        if width < min_size or height < min_size:
            continue

        if min_area > 0 and width * height < min_area:
            continue

        img_idx += 1
        ext = base_image.get("ext", "png")
        if ext not in ("png", "jpg", "jpeg"):
            ext = "png"

        filename = f"{img_prefix}_p{page_num}_{img_idx:03d}.{ext}"
        filepath = images_dir / filename

        with open(filepath, "wb") as f:
            f.write(base_image["image"])

        placeholders.append(f"![IMG_{img_idx:03d}](images/{filename})")

    return placeholders


def clean_text(text):
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def process_pages(doc, page_range, img_prefix, md_path, images_dir, min_size, min_area):
    md_lines = []
    total_images = 0

    for i, page_idx in enumerate(page_range):
        page = doc[page_idx]
        page_num = page_idx + 1

        text = page.get_text()
        text = clean_text(text)

        placeholders = extract_images_from_page(
            doc, page, img_prefix, page_num, images_dir, min_size, min_area
        )
        total_images += len(placeholders)

        if i > 0:
            md_lines.append("\n---\n")

        md_lines.append(f"<!-- Page {page_num} -->\n")

        if text:
            md_lines.append(text)
            md_lines.append("")

        for ph in placeholders:
            md_lines.append(ph)
            md_lines.append("")

    content = "\n".join(md_lines)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)

    return total_images


def main():
    parser = argparse.ArgumentParser(description="PDF → Markdown 변환 (RAG용)")
    parser.add_argument("pdf", help="PDF 파일 경로")
    parser.add_argument("-o", "--output", help="출력 디렉토리")
    parser.add_argument("-s", "--split", help="분할 설정 JSON 파일")
    parser.add_argument("-p", "--prefix", help="이미지 파일명 접두어")
    parser.add_argument("--min-img-size", type=int, default=200, help="최소 이미지 크기(px)")
    parser.add_argument("--min-img-area", type=int, default=0, help="최소 이미지 면적(px)")
    args = parser.parse_args()

    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.exists():
        print(f"[오류] 파일 없음: {pdf_path}")
        return

    out_dir = Path(args.output) if args.output else pdf_path.parent / "md"
    images_dir = out_dir / "images"
    os.makedirs(images_dir, exist_ok=True)

    default_prefix = pdf_path.stem
    prefix = args.prefix or default_prefix

    doc = fitz.open(str(pdf_path))
    total_md = 0
    total_img = 0

    if args.split:
        with open(args.split, "r", encoding="utf-8") as f:
            sections = json.load(f)

        for section in sections:
            s_name = section["name"]
            s_prefix = section.get("prefix", s_name)
            md_name = f"{s_name}.md"
            md_path = out_dir / md_name
            page_range = range(section["start"], section["end"] + 1)

            print(f"  섹션: {md_name} (p{section['start']+1}~p{section['end']+1})")

            n_img = process_pages(
                doc, page_range, s_prefix, md_path, images_dir,
                args.min_img_size, args.min_img_area
            )
            total_md += 1
            total_img += n_img
            print(f"    → {len(page_range)}페이지, 이미지 {n_img}개")
    else:
        md_name = f"{prefix}.md"
        md_path = out_dir / md_name

        print(f"처리: {pdf_path.name} → {md_name}")

        n_pages = len(doc)
        n_img = process_pages(
            doc, range(n_pages), prefix, md_path, images_dir,
            args.min_img_size, args.min_img_area
        )
        total_md += 1
        total_img += n_img
        print(f"  → {n_pages}페이지, 이미지 {n_img}개")

    doc.close()

    print(f"\n=== 완료 ===")
    print(f"MD 파일: {total_md}개")
    print(f"추출 이미지: {total_img}개")
    print(f"출력 위치: {out_dir}")


if __name__ == "__main__":
    main()
