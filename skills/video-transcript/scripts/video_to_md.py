#!/usr/bin/env python3
"""
yt-dlp 자동 자막(또는 업로드된 자막)을 받아서 마크다운으로 저장.

사용법:
    python video_to_md.py "https://youtube.com/watch?v=..." -o out.md -l ko
    python video_to_md.py "https://youtube.com/watch?v=..." --no-llm
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


def is_url(source: str) -> bool:
    try:
        return urlparse(source).scheme in ("http", "https")
    except Exception:
        return False


def check_deps():
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        print("ERROR: yt-dlp 미설치 — pip install yt-dlp", file=sys.stderr)
        sys.exit(1)


def get_video_title(url: str) -> str:
    import yt_dlp

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("title", "Untitled")
    except Exception as e:
        print(f"WARNING: 제목 추출 실패: {e}", file=sys.stderr)
        return "Untitled"


def download_subs(url: str, out_dir: str, lang: str) -> tuple[str | None, str]:
    """Return (subtitle_file_path, title). Try auto-captions first."""
    import yt_dlp

    title = get_video_title(url)
    langs = [lang] if lang else ["ko", "ko-KR", "en", "en-US", "ja"]

    base = os.path.join(out_dir, "subs")
    common = {
        "skip_download": True,
        "subtitlesformat": "vtt",
        "subtitleslangs": langs,
        "outtmpl": base,
        "quiet": True,
        "no_warnings": True,
    }

    # 1) 업로드된 자막
    with yt_dlp.YoutubeDL({**common, "writesubtitles": True}) as ydl:
        try:
            ydl.download([url])
        except Exception:
            pass

    # 2) 자동 생성 자막 (fallback)
    for f in os.listdir(out_dir):
        if f.endswith(".vtt"):
            return os.path.join(out_dir, f), title

    with yt_dlp.YoutubeDL({**common, "writeautomaticsub": True}) as ydl:
        ydl.download([url])

    for f in os.listdir(out_dir):
        if f.endswith(".vtt"):
            return os.path.join(out_dir, f), title

    return None, title


def vtt_to_text(vtt_path: str) -> str:
    with open(vtt_path, encoding="utf-8") as f:
        raw = f.read()
    lines = []
    seen = set()
    for line in raw.split("\n"):
        line = line.strip()
        if (
            not line
            or "-->" in line
            or line.startswith("WEBVTT")
            or line.startswith("Kind:")
            or line.startswith("Language:")
            or line.startswith("NOTE")
        ):
            continue
        clean = re.sub(r"<[^>]+>", "", line)
        clean = re.sub(r"&nbsp;", " ", clean).strip()
        if clean and clean not in seen:
            seen.add(clean)
            lines.append(clean)
    return " ".join(lines)


def sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def structure_with_llm(raw_text: str, title: str) -> str:
    import requests

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        keyfile = Path.home() / ".claude" / "apikeys" / "claude"
        if keyfile.exists():
            api_key = keyfile.read_text(encoding="utf-8").strip()
    if not api_key:
        print("WARNING: Claude API 키 없음, 원본 텍스트 유지", file=sys.stderr)
        return raw_text

    prompt = f"""다음은 '{title}' 영상의 자막 텍스트입니다. 검색·요약용 마크다운으로 구조화해주세요.

요구사항:
1. 논리적 섹션과 헤딩(##, ###) 부여
2. 핵심 개념은 **굵게**
3. 목록은 불릿 포인트
4. 섹션당 200-500자
5. 오탈자·어색한 표현은 자연스럽게 수정 (원본 의미 보존)
6. 맨 아래 '## 핵심 키워드' 섹션 추가 (5-10개)

원본:
{raw_text}

구조화된 마크다운:"""

    try:
        print("LLM으로 구조화 중...", file=sys.stderr)
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-5",
                "max_tokens": 8000,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=180,
        )
        if r.status_code == 200:
            return r.json()["content"][0]["text"]
        print(f"WARNING: LLM 실패 ({r.status_code})", file=sys.stderr)
    except Exception as e:
        print(f"WARNING: LLM 오류: {e}", file=sys.stderr)
    return raw_text


def generate_markdown(
    text: str, source: str, title: str, language: str, use_llm: bool
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = structure_with_llm(text, title) if use_llm else text
    return f"""---
source: {source}
title: {title}
created: {now}
language: {language}
type: video-transcript
---

# {title}

{body}
"""


def main():
    ap = argparse.ArgumentParser(description="YouTube 자막을 마크다운으로 저장")
    ap.add_argument("source", help="URL (로컬 파일 미지원 — 자막 기반 스킬)")
    ap.add_argument("-o", "--output", help="출력 마크다운 경로")
    ap.add_argument("-l", "--language", default="", help="자막 언어 (ko/en 등)")
    ap.add_argument(
        "--no-llm", action="store_true", help="LLM 구조화 비활성화"
    )
    args = ap.parse_args()

    check_deps()

    if not is_url(args.source):
        print(
            "ERROR: 이 스킬은 YouTube 등 자막이 있는 URL만 지원합니다.",
            file=sys.stderr,
        )
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmp:
        vtt_path, title = download_subs(args.source, tmp, args.language)
        if not vtt_path:
            print(
                "ERROR: 자막을 찾지 못했습니다 (자동 자막·업로드 자막 모두 없음).",
                file=sys.stderr,
            )
            sys.exit(2)

        text = vtt_to_text(vtt_path)
        if not text.strip():
            print("ERROR: 자막 파싱 결과가 비어 있음.", file=sys.stderr)
            sys.exit(3)

        lang_guess = args.language or (
            "ko" if re.search(r"[가-힣]", text) else "unknown"
        )

        md = generate_markdown(
            text=text,
            source=args.source,
            title=title,
            language=lang_guess,
            use_llm=not args.no_llm,
        )

        if args.output:
            out_path = args.output
        else:
            out_path = f"{sanitize_filename(title)}.md"

        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)

        print(f"\n완료: {out_path}", file=sys.stderr)
        print(f"언어: {lang_guess}  길이: {len(text)} 문자", file=sys.stderr)
        print(out_path)


if __name__ == "__main__":
    main()
