"""
범용 HWPX 이종 템플릿 병합기.

서로 다른 header.xml을 가진 HWPX 파일을 스타일 보존하며 병합한다.
FILE1의 charPr/paraPr/fontRef를 FILE2(기반)의 header에 추가하고,
FILE1의 내용을 FILE2 앞에 삽입한다.

Usage:
    python merge_hwpx.py <file1.hwpx> <file2.hwpx> -o <output.hwpx>
        [--base {1|2}]         기반 파일 선택 (기본: 2, header가 큰 파일)
        [--order {12|21}]      내용 순서 (기본: 12, file1→file2)
        [--img-prefix TEXT]    file1 이미지 접두어 (기본: "src_")
        [--no-pagebreak]       파일 사이 페이지 넘김 생략

같은 템플릿 파일끼리는 이 스크립트 불필요 — 워크플로우 I 케이스 A 참조.
"""
import argparse
import zipfile
import os
import sys
import subprocess
from lxml import etree
from pathlib import Path
from copy import deepcopy

sys.stdout.reconfigure(encoding="utf-8")

# 스킬 디렉토리 자동 감지
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from hwpx_helpers import update_content_hpf

HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HH = "http://www.hancom.co.kr/hwpml/2011/head"
HC = "http://www.hancom.co.kr/hwpml/2011/core"


def find_items(header, tag):
    """header.xml에서 charPr/paraPr/borderFill 등을 (id, element) 리스트로 반환."""
    items = []
    for elem in header.iter(f"{{{HH}}}{tag}"):
        id_val = elem.get("id")
        if id_val is not None:
            items.append((int(id_val), elem))
    return items


def get_max_id(root):
    """XML 트리에서 숫자 id 속성의 최대값."""
    mx = 0
    for elem in root.iter():
        v = elem.get("id")
        if v and v.isdigit():
            mx = max(mx, int(v))
    return mx


def offset_ids(elem, off):
    """elem과 모든 자식의 숫자 id를 off만큼 오프셋."""
    v = elem.get("id")
    if v and v.isdigit():
        elem.set("id", str(int(v) + off))
    for ch in elem:
        offset_ids(ch, off)


def count_skip(paras):
    """secPr/ctrl이 포함된 선두 문단 수."""
    skip = 0
    for p in paras:
        if p.find(f".//{{{HP}}}secPr") is not None or p.find(f".//{{{HP}}}ctrl") is not None:
            skip += 1
        else:
            break
    return skip


def create_clean_border_fill(bf_id, with_fill=False):
    """SOLID 테두리 + 배경 없음(또는 연한 회색)의 깨끗한 borderFill XML."""
    fill = ""
    if with_fill:
        fill = f'<hc:fillBrush><hc:winBrush faceColor="#E7E6E6" hatchColor="#999999" alpha="0"/></hc:fillBrush>'
    return etree.fromstring(
        f'<hh:borderFill xmlns:hh="{HH}" xmlns:hc="{HC}" id="{bf_id}" '
        f'threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
        f'<hh:slash type="NONE" Crooked="0" isCounter="0"/>'
        f'<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
        f'<hh:leftBorder type="SOLID" width="0.12 mm" color="#000000"/>'
        f'<hh:rightBorder type="SOLID" width="0.12 mm" color="#000000"/>'
        f'<hh:topBorder type="SOLID" width="0.12 mm" color="#000000"/>'
        f'<hh:bottomBorder type="SOLID" width="0.12 mm" color="#000000"/>'
        f'<hh:diagonal type="NONE" width="0.1 mm" color="#000000"/>'
        f'{fill}</hh:borderFill>'
    )


def build_font_map(header_src, header_tgt):
    """src header의 fontRef ID → tgt header의 fontRef ID 매핑 (이름 기반)."""
    font_map = {}
    for ff_tgt in header_tgt.iter(f"{{{HH}}}fontface"):
        lang = ff_tgt.get("lang")
        name_to_id = {f.get("face"): f.get("id") for f in ff_tgt.iter(f"{{{HH}}}font")}
        for ff_src in header_src.iter(f"{{{HH}}}fontface"):
            if ff_src.get("lang") == lang:
                for f in ff_src.iter(f"{{{HH}}}font"):
                    if f.get("face") in name_to_id:
                        font_map[(lang, f.get("id"))] = name_to_id[f.get("face")]
    return font_map


LANG_TO_ATTR = {
    "HANGUL": "hangul", "LATIN": "latin", "HANJA": "hanja",
    "JAPANESE": "japanese", "OTHER": "other", "SYMBOL": "symbol", "USER": "user",
}


def merge_hwpx(file1, file2, output, base=2, order="12", img_prefix="src_", pagebreak=True):
    """
    두 HWPX 파일을 병합한다.

    Args:
        file1, file2: 입력 HWPX 파일 경로
        output: 출력 HWPX 파일 경로
        base: 기반 파일 번호 (1 또는 2). header/settings/META-INF를 이 파일에서 가져옴.
        order: "12" = file1 먼저, "21" = file2 먼저
        img_prefix: 추가 파일 이미지의 접두어 (충돌 방지)
        pagebreak: True면 파일 사이에 페이지 넘김 삽입
    """
    file1, file2, output = Path(file1), Path(file2), Path(output)

    # base가 아닌 쪽을 "src"(추가), base 쪽을 "tgt"(기반)로 설정
    if base == 1:
        tgt_path, src_path = file1, file2
    else:
        tgt_path, src_path = file2, file1

    # 파싱
    with zipfile.ZipFile(str(src_path)) as z:
        header_src = etree.fromstring(z.read("Contents/header.xml"))
        root_src = etree.fromstring(z.read("Contents/section0.xml"))
    with zipfile.ZipFile(str(tgt_path)) as z:
        header_tgt = etree.fromstring(z.read("Contents/header.xml"))
        root_tgt = etree.fromstring(z.read("Contents/section0.xml"))

    print(f"src({src_path.name}): {len(list(root_src))} 요소")
    print(f"tgt({tgt_path.name}): {len(list(root_tgt))} 요소")

    # === header 병합: src의 스타일을 tgt header에 추가 ===

    max_cp = max(id for id, _ in find_items(header_tgt, "charPr"))
    max_pp = max(id for id, _ in find_items(header_tgt, "paraPr"))
    max_bf = max(id for id, _ in find_items(header_tgt, "borderFill"))

    # 표 전용 borderFill 생성
    bf_container = header_tgt.find(f".//{{{HH}}}borderFills")
    cell_bf_id = max_bf + 1
    hdr_bf_id = max_bf + 2
    bf_container.append(create_clean_border_fill(cell_bf_id, with_fill=False))
    bf_container.append(create_clean_border_fill(hdr_bf_id, with_fill=True))
    bf_container.set("itemCnt", str(len(list(bf_container))))
    bf_map = {3: cell_bf_id, 4: hdr_bf_id, 5: cell_bf_id, 6: cell_bf_id}

    # 폰트 매핑
    font_map = build_font_map(header_src, header_tgt)
    print(f"폰트 매핑: {len(font_map)}건")

    # charPr 추가
    cp_map = {}
    cp_container = header_tgt.find(f".//{{{HH}}}charProperties")
    for old_id, elem in find_items(header_src, "charPr"):
        new_id = max_cp + 1 + old_id
        cp_map[old_id] = new_id
        new_elem = deepcopy(elem)
        new_elem.set("id", str(new_id))
        new_elem.set("borderFillIDRef", "1")
        fr = new_elem.find(f"{{{HH}}}fontRef")
        if fr is not None:
            for lang, attr in LANG_TO_ATTR.items():
                old_fid = fr.get(attr)
                if old_fid and (lang, old_fid) in font_map:
                    fr.set(attr, font_map[(lang, old_fid)])
        cp_container.append(new_elem)
    cp_container.set("itemCnt", str(len(list(cp_container))))

    # paraPr 추가
    pp_map = {}
    pp_container = header_tgt.find(f".//{{{HH}}}paraProperties")
    for old_id, elem in find_items(header_src, "paraPr"):
        new_id = max_pp + 1 + old_id
        pp_map[old_id] = new_id
        new_elem = deepcopy(elem)
        new_elem.set("id", str(new_id))
        for border in new_elem.iter(f"{{{HH}}}border"):
            border.set("borderFillIDRef", "1")
        pp_container.append(new_elem)
    pp_container.set("itemCnt", str(len(list(pp_container))))

    print(f"charPr: {len(cp_map)}개, paraPr: {len(pp_map)}개")

    # === src section 리맵 ===

    for elem in root_src.iter():
        cp = elem.get("charPrIDRef")
        if cp is not None and int(cp) in cp_map:
            elem.set("charPrIDRef", str(cp_map[int(cp)]))
        pp = elem.get("paraPrIDRef")
        if pp is not None and int(pp) in pp_map:
            elem.set("paraPrIDRef", str(pp_map[int(pp)]))
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag in ("tc", "tbl"):
            bf = elem.get("borderFillIDRef")
            if bf is not None and int(bf) in bf_map:
                elem.set("borderFillIDRef", str(bf_map[int(bf)]))

    # src 이미지 참조명 변경
    for elem in root_src.iter():
        ref = elem.get("binaryItemIDRef")
        if ref and ref.startswith("image"):
            elem.set("binaryItemIDRef", img_prefix + ref)

    # === tgt 전처리 ===

    # secPr 문단에서 제목 텍스트 run 제거
    first_para = list(root_tgt)[0]
    for run in list(first_para.iter(f"{{{HP}}}run")):
        t = run.find(f"{{{HP}}}t")
        if t is not None and t.text and t.text.strip():
            title_text = t.text.strip()
            first_para.remove(run)
            print(f"secPr 문단에서 제목 run 제거: '{title_text}'")

    # styleIDRef 통일
    for elem in root_tgt.iter():
        if elem.get("styleIDRef") is not None and elem.get("styleIDRef") != "0":
            elem.set("styleIDRef", "0")

    # === section 병합 ===

    paras_src = list(root_src)
    skip_src = count_skip(paras_src)
    paras_tgt = list(root_tgt)
    skip_tgt = count_skip(paras_tgt)

    max_id_tgt = get_max_id(root_tgt)
    offset = max_id_tgt + 1000

    # 순서 결정
    if order == "12":
        # file1 먼저 → file2 뒤에
        # src=file1이면 src 먼저, tgt 뒤
        if base == 2:  # tgt=file2, src=file1 → src 먼저
            first_paras, first_skip = paras_src, skip_src
            # tgt는 이미 root_tgt에 있음
        else:  # tgt=file1, src=file2 → tgt 먼저 (이미 기반)
            first_paras, first_skip = None, 0
    else:
        # file2 먼저
        if base == 2:  # tgt=file2 → tgt 먼저 (이미 기반)
            first_paras, first_skip = None, 0
        else:  # tgt=file1, src=file2 → src 먼저
            first_paras, first_skip = paras_src, skip_src

    if first_paras is not None:
        # src 문단을 secPr 직후에 삽입
        insert_pos = skip_tgt
        for idx, p in enumerate(first_paras[first_skip:]):
            pc = deepcopy(p)
            offset_ids(pc, offset)
            root_tgt.insert(insert_pos + idx, pc)

        if pagebreak:
            pb_pos = insert_pos + len(first_paras) - first_skip
            pb = etree.Element(f"{{{HP}}}p")
            pb.set("id", str(offset + get_max_id(root_src) + 500))
            pb.set("paraPrIDRef", "0"); pb.set("styleIDRef", "0")
            pb.set("pageBreak", "1"); pb.set("columnBreak", "0"); pb.set("merged", "0")
            run = etree.SubElement(pb, f"{{{HP}}}run")
            run.set("charPrIDRef", "0")
            etree.SubElement(run, f"{{{HP}}}t")
            root_tgt.insert(pb_pos, pb)
    else:
        # src를 뒤에 추가
        if pagebreak:
            mx = get_max_id(root_tgt)
            pb = etree.SubElement(root_tgt, f"{{{HP}}}p")
            pb.set("id", str(mx + 500))
            pb.set("paraPrIDRef", "0"); pb.set("styleIDRef", "0")
            pb.set("pageBreak", "1"); pb.set("columnBreak", "0"); pb.set("merged", "0")
            run = etree.SubElement(pb, f"{{{HP}}}run")
            run.set("charPrIDRef", "0")
            etree.SubElement(run, f"{{{HP}}}t")
        for p in paras_src[skip_src:]:
            pc = deepcopy(p)
            offset_ids(pc, offset)
            root_tgt.append(pc)

    print(f"최종: {len(list(root_tgt))}개 요소")

    # === 직렬화 + ZIP 조립 ===

    merged_section = '<?xml version="1.0" encoding="UTF-8"?>\n' + etree.tostring(root_tgt, encoding="unicode")
    merged_header = '<?xml version="1.0" encoding="UTF-8"?>\n' + etree.tostring(header_tgt, encoding="unicode")

    # src BinData 사전 로드
    src_bindata = {}
    with zipfile.ZipFile(str(src_path)) as z:
        for n in z.namelist():
            if n.startswith("BinData/"):
                src_bindata["BinData/" + img_prefix + os.path.basename(n)] = z.read(n)

    # tgt 기반으로 ZIP 조립
    with zipfile.ZipFile(str(tgt_path), "r") as z_tgt:
        with zipfile.ZipFile(str(output), "w", zipfile.ZIP_DEFLATED) as zout:
            for item in z_tgt.infolist():
                if item.filename == "Contents/section0.xml":
                    zout.writestr(item, merged_section.encode("utf-8"))
                elif item.filename == "Contents/header.xml":
                    zout.writestr(item, merged_header.encode("utf-8"))
                elif item.filename == "mimetype":
                    zout.writestr(item, z_tgt.read(item.filename), compress_type=zipfile.ZIP_STORED)
                else:
                    zout.writestr(item, z_tgt.read(item.filename))
            for name, data in src_bindata.items():
                zout.writestr(name, data)

    # content.hpf 업데이트
    all_imgs = []
    with zipfile.ZipFile(str(output)) as z:
        for n in z.namelist():
            if n.startswith("BinData/"):
                fname = os.path.basename(n)
                all_imgs.append({"file": fname, "id": fname.rsplit(".", 1)[0], "src_path": ""})
    update_content_hpf(str(output), all_imgs)

    # 후처리
    subprocess.run([sys.executable, str(SCRIPT_DIR / "fix_namespaces.py"), str(output)],
                   check=True, capture_output=True)
    r = subprocess.run([sys.executable, str(SCRIPT_DIR / "validate.py"), str(output)],
                       capture_output=True, text=True, encoding="utf-8")
    print(f"validate: {r.stdout.strip()}")
    print(f"\n✅ {output.name} ({output.stat().st_size:,} bytes, {output.stat().st_size/1024/1024:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(description="HWPX 이종 템플릿 병합기")
    parser.add_argument("file1", help="첫 번째 HWPX 파일")
    parser.add_argument("file2", help="두 번째 HWPX 파일")
    parser.add_argument("-o", "--output", required=True, help="출력 HWPX 파일")
    parser.add_argument("--base", type=int, default=2, choices=[1, 2],
                        help="기반 파일 번호 (기본: 2, header가 큰 파일)")
    parser.add_argument("--order", default="12", choices=["12", "21"],
                        help="내용 순서 (기본: 12)")
    parser.add_argument("--img-prefix", default="src_",
                        help="추가 파일 이미지 접두어 (기본: src_)")
    parser.add_argument("--no-pagebreak", action="store_true",
                        help="파일 사이 페이지 넘김 생략")
    args = parser.parse_args()
    merge_hwpx(args.file1, args.file2, args.output,
               base=args.base, order=args.order,
               img_prefix=args.img_prefix, pagebreak=not args.no_pagebreak)


if __name__ == "__main__":
    main()
