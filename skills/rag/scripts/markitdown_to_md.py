#!/usr/bin/env python3
"""
markitdown_to_md.py — MarkItDown 기반 추가 포맷 변환 (RAG용)

지원 포맷: PPTX, XLSX, CSV, HTML, JSON, XML, WAV, MP3, YouTube URL
기존 pdf_to_md.py, doc_to_md.py가 처리하지 않는 포맷을 담당.

사용법:
  python markitdown_to_md.py <file_or_url> [옵션]
  python markitdown_to_md.py <file1> <file2> ... -o <output_dir>

옵션:
  -o, --output DIR    출력 디렉토리 (기본: 파일과 같은 위치에 md/)
"""

import sys
import os
import argparse
import warnings
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

try:
    from markitdown import MarkItDown
    HAS_MARKITDOWN = True
except ImportError:
    HAS_MARKITDOWN = False

try:
    import whisper
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.wma'}

SUPPORTED_EXTENSIONS = {
    '.pptx', '.xlsx', '.xls', '.csv',
    '.html', '.htm',
    '.json', '.xml',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
    '.epub', '.zip',
} | AUDIO_EXTENSIONS


def is_youtube_url(source):
    """YouTube URL인지 판별."""
    return any(k in source for k in ['youtube.com/', 'youtu.be/'])


def transcribe_audio(file_path, model_name='turbo', language='ko'):
    """Whisper turbo로 오디오 파일 음성인식."""
    if not HAS_WHISPER:
        print("  [오류] whisper 미설치. 설치: pip install openai-whisper")
        return None

    print(f"  Whisper {model_name} 모델 로딩 중...")
    model = whisper.load_model(model_name)
    print(f"  음성인식 중... (언어: {language})")
    result = model.transcribe(str(file_path), language=language)

    segments = result.get('segments', [])
    lines = [f"### Audio Transcript\n"]
    for seg in segments:
        start = seg['start']
        m, s = int(start // 60), int(start % 60)
        text = seg['text'].strip()
        lines.append(f"[{m:02d}:{s:02d}] {text}")

    return "\n".join(lines)


def convert_single(md, source, out_dir, whisper_model='turbo', language='ko'):
    """단일 파일 또는 URL을 마크다운으로 변환."""
    is_url = source.startswith('http://') or source.startswith('https://')

    if is_url:
        name = "youtube" if is_youtube_url(source) else "web"
        label = source
    else:
        path = Path(source).resolve()
        if not path.exists():
            print(f"  [오류] 파일 없음: {path}")
            return None
        name = path.stem
        label = path.name
        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            print(f"  [오류] 미지원 확장자: {ext}")
            print(f"  지원: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
            return None

    print(f"  변환 중: {label}")

    # 오디오 파일은 Whisper turbo로 처리
    if not is_url and path.suffix.lower() in AUDIO_EXTENSIONS:
        try:
            text = transcribe_audio(path, model_name=whisper_model, language=language)
        except Exception as e:
            print(f"  [오류] Whisper: {type(e).__name__}: {str(e)[:300]}")
            return None
    else:
        try:
            result = md.convert(source if is_url else str(Path(source).resolve()))
            text = result.text_content or ""
        except Exception as e:
            print(f"  [오류] {type(e).__name__}: {str(e)[:300]}")
            return None

    if not text.strip():
        print(f"  [경고] 빈 결과 (텍스트 없음)")
        return None

    # 파일명 안전하게
    safe_name = "".join(c if c.isalnum() or c in '-_. 가-힣' else '_' for c in name)
    # 한글 허용을 위해 더 넓은 범위
    safe_name = name.replace('/', '_').replace('\\', '_').replace(':', '_')
    md_path = out_dir / f"{safe_name}.md"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"  → {md_path.name} ({len(text)} 글자)")
    return md_path


def main():
    if not HAS_MARKITDOWN:
        print("[오류] markitdown 미설치. 설치: pip install 'markitdown[all]'")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="MarkItDown 기반 추가 포맷 → Markdown 변환 (RAG용)"
    )
    parser.add_argument("sources", nargs='+', help="파일 경로 또는 YouTube URL")
    parser.add_argument("-o", "--output", help="출력 디렉토리")
    parser.add_argument("--whisper-model", default="turbo", help="Whisper 모델 (기본: turbo)")
    parser.add_argument("--language", default="ko", help="오디오 언어 (기본: ko)")
    args = parser.parse_args()

    # 출력 디렉토리 결정
    if args.output:
        out_dir = Path(args.output)
    else:
        first = args.sources[0]
        if first.startswith('http'):
            out_dir = Path.cwd() / "md"
        else:
            out_dir = Path(first).resolve().parent / "md"
    os.makedirs(out_dir, exist_ok=True)

    md = MarkItDown()
    results = []

    for source in args.sources:
        result = convert_single(md, source, out_dir,
                                whisper_model=args.whisper_model,
                                language=args.language)
        if result:
            results.append(result)

    print(f"\n=== 완료 ===")
    print(f"변환 성공: {len(results)}/{len(args.sources)}개")
    print(f"출력 위치: {out_dir}")


if __name__ == "__main__":
    main()
