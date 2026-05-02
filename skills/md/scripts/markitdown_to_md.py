#!/usr/bin/env python3
"""
markitdown_to_md.py — MarkItDown 기반 추가 포맷 변환

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
import shutil
import subprocess
import tempfile
import warnings
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

try:
    from markitdown import MarkItDown
    HAS_MARKITDOWN = True
except ImportError:
    HAS_MARKITDOWN = False

AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.wma'}

# Gemini CLI @-reference 인라인 크기 제한(실측 ~20MB). 안전 마진을 두고 19MB.
GEMINI_INLINE_SIZE_LIMIT = 19 * 1024 * 1024

# 큰 오디오를 전사용으로 재인코딩할 때 사용할 비트레이트(음성이면 16kbps mono면 충분).
AUDIO_REENCODE_BITRATE = '24k'
AUDIO_REENCODE_SAMPLERATE = '16000'

# 전사 결과가 사실상 거부 메시지인지 판정할 때 쓰는 패턴.
# Gemini가 파일을 못 읽었을 때 이런 문구를 돌려준다 — 그 결과를 MD로 저장하지 않기 위함.
REFUSAL_PATTERNS = [
    '파일 읽기 제한',
    '분할하거나 압축',
    '크기를 초과',
    '20MB',
    '파일이 너무 큽니다',
]

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


def prepare_audio_for_gemini(path: Path):
    """Gemini CLI @-reference 인라인 크기 제한(~20MB)을 우회하기 위해,
    19MB를 넘는 오디오는 ffmpeg로 mono 저비트레이트 m4a로 재인코딩해 임시 경로를 반환한다.

    반환: (사용할 경로, 정리 대상 임시 디렉토리 또는 None)
    """
    size = path.stat().st_size
    if size <= GEMINI_INLINE_SIZE_LIMIT:
        return path, None

    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        print(f"  [경고] 오디오 {size/1024/1024:.1f}MB > 19MB 이지만 ffmpeg 미설치. 원본으로 진행(실패 가능).")
        return path, None

    tmpdir = Path(tempfile.mkdtemp(prefix='audio_prep_'))
    out = tmpdir / f"{path.stem}.m4a"
    print(f"  오디오 {size/1024/1024:.1f}MB > 19MB. ffmpeg로 mono {AUDIO_REENCODE_BITRATE} 재인코딩 중...")
    cmd = [
        ffmpeg, '-y', '-i', str(path),
        '-vn', '-ac', '1', '-ar', AUDIO_REENCODE_SAMPLERATE,
        '-c:a', 'aac', '-b:a', AUDIO_REENCODE_BITRATE,
        str(out),
    ]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0 or not out.exists():
        err = (r.stderr or b'').decode('utf-8', errors='replace')[:300]
        print(f"  [경고] ffmpeg 재인코딩 실패: {err}. 원본으로 진행.")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return path, None

    new_size = out.stat().st_size
    print(f"  재인코딩 완료: {new_size/1024/1024:.2f}MB → {out.name}")
    return out, tmpdir


def looks_like_refusal(text: str) -> bool:
    """Gemini가 파일을 못 읽고 거부 메시지를 돌려준 경우 감지."""
    hit = sum(1 for p in REFUSAL_PATTERNS if p in text)
    # 2개 이상 매칭 또는 전체 길이가 짧은데 1개라도 매칭되면 refusal.
    return hit >= 2 or (hit >= 1 and len(text) < 2000)


def transcribe_audio(file_path, language='ko', model=None):
    """gemini -p 헤드리스 모드로 오디오 파일 음성인식."""
    gemini = shutil.which('gemini')
    if not gemini:
        print("  [오류] gemini CLI 미설치. 설치: npm i -g @google/gemini-cli")
        return None

    abs_path = str(Path(file_path).resolve()).replace('\\', '/')
    lang_label = {'ko': '한국어', 'en': '영어', 'ja': '일본어'}.get(language, language)
    prompt = (
        f"@{abs_path}\n"
        f"이 오디오 파일을 {lang_label}로 전사해줘. "
        "가능하면 [MM:SS] 타임스탬프와 화자 구분(**A:**, **B:** 등)을 포함하라. "
        "에이전트 추론 로그(계획·사고 과정)와 전사 뒤 요약 코멘트도 제거하지 말고 그대로 남겨라 — 메타정보로 활용한다."
    )

    print(f"  gemini -p 전사 중... (언어: {language})")
    env = os.environ.copy()
    env.pop('CLAUDECODE', None)

    cmd = [gemini, '-p', prompt, '-o', 'text', '-y']
    if model:
        cmd += ['-m', model]

    try:
        # stdin=DEVNULL: gemini가 OAuth 로그인 프롬프트 대기로 hang되는 것을 방지 (즉시 EOF → 실패)
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding='utf-8',
            errors='replace', env=env, timeout=60 * 60,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        print("  [오류] gemini 전사 타임아웃 (1시간 초과)")
        return None

    if proc.returncode != 0:
        err = (proc.stderr or '').strip()[:500]
        print(f"  [오류] gemini 전사 실패 (exit {proc.returncode}): {err}")
        return None

    text = (proc.stdout or '').strip()
    if not text:
        print("  [경고] gemini 전사 결과가 비어 있음")
        return None
    if looks_like_refusal(text):
        print(f"  [오류] gemini가 파일을 처리 못했음(거부 응답). 발췌: {text[:200]}")
        return None
    return f"### Audio Transcript\n\n{text}"


def convert_single(md, source, out_dir, language='ko', gemini_model=None):
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

    if not is_url and path.suffix.lower() in AUDIO_EXTENSIONS:
        prep_path, prep_tmp = prepare_audio_for_gemini(path)
        try:
            text = transcribe_audio(prep_path, language=language, model=gemini_model)
        except Exception as e:
            print(f"  [오류] gemini 전사: {type(e).__name__}: {str(e)[:300]}")
            text = None
        finally:
            if prep_tmp:
                shutil.rmtree(prep_tmp, ignore_errors=True)
    else:
        try:
            result = md.convert(source if is_url else str(path))
            text = result.text_content or ""
        except Exception as e:
            print(f"  [오류] {type(e).__name__}: {str(e)[:300]}")
            return None

    if not text.strip():
        print(f"  [경고] 빈 결과 (텍스트 없음)")
        return None

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
        description="MarkItDown 기반 추가 포맷 → Markdown 변환"
    )
    parser.add_argument("sources", nargs='+', help="파일 경로 또는 YouTube URL")
    parser.add_argument("-o", "--output", help="출력 디렉토리")
    parser.add_argument("--gemini-model", default=None, help="Gemini 모델 (기본: CLI 기본값)")
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
                                language=args.language,
                                gemini_model=args.gemini_model)
        if result:
            results.append(result)

    print(f"\n=== 완료 ===")
    print(f"변환 성공: {len(results)}/{len(args.sources)}개")
    print(f"출력 위치: {out_dir}")


if __name__ == "__main__":
    main()
