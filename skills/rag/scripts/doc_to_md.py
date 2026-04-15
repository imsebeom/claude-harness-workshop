#!/usr/bin/env python3
"""
doc_to_md.py — HWP/HWPX/DOCX → Markdown 변환 (RAG용)

사용법:
  python doc_to_md.py <file_path> [옵션]

옵션:
  -o, --output DIR    출력 디렉토리 (기본: 파일과 같은 위치에 md/)

지원 형식: .hwp, .hwpx, .docx
- .hwp : Windows + 한컴 오피스 COM (HWPFrame.HwpObject) → .hwpx 임시 변환
- .hwpx: LibreOffice → .docx 임시 변환
- .docx: python-docx 직접 처리
"""

import os
import re
import sys
import subprocess
import argparse
import zipfile
import shutil
from pathlib import Path

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


def _find_soffice() -> str:
    candidates = [
        "C:/Program Files/LibreOffice/program/soffice.exe",
        "C:/Program Files (x86)/LibreOffice/program/soffice.exe",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "soffice",
    ]
    for c in candidates:
        if Path(c).exists() or shutil.which(c):
            return c
    return "soffice"


SOFFICE = _find_soffice()


def hancom_save_as(src_path: Path, target_path: Path, fmt: str) -> Path:
    """한컴 오피스 COM으로 src_path를 fmt 형식으로 SaveAs.

    fmt 예: "HWPX", "MSWord" (.docx), "PDF", "HTML"
    """
    if sys.platform != "win32":
        raise RuntimeError(
            "한컴 COM 변환은 Windows에서만 지원된다."
        )
    try:
        import pythoncom
        import win32com.client as win32
    except ImportError as exc:
        raise RuntimeError(
            "한컴 COM 변환에는 pywin32가 필요하다: pip install pywin32"
        ) from exc

    if target_path.exists() and target_path.stat().st_size > 0:
        return target_path

    pythoncom.CoInitialize()
    hwp = None
    try:
        hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
        try:
            hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
        except Exception:
            pass
        hwp.Open(str(src_path))
        hwp.SaveAs(str(target_path), fmt)
        hwp.Run("FileClose")
    except Exception as exc:
        raise RuntimeError(
            f"한컴 COM SaveAs 실패 ({src_path.suffix} → {fmt}): {exc}. "
            "한컴 오피스 설치 및 COM 자동화 활성화 여부를 확인하라."
        ) from exc
    finally:
        try:
            if hwp is not None:
                hwp.Quit()
        except Exception:
            pass
        pythoncom.CoUninitialize()

    if not target_path.exists() or target_path.stat().st_size == 0:
        raise RuntimeError(f"한컴 COM 변환 후 출력 파일이 없다: {target_path}")
    return target_path


def hwp_to_md(file_path: Path, out_dir: Path):
    """HWP → MD: 두 경로 중 하나로 변환한다.

    1차(기본): 한컴 COM으로 .hwpx 임시 변환 → 순수 파이썬 hwpx 파서
      - Windows + 한컴 오피스 설치 필요
      - 표, 이미지, 서식 보존이 가장 좋음

    2차(폴백): pyhwp(순수 파이썬)로 직접 텍스트 추출
      - 어느 OS에서도 동작 (한컴·LibreOffice 무관)
      - 표는 `<표>` 플레이스홀더로 남고, 이미지·서식은 손실됨
      - 설치: pip install pyhwp

    강제 override: 환경변수 RAG_DOC_BACKEND=pyhwp 또는 =hancom
    """
    backend = os.environ.get("RAG_DOC_BACKEND", "").strip().lower()

    # 강제 pyhwp 선택
    if backend == "pyhwp":
        return _hwp_to_md_via_pyhwp(file_path, out_dir)

    # 강제 한컴 선택 또는 기본(한컴 우선)
    if backend in ("hancom", ""):
        try:
            return _hwp_to_md_via_hancom(file_path, out_dir)
        except Exception as exc:
            if backend == "hancom":
                raise
            # 기본 경로: 한컴 실패 시 pyhwp 폴백
            print(
                f"[hwp_to_md] 한컴 COM 경로 실패({type(exc).__name__}), "
                f"pyhwp 폴백으로 전환",
                file=sys.stderr,
            )
            return _hwp_to_md_via_pyhwp(file_path, out_dir)

    raise RuntimeError(
        f"알 수 없는 RAG_DOC_BACKEND='{backend}'. "
        "'hancom' 또는 'pyhwp' 중 하나를 쓰거나 비워 두어라."
    )


def _hwp_to_md_via_hancom(file_path: Path, out_dir: Path):
    """한컴 COM 경로: .hwp → .hwpx → hwpx_pure_to_md."""
    temp_dir = out_dir / "_temp"
    os.makedirs(temp_dir, exist_ok=True)
    try:
        hwpx_path = temp_dir / (file_path.stem + ".hwpx")
        hancom_save_as(file_path, hwpx_path, "HWPX")
        return hwpx_pure_to_md(hwpx_path, out_dir, original_stem=file_path.stem)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _hwp_to_md_via_pyhwp(file_path: Path, out_dir: Path):
    """pyhwp 경로: 순수 파이썬으로 .hwp → 텍스트 → 마크다운.

    한컴·LibreOffice가 없어도 동작. 다만 다음 한계가 있다.
    - 표는 ``<표>`` 플레이스홀더로 표시됨 (본문 구조는 유지)
    - 임베디드 이미지는 추출되지 않음
    - 굵게·기울임 등 서식은 손실됨

    pyhwp 설치 필요: pip install pyhwp
    """
    try:
        from contextlib import closing
        import io
        from hwp5.hwp5txt import TextTransform
        from hwp5.xmlmodel import Hwp5File
    except ImportError as exc:
        raise RuntimeError(
            ".hwp 변환에 pyhwp가 필요한데 설치되어 있지 않다. "
            "다음을 실행: pip install pyhwp"
        ) from exc

    stem = file_path.stem
    md_path = out_dir / f"{stem}.md"
    os.makedirs(out_dir, exist_ok=True)

    with closing(Hwp5File(str(file_path))) as hwp5:
        buf = io.BytesIO()
        TextTransform().transform_hwp5_to_text(hwp5, buf)
        text = buf.getvalue().decode("utf-8", errors="replace")

    # 텍스트 → 마크다운: 간단한 정리
    lines = [line.rstrip() for line in text.splitlines()]
    # 연속 공백 줄 정리 (3줄 이상 → 2줄)
    cleaned = []
    blank_run = 0
    for line in lines:
        if not line.strip():
            blank_run += 1
            if blank_run <= 2:
                cleaned.append("")
        else:
            blank_run = 0
            cleaned.append(line)

    md_lines = [f"# {stem}", "", *cleaned, "", "---", "", "> pyhwp 폴백으로 변환됨 (한컴 미사용). 표·이미지·서식 일부가 누락될 수 있음."]
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return md_path


def hwpx_pure_to_md(hwpx_path: Path, out_dir: Path, original_stem: str | None = None):
    """HWPX → MD: zipfile + ElementTree 기반 순수 파이썬 변환.

    Contents/sectionN.xml에서 단락/표/수식/이미지 참조를 추출하고,
    BinData/ 폴더의 이미지를 out_dir/images/로 복사한다.
    참고: github.com/llA1ll/markitdown_hwpx _hwpx_converter.py
    """
    import re as _re
    import zipfile as _zip
    from xml.etree import ElementTree as ET

    stem = original_stem or hwpx_path.stem
    images_dir = out_dir / "images"
    os.makedirs(images_dir, exist_ok=True)

    def tag_name(node):
        t = getattr(node, "tag", "")
        return t.split("}", 1)[1] if "}" in t else t

    def normalize(text: str) -> str:
        return _re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()

    def join_inline(parts):
        return normalize(" ".join(parts))

    def table_to_md(tbl):
        rows = []
        for tr in list(tbl):
            if tag_name(tr) != "tr":
                continue
            row = []
            for tc in list(tr):
                if tag_name(tc) != "tc":
                    continue
                cell = []
                for sub in tc.iter():
                    name = tag_name(sub)
                    if name == "t":
                        text = normalize(sub.text or "")
                        if text:
                            cell.append(text)
                    elif name == "script":
                        s = normalize(sub.text or "")
                        if s:
                            cell.append(f"${s}$")
                row.append(join_inline(cell))
            if any(c.strip() for c in row):
                rows.append(row)
        if not rows:
            return ""
        cols = max(len(r) for r in rows)
        rows = [r + [""] * (cols - len(r)) for r in rows]
        header = rows[0]
        sep = ["---"] * cols
        lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(sep) + " |",
        ]
        lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
        return "\n".join(lines)

    def paragraph_to_md(p, image_counter):
        inline = []
        block_lines = []
        for node in p.iter():
            name = tag_name(node)
            if name == "t":
                text = normalize(node.text or "")
                if text:
                    inline.append(text)
            elif name == "script":
                s = normalize(node.text or "")
                if s:
                    inline.append(f"${s}$")
            elif name == "img":
                ref = (
                    node.attrib.get("binaryItemIDRef")
                    or node.attrib.get("{http://www.hancom.co.kr/hwpml/2011/ctrl}binaryItemIDRef")
                    or ""
                ).strip()
                if ref:
                    image_counter[0] += 1
                    inline.append(f"![IMG_{image_counter[0]:03d}](__IMGREF__{ref})")
            elif name == "tbl":
                if inline:
                    block_lines.append(join_inline(inline))
                    inline = []
                tmd = table_to_md(node)
                if tmd:
                    block_lines.append(tmd)
        if inline:
            block_lines.append(join_inline(inline))
        return [ln for ln in block_lines if ln.strip()]

    md_chunks = []
    image_refs = {}
    image_counter = [0]

    with _zip.ZipFile(str(hwpx_path)) as archive:
        sections = sorted(
            [n for n in archive.namelist()
             if n.lower().startswith("contents/section") and n.lower().endswith(".xml")],
            key=lambda n: int(_re.search(r"section(\d+)\.xml$", n.lower()).group(1))
            if _re.search(r"section(\d+)\.xml$", n.lower()) else 10**9,
        )
        for sec in sections:
            root = ET.fromstring(archive.read(sec))
            visited = set()
            for p in root.iter():
                if id(p) in visited:
                    continue
                if not tag_name(p).endswith("p"):
                    continue
                lines = paragraph_to_md(p, image_counter)
                if lines:
                    md_chunks.extend(lines)
                    md_chunks.append("")
                for descendant in p.iter():
                    visited.add(id(descendant))

        for name in archive.namelist():
            if name.startswith("BinData/"):
                base = Path(name).name
                ext = Path(name).suffix.lower()
                if ext not in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp"):
                    continue
                ref_id = Path(name).stem
                out_name = f"{stem}_{ref_id}{ext}"
                with archive.open(name) as src, open(images_dir / out_name, "wb") as dst:
                    dst.write(src.read())
                image_refs[ref_id] = out_name
                image_refs[base] = out_name

    content = "\n".join(md_chunks)

    def resolve_ref(m):
        ref = m.group(1)
        if ref in image_refs:
            return f"images/{image_refs[ref]}"
        for k, v in image_refs.items():
            if k.endswith(ref) or ref.endswith(k):
                return f"images/{v}"
        return f"images/{ref}"

    content = _re.sub(r"__IMGREF__([^\)]+)", resolve_ref, content)
    content = _re.sub(r"\n{3,}", "\n\n", content).strip()

    md_path = out_dir / f"{stem}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)

    extracted = len({v for v in image_refs.values()})
    print(f"  → {md_path.name} (이미지 {extracted}개, 순수 hwpx 파서)")
    return md_path


def hwpx_to_md(file_path, out_dir):
    """HWPX → MD: 우선 순수 파이썬 파서를 시도, 실패 시 LibreOffice 폴백."""
    try:
        return hwpx_pure_to_md(Path(file_path), out_dir)
    except Exception as exc:
        print(f"  [경고] 순수 hwpx 파서 실패, LibreOffice 폴백 시도: {exc}")

    temp_dir = out_dir / "_temp"
    os.makedirs(temp_dir, exist_ok=True)

    # LibreOffice로 DOCX 변환
    subprocess.run([
        SOFFICE, "--headless", "--convert-to", "docx",
        "--outdir", str(temp_dir), str(file_path)
    ], check=True, capture_output=True)

    docx_path = temp_dir / (file_path.stem + ".docx")
    if not docx_path.exists():
        print(f"[오류] LibreOffice 변환 실패: {file_path}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None

    result = docx_to_md(docx_path, out_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)
    return result


def docx_to_md(file_path, out_dir):
    """DOCX → MD: python-docx로 텍스트 추출 + 이미지 추출."""
    if not HAS_DOCX:
        # python-docx 없으면 LibreOffice로 텍스트 추출
        return docx_to_md_libreoffice(file_path, out_dir)

    images_dir = out_dir / "images"
    os.makedirs(images_dir, exist_ok=True)

    doc = Document(str(file_path))
    md_lines = []
    img_idx = 0

    # 이미지 추출 (ZIP 내 media 폴더)
    image_map = {}
    with zipfile.ZipFile(str(file_path), "r") as z:
        for name in z.namelist():
            if name.startswith("word/media/"):
                ext = Path(name).suffix
                if ext.lower() in (".png", ".jpg", ".jpeg", ".gif", ".bmp"):
                    img_idx += 1
                    out_name = f"{file_path.stem}_{img_idx:03d}{ext}"
                    with z.open(name) as src, open(images_dir / out_name, "wb") as dst:
                        dst.write(src.read())
                    image_map[name] = out_name

    # 텍스트 추출
    img_counter = 0
    for para in doc.paragraphs:
        text = para.text.strip()

        # 스타일 기반 헤딩
        style = para.style.name if para.style else ""
        if "Heading 1" in style or "제목 1" in style:
            md_lines.append(f"# {text}")
        elif "Heading 2" in style or "제목 2" in style:
            md_lines.append(f"## {text}")
        elif "Heading 3" in style or "제목 3" in style:
            md_lines.append(f"### {text}")
        elif text:
            md_lines.append(text)

        # 인라인 이미지 확인
        for run in para.runs:
            if run._element.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing'):
                img_counter += 1
                if img_counter <= img_idx:
                    img_name = f"{file_path.stem}_{img_counter:03d}"
                    matching = [v for v in image_map.values() if v.startswith(img_name)]
                    if matching:
                        md_lines.append(f"\n![IMG_{img_counter:03d}](images/{matching[0]})\n")

        md_lines.append("")

    content = "\n".join(md_lines)
    content = re.sub(r'\n{3,}', '\n\n', content)

    md_path = out_dir / f"{file_path.stem}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  → {md_path.name} (이미지 {img_idx}개)")
    return md_path


def docx_to_md_libreoffice(file_path, out_dir):
    """python-docx 없을 때 LibreOffice로 텍스트 추출."""
    temp_dir = out_dir / "_temp"
    os.makedirs(temp_dir, exist_ok=True)

    subprocess.run([
        SOFFICE, "--headless", "--convert-to", "txt:Text",
        "--outdir", str(temp_dir), str(file_path)
    ], check=True, capture_output=True)

    txt_path = temp_dir / (file_path.stem + ".txt")
    if txt_path.exists():
        text = txt_path.read_text(encoding="utf-8", errors="replace")
        md_path = out_dir / f"{file_path.stem}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  → {md_path.name} (텍스트만, 이미지 없음)")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return md_path

    shutil.rmtree(temp_dir, ignore_errors=True)
    return None


def main():
    parser = argparse.ArgumentParser(description="HWPX/DOCX → Markdown 변환")
    parser.add_argument("file", help="파일 경로 (.hwpx 또는 .docx)")
    parser.add_argument("-o", "--output", help="출력 디렉토리")
    args = parser.parse_args()

    file_path = Path(args.file).resolve()
    if not file_path.exists():
        print(f"[오류] 파일 없음: {file_path}")
        return

    out_dir = Path(args.output) if args.output else file_path.parent / "md"
    os.makedirs(out_dir, exist_ok=True)

    ext = file_path.suffix.lower()
    if ext == ".hwp":
        hwp_to_md(file_path, out_dir)
    elif ext == ".hwpx":
        hwpx_to_md(file_path, out_dir)
    elif ext == ".docx":
        docx_to_md(file_path, out_dir)
    else:
        print(f"[오류] 지원하지 않는 형식: {ext}")
        print("지원 형식: .hwp, .hwpx, .docx")


if __name__ == "__main__":
    main()
