#!/usr/bin/env python3
"""
fill_image_desc_claude.py — Claude CLI로 이미지 설명 채우기 (Gemini 대체)

Max 요금제 사용자용. claude -p 파이프 모드로 이미지 인식을 병렬 처리.
API 비용 0원 (Max 구독에 포함).

사용법:
  python fill_image_desc_claude.py <md_dir> [옵션]

옵션:
  -c, --context TEXT      이미지 설명 맥락 (예: "초등학교 5학년 과학 교사용 지도서")
  -w, --workers N         병렬 워커 수 (기본: 5, Max 요금제 rate limit 고려)
  --min-area PX           최소 이미지 면적 (기본: 100000)
  --model MODEL           Claude 모델 (기본: haiku, 빠르고 이미지 설명에 충분)
"""

import os
import re
import json
import asyncio
import argparse
import sys
from pathlib import Path
from PIL import Image

IMG_PATTERN = re.compile(r'^!\[IMG_\d+\]\((images/.+\.(?:png|jpe?g|gif|bmp|webp))\)\s*$', re.IGNORECASE)


def load_progress(progress_file):
    if progress_file.exists():
        with open(progress_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed": {}}


def save_progress(progress, progress_file):
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
            pending.append({"img_rel": img_rel, "img_path": str(img_path.resolve())})
    return pending


def ensure_thumb(img_path_str, thumb_size):
    """원본 이미지의 긴 변을 thumb_size로 리사이즈한 썸네일을 반환.
    원본이 이미 작으면 원본 경로를 그대로 반환."""
    if thumb_size <= 0:
        return img_path_str
    src = Path(img_path_str)
    try:
        with Image.open(src) as im:
            w, h = im.size
            long_side = max(w, h)
            if long_side <= thumb_size:
                return img_path_str
            thumb_dir = src.parent / "_thumb"
            thumb_dir.mkdir(exist_ok=True)
            dst = thumb_dir / src.name
            if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
                return str(dst.resolve())
            scale = thumb_size / long_side
            new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
            im2 = im.convert("RGB") if im.mode not in ("RGB", "RGBA", "L") else im
            im2.thumbnail(new_size, Image.LANCZOS)
            save_kwargs = {}
            if dst.suffix.lower() in (".jpg", ".jpeg"):
                save_kwargs["quality"] = 85
                save_kwargs["optimize"] = True
            im2.save(dst, **save_kwargs)
            return str(dst.resolve())
    except Exception:
        return img_path_str


async def describe_one(sem, item, context, model, counter, total, thumb_size):
    """claude -p로 이미지 하나 설명"""
    img_path = await asyncio.to_thread(ensure_thumb, item["img_path"], thumb_size)
    prompt = (
        f"Read the image file at '{img_path}' using the Read tool. "
        f"This image is from {context}. "
        f"Describe the content of this image in Korean in detail. "
        f"Output ONLY the description text, nothing else. No prefixes, no quotes."
    )

    env = {**os.environ}
    env.pop("CLAUDECODE", None)  # 중첩 세션 방지 해제

    async with sem:
        for attempt in range(3):
            try:
                proc = await asyncio.create_subprocess_exec(
                    "claude", "-p", prompt,
                    "--allowedTools", "Read",
                    "--permission-mode", "bypassPermissions",
                    "--model", model,
                    "--no-session-persistence",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=120
                )

                if proc.returncode == 0:
                    desc = stdout.decode("utf-8", errors="replace").strip()
                    if desc:
                        counter[0] += 1
                        n = counter[0]
                        if n % 5 == 0 or n == total:
                            print(f"  [{n}/{total}] {item['img_rel']}", flush=True)
                        return item["img_rel"], desc

                err_msg = stderr.decode("utf-8", errors="replace").strip()
                if "rate" in err_msg.lower() or "overloaded" in err_msg.lower():
                    wait = 10 * (2 ** attempt)
                    print(f"  [제한] {item['img_rel']} → {wait}초 대기", flush=True)
                    await asyncio.sleep(wait)
                else:
                    print(f"  [오류] {item['img_rel']}: {err_msg[:100]}", flush=True)
                    await asyncio.sleep(3)

            except asyncio.TimeoutError:
                print(f"  [타임아웃] {item['img_rel']} (시도 {attempt+1})", flush=True)
            except Exception as e:
                print(f"  [예외] {item['img_rel']}: {e}", flush=True)
                await asyncio.sleep(3)

    return item["img_rel"], None


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


async def main_async(args):
    md_dir = Path(args.md_dir).resolve()
    progress_file = md_dir / "image_desc_progress.json"

    progress = load_progress(progress_file)
    before = len(progress["completed"])
    print(f"이전 진행: {before}개", flush=True)

    pending = collect_pending(md_dir, progress, args.min_area)
    print(f"대기: {len(pending)}개", flush=True)

    if not pending:
        print("처리할 이미지가 없습니다.", flush=True)
        return

    total = len(pending)
    counter = [0]
    sem = asyncio.Semaphore(args.workers)

    # 배치로 나눠서 처리 (중간 저장)
    batch_size = args.workers * 3
    for batch_start in range(0, total, batch_size):
        batch = pending[batch_start:batch_start + batch_size]
        tasks = [
            describe_one(sem, item, args.context, args.model, counter, total, args.thumb_size)
            for item in batch
        ]
        results = await asyncio.gather(*tasks)

        for img_rel, desc in results:
            if desc:
                progress["completed"][img_rel] = desc

        save_progress(progress, progress_file)
        print(f"  --- 배치 저장 ({len(progress['completed'])}개) ---", flush=True)

    insert_descriptions(md_dir, progress)

    total_done = len(progress["completed"])
    print(f"\n=== 완료 ===")
    print(f"총 설명: {total_done}개 (+{total_done - before})", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Claude CLI로 이미지 설명 채우기")
    parser.add_argument("md_dir", help="MD 파일이 있는 디렉토리")
    parser.add_argument("-c", "--context", default="문서", help="이미지 맥락 설명")
    parser.add_argument("-w", "--workers", type=int, default=10,
                        help="병렬 워커 수 (기본: 10, Max 요금제 rate limit 고려)")
    parser.add_argument("--min-area", type=int, default=100000,
                        help="최소 이미지 면적(px)")
    parser.add_argument("--model", default="sonnet",
                        help="Claude 모델 (기본: sonnet)")
    parser.add_argument("--thumb-size", type=int, default=1024,
                        help="썸네일 긴변 픽셀 (기본: 1024, 0이면 리사이즈 안함)")

    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
