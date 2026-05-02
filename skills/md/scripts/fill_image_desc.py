#!/usr/bin/env python3
"""
fill_image_desc.py — Gemini로 이미지 설명 채우기

사용법:
  python fill_image_desc.py <md_dir> [옵션]

옵션:
  -c, --context TEXT      이미지 설명 맥락 (예: "초등학교 5학년 과학 교사용 지도서")
  -k, --api-key KEY       Gemini API 키
  -m, --model MODEL       Gemini 모델 (기본: gemini-3.1-flash-lite-preview)
  -w, --workers N         병렬 워커 수 (기본: 50)
  --min-area PX           최소 이미지 면적 (기본: 100000)
  --interval SEC          요청 간 최소 간격 (기본: 0.05)
"""

import re
import time
import json
import threading
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
import google.generativeai as genai

IMG_PATTERN = re.compile(r'^!\[IMG_\d+\]\((images/[^)]+)\)\s*$')

_last_request = 0.0
_lock = threading.Lock()


def throttle(interval):
    global _last_request
    with _lock:
        now = time.time()
        wait = interval - (now - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.time()


def load_progress(progress_file):
    if progress_file.exists():
        with open(progress_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed": {}}


def save_progress(progress, progress_file):
    with _lock:
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False)


def collect_pending(md_dir, progress, min_area):
    pending = []
    for md_path in sorted(md_dir.glob("*.md")):
        with open(md_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            match = IMG_PATTERN.match(line)
            if not match:
                continue
            img_rel = match.group(1)
            if img_rel in progress["completed"]:
                continue
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines) and lines[j].strip().startswith(">"):
                continue
            img_path = md_dir / img_rel
            if not img_path.exists():
                continue
            if min_area > 0:
                try:
                    with Image.open(img_path) as img:
                        w, h = img.size
                    if w * h < min_area:
                        continue
                except Exception:
                    continue
            pending.append({"img_rel": img_rel, "img_path": img_path})
    return pending


def describe_one(model, item, context, progress, progress_file, counter, total, interval):
    prompt = f"이 이미지는 {context}의 삽화/그림입니다. 이미지의 내용을 한국어로 상세히 설명해주세요."

    for attempt in range(5):
        throttle(interval)
        try:
            img = Image.open(item["img_path"])
            response = model.generate_content([prompt, img])
            img.close()
            desc = response.text.strip()

            with _lock:
                progress["completed"][item["img_rel"]] = desc
                counter[0] += 1
                n = counter[0]
            if n % 10 == 0:
                save_progress(progress, progress_file)
            print(f"  [{n}/{total}] {item['img_rel']}", flush=True)
            return True

        except Exception as e:
            err = str(e).lower()
            if "429" in err or "resource" in err or "quota" in err:
                wait = 5 * (2 ** attempt)
                print(f"  [제한] {item['img_rel']} → {wait}초 대기", flush=True)
                time.sleep(wait)
            else:
                print(f"  [오류] {item['img_rel']}: {e}", flush=True)
                if attempt < 4:
                    time.sleep(3)
                else:
                    return False
    return False


def insert_descriptions(md_dir, progress):
    for md_path in sorted(md_dir.glob("*.md")):
        with open(md_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        modified = False
        i = 0
        while i < len(lines):
            line = lines[i]
            new_lines.append(line)
            match = IMG_PATTERN.match(line)
            if not match:
                i += 1
                continue
            img_rel = match.group(1)
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines) and lines[j].strip().startswith(">"):
                i += 1
                continue
            if img_rel in progress["completed"]:
                desc = progress["completed"][img_rel]
                blockquote = "\n".join(f"> {dl}" for dl in desc.split("\n"))
                new_lines.append("\n")
                new_lines.append(blockquote + "\n")
                modified = True
            i += 1

        if modified:
            with open(md_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            print(f"  삽입: {md_path.name}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Gemini로 이미지 설명 채우기")
    parser.add_argument("md_dir", help="MD 파일이 있는 디렉토리")
    parser.add_argument("-c", "--context", default="문서", help="이미지 맥락 설명")
    parser.add_argument("-k", "--api-key", required=True, help="Gemini API 키")
    parser.add_argument("-m", "--model", default="gemini-3.1-flash-lite-preview", help="Gemini 모델")
    parser.add_argument("-w", "--workers", type=int, default=50, help="병렬 워커 수")
    parser.add_argument("--min-area", type=int, default=100000, help="최소 이미지 면적(px)")
    parser.add_argument("--interval", type=float, default=0.05, help="요청 간 최소 간격(초)")
    args = parser.parse_args()

    md_dir = Path(args.md_dir).resolve()
    progress_file = md_dir / "image_desc_progress.json"

    genai.configure(api_key=args.api_key)
    model = genai.GenerativeModel(args.model)

    progress = load_progress(progress_file)
    before = len(progress["completed"])
    print(f"이전 진행: {before}개\n", flush=True)

    pending = collect_pending(md_dir, progress, args.min_area)
    print(f"대기: {len(pending)}개\n", flush=True)

    if pending:
        total = len(pending)
        counter = [0]

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [
                executor.submit(
                    describe_one, model, item, args.context,
                    progress, progress_file, counter, total, args.interval
                )
                for item in pending
            ]
            for f in as_completed(futures):
                pass

        save_progress(progress, progress_file)

    print(flush=True)
    insert_descriptions(md_dir, progress)

    total = len(progress["completed"])
    print(f"\n=== 완료 ===")
    print(f"총 설명: {total}개 (+{total - before})", flush=True)


if __name__ == "__main__":
    main()
