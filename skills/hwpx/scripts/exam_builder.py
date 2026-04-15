#!/usr/bin/env python3
"""
시험 문제지 HWPX 생성기 (Workflow J)

구조화된 JSON 데이터 → 시험 문제지 HWPX 문서.
엔드노트 정답, 탭 정렬 선택지, 그룹 레이블/지문 등을 지원.

사용법:
  CLI:
    python exam_builder.py data.json -o exam.hwpx
    python exam_builder.py data.json --ref form.hwpx -o exam.hwpx
    python exam_builder.py data.json --template report -o exam.hwpx

  Import:
    from exam_builder import build_exam, build_section_xml
"""

import argparse
import json
import os
import random
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from hwpx_helpers import (
    NS_DECL,
    extract_secpr_and_colpr,
    next_id,
    reset_id,
    xml_escape,
)

# ─── 기본 secPr (md2hwpx.py와 동일, colCount만 2로 변경) ──────────

DEFAULT_SECPR = (
    '<hp:secPr id="" textDirection="HORIZONTAL" spaceColumns="1134" '
    'tabStop="8000" tabStopVal="4000" tabStopUnit="HWPUNIT" '
    'outlineShapeIDRef="1" memoShapeIDRef="0" textVerticalWidthHead="0" '
    'masterPageCnt="0">'
    '<hp:grid lineGrid="0" charGrid="0" wonggojiFormat="0"/>'
    '<hp:startNum pageStartsOn="BOTH" page="0" pic="0" tbl="0" equation="0"/>'
    '<hp:visibility hideFirstHeader="0" hideFirstFooter="0" '
    'hideFirstMasterPage="0" border="SHOW_ALL" fill="SHOW_ALL" '
    'hideFirstPageNum="0" hideFirstEmptyLine="0" showLineNumber="0"/>'
    '<hp:lineNumberShape restartType="0" countBy="0" distance="0" startNumber="0"/>'
    '<hp:pagePr landscape="WIDELY" width="59528" height="84186" gutterType="LEFT_ONLY">'
    '<hp:margin header="4252" footer="4252" gutter="0" '
    'left="8504" right="8504" top="5668" bottom="4252"/>'
    '</hp:pagePr>'
    '<hp:footNotePr>'
    '<hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0"/>'
    '<hp:noteLine length="-1" type="SOLID" width="0.12 mm" color="#000000"/>'
    '<hp:noteSpacing betweenNotes="283" belowLine="567" aboveLine="850"/>'
    '<hp:numbering type="CONTINUOUS" newNum="1"/>'
    '<hp:placement place="EACH_COLUMN" beneathText="0"/>'
    '</hp:footNotePr>'
    '<hp:endNotePr>'
    '<hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0"/>'
    '<hp:noteLine length="14692344" type="SOLID" width="0.12 mm" color="#000000"/>'
    '<hp:noteSpacing betweenNotes="0" belowLine="567" aboveLine="850"/>'
    '<hp:numbering type="CONTINUOUS" newNum="1"/>'
    '<hp:placement place="END_OF_DOCUMENT" beneathText="0"/>'
    '</hp:endNotePr>'
    '<hp:pageBorderFill type="BOTH" borderFillIDRef="1" textBorder="PAPER" '
    'headerInside="0" footerInside="0" fillArea="PAPER">'
    '<hp:offset left="1417" right="1417" top="1417" bottom="1417"/>'
    '</hp:pageBorderFill>'
    '<hp:pageBorderFill type="EVEN" borderFillIDRef="1" textBorder="PAPER" '
    'headerInside="0" footerInside="0" fillArea="PAPER">'
    '<hp:offset left="1417" right="1417" top="1417" bottom="1417"/>'
    '</hp:pageBorderFill>'
    '<hp:pageBorderFill type="ODD" borderFillIDRef="1" textBorder="PAPER" '
    'headerInside="0" footerInside="0" fillArea="PAPER">'
    '<hp:offset left="1417" right="1417" top="1417" bottom="1417"/>'
    '</hp:pageBorderFill>'
    '</hp:secPr>'
)

DEFAULT_COLPR_1COL = (
    '<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" '
    'colCount="1" sameSz="1" sameGap="0"/></hp:ctrl>'
)

DEFAULT_COLPR_2COL = (
    '<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" '
    'colCount="2" sameSz="1" sameGap="2268"/></hp:ctrl>'
)

# ─── 기본 스타일 ID (report 템플릿 기준) ────────────────────────────

DEFAULT_STYLE = {
    "group_label": {"charPr": "9", "paraPr": "0"},
    "passage":     {"charPr": "0", "paraPr": "0"},
    "question":    {"charPr": "0", "paraPr": "0"},
    "choice":      {"charPr": "0", "paraPr": "0"},
    "endnote_ref": {"charPr": "0"},
    "endnote_body":{"charPr": "0", "paraPr": "0"},
    "empty":       {"charPr": "0", "paraPr": "0"},
}

CIRCLE_NUMS = ["①", "②", "③", "④", "⑤"]


# ═══════════════════════════════════════════════════════════════════
# XML 빌더 함수
# ═══════════════════════════════════════════════════════════════════

def _lineseg():
    """기본 linesegarray (한글이 열 때 자동 재계산)."""
    return (
        '<hp:linesegarray><hp:lineseg textpos="0" vertpos="0" '
        'vertsize="900" textheight="900" baseline="765" spacing="360" '
        'horzpos="0" horzsize="22960" flags="393216"/></hp:linesegarray>'
    )


def make_endnote_run(endnote_num, answer, style):
    """엔드노트 run — 정답을 엔드노트로 삽입."""
    inst_id = random.randint(1_000_000_000, 2_100_000_000)
    en_charpr = style.get("endnote_ref", {}).get("charPr", "0")
    body_charpr = style.get("endnote_body", {}).get("charPr", "0")
    body_parapr = style.get("endnote_body", {}).get("paraPr", "0")
    return (
        f'<hp:run charPrIDRef="{en_charpr}">'
        f'<hp:ctrl>'
        f'<hp:endNote number="{endnote_num}" suffixChar="41" instId="{inst_id}">'
        f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" '
        f'vertAlign="TOP" linkListIDRef="0" linkListNextIDRef="0" '
        f'textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
        f'<hp:p id="{next_id()}" paraPrIDRef="{body_parapr}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{body_charpr}"><hp:ctrl>'
        f'<hp:autoNum num="{endnote_num}" numType="ENDNOTE">'
        f'<hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" '
        f'suffixChar=")" supscript="0"/>'
        f'</hp:autoNum></hp:ctrl><hp:t> </hp:t></hp:run>'
        f'<hp:run charPrIDRef="{body_charpr}">'
        f'<hp:t>{xml_escape(answer)}</hp:t></hp:run>'
        f'{_lineseg()}'
        f'</hp:p></hp:subList></hp:endNote></hp:ctrl>'
        f'<hp:t/></hp:run>'
    )


def make_question_para(num, text, answer, endnote_num, style):
    """질문 문단 + 엔드노트 정답."""
    charpr = style.get("question", {}).get("charPr", "0")
    parapr = style.get("question", {}).get("paraPr", "0")
    endnote = make_endnote_run(endnote_num, answer, style)
    return (
        f'<hp:p id="{next_id()}" paraPrIDRef="{parapr}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{charpr}">'
        f'<hp:t>{xml_escape(f"{num}. {text}")}</hp:t></hp:run>'
        f'{endnote}'
        f'{_lineseg()}'
        f'</hp:p>'
    )


def make_choices_inline(choices, style):
    """짧은 선택지 — 탭 정렬 2줄 (①②③ / ④⑤)."""
    charpr = style.get("choice", {}).get("charPr", "0")
    parapr = style.get("choice", {}).get("paraPr", "0")
    c = [xml_escape(ch) for ch in choices]

    rows = []
    if len(c) >= 3:
        row1 = (
            f'<hp:p id="{next_id()}" paraPrIDRef="{parapr}" styleIDRef="0" '
            f'pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{charpr}"><hp:t>'
            f'{CIRCLE_NUMS[0]} {c[0]}'
            f'<hp:tab width="3754" leader="0" type="1"/>'
            f'{CIRCLE_NUMS[1]} {c[1]}'
            f'<hp:tab width="3754" leader="0" type="1"/>'
            f'{CIRCLE_NUMS[2]} {c[2]}'
            f'</hp:t></hp:run>{_lineseg()}</hp:p>'
        )
        rows.append(row1)

    if len(c) >= 5:
        row2 = (
            f'<hp:p id="{next_id()}" paraPrIDRef="{parapr}" styleIDRef="0" '
            f'pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{charpr}"><hp:t>'
            f'{CIRCLE_NUMS[3]} {c[3]}'
            f'<hp:tab width="3754" leader="0" type="1"/>'
            f'{CIRCLE_NUMS[4]} {c[4]}'
            f'</hp:t></hp:run>{_lineseg()}</hp:p>'
        )
        rows.append(row2)
    elif len(c) == 4:
        row2 = (
            f'<hp:p id="{next_id()}" paraPrIDRef="{parapr}" styleIDRef="0" '
            f'pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{charpr}"><hp:t>'
            f'{CIRCLE_NUMS[3]} {c[3]}'
            f'</hp:t></hp:run>{_lineseg()}</hp:p>'
        )
        rows.append(row2)

    return rows


def make_choices_stacked(choices, style):
    """긴 선택지 — 각 1줄."""
    charpr = style.get("choice", {}).get("charPr", "0")
    parapr = style.get("choice", {}).get("paraPr", "0")
    rows = []
    for i, ch in enumerate(choices):
        sym = CIRCLE_NUMS[i] if i < len(CIRCLE_NUMS) else f"({i+1})"
        rows.append(
            f'<hp:p id="{next_id()}" paraPrIDRef="{parapr}" styleIDRef="0" '
            f'pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{charpr}">'
            f'<hp:t>{sym} {xml_escape(ch)}</hp:t></hp:run>'
            f'{_lineseg()}</hp:p>'
        )
    return rows


def make_group_label_para(label, style, secpr="", colpr=""):
    """그룹 레이블 ([1-2] 다음 글을 읽고...). 첫 문단이면 secPr+colPr 포함."""
    charpr = style.get("group_label", {}).get("charPr", "9")
    parapr = style.get("group_label", {}).get("paraPr", "0")
    sec_run = ""
    if secpr:
        sec_run = f'<hp:run charPrIDRef="{charpr}">{secpr}{colpr}</hp:run>'
    return (
        f'<hp:p id="{next_id()}" paraPrIDRef="{parapr}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'{sec_run}'
        f'<hp:run charPrIDRef="{charpr}">'
        f'<hp:t>{xml_escape(label)}</hp:t></hp:run>'
        f'{_lineseg()}</hp:p>'
    )


def make_passage_para(text, style):
    """지문 본문 단락."""
    charpr = style.get("passage", {}).get("charPr", "0")
    parapr = style.get("passage", {}).get("paraPr", "0")
    return (
        f'<hp:p id="{next_id()}" paraPrIDRef="{parapr}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{charpr}">'
        f'<hp:t>{xml_escape(text)}</hp:t></hp:run>'
        f'{_lineseg()}</hp:p>'
    )


def make_empty_para(style):
    """빈 줄."""
    charpr = style.get("empty", {}).get("charPr", "0")
    parapr = style.get("empty", {}).get("paraPr", "0")
    return (
        f'<hp:p id="{next_id()}" paraPrIDRef="{parapr}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{charpr}"><hp:t/></hp:run>'
        f'{_lineseg()}</hp:p>'
    )


def _is_short_choices(choices):
    """선택지가 탭 정렬(inline)에 적합한지 판단."""
    return all(len(c) <= 15 for c in choices)


# ═══════════════════════════════════════════════════════════════════
# section0.xml 조립
# ═══════════════════════════════════════════════════════════════════

def build_section_xml(data, secpr=None, colpr=None):
    """
    JSON 데이터 → section0.xml 문자열.

    Args:
        data: 파싱된 JSON (dict)
        secpr: secPr XML 문자열 (None이면 DEFAULT_SECPR 사용)
        colpr: colPr XML 문자열 (None이면 columns 설정에 따라 자동)
    """
    reset_id(100)

    if secpr is None:
        secpr = DEFAULT_SECPR
    if colpr is None:
        cols = data.get("columns", 1)
        colpr = DEFAULT_COLPR_2COL if cols >= 2 else DEFAULT_COLPR_1COL

    style = {**DEFAULT_STYLE}
    if "style" in data:
        for k, v in data["style"].items():
            if k in style:
                style[k].update(v)
            else:
                style[k] = v

    items = data.get("items", [])
    paras = []
    endnote_num = 1
    is_first = True

    for item in items:
        # 그룹 문항 (group + passage + questions)
        if "group" in item or "questions" in item:
            # 그룹 레이블
            if item.get("group"):
                if is_first:
                    paras.append(make_group_label_para(
                        item["group"], style, secpr, colpr))
                    is_first = False
                else:
                    paras.append(make_empty_para(style))
                    paras.append(make_group_label_para(item["group"], style))

            # 지문
            if item.get("passage"):
                paras.append(make_passage_para(item["passage"], style))
                paras.append(make_empty_para(style))

            # 하위 질문들
            for q in item.get("questions", []):
                paras.append(make_question_para(
                    q["num"], q["text"], q.get("answer", ""),
                    endnote_num, style))
                endnote_num += 1

                choices = q.get("choices", [])
                if choices:
                    if _is_short_choices(choices):
                        paras.extend(make_choices_inline(choices, style))
                    else:
                        paras.extend(make_choices_stacked(choices, style))

                paras.append(make_empty_para(style))

        # 독립 문항 (num + text + choices)
        elif "num" in item:
            if is_first:
                # 첫 문단에 secPr+colPr 넣기: 빈 레이블로 처리
                paras.append(
                    f'<hp:p id="{next_id()}" paraPrIDRef="0" styleIDRef="0" '
                    f'pageBreak="0" columnBreak="0" merged="0">'
                    f'<hp:run charPrIDRef="0">{secpr}{colpr}</hp:run></hp:p>'
                )
                is_first = False

            paras.append(make_question_para(
                item["num"], item["text"], item.get("answer", ""),
                endnote_num, style))
            endnote_num += 1

            choices = item.get("choices", [])
            if choices:
                if _is_short_choices(choices):
                    paras.extend(make_choices_inline(choices, style))
                else:
                    paras.extend(make_choices_stacked(choices, style))

            paras.append(make_empty_para(style))

    # 문서 끝 단락
    paras.append(
        f'<hp:p id="{next_id()}" paraPrIDRef="0" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="0"><hp:t/></hp:run>{_lineseg()}</hp:p>'
    )

    xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    xml += f'<hs:sec {NS_DECL}>'
    xml += "".join(paras)
    xml += '</hs:sec>'
    return xml


# ═══════════════════════════════════════════════════════════════════
# 전체 파이프라인
# ═══════════════════════════════════════════════════════════════════

def build_exam(json_path, output, template="report", ref_hwpx=None,
               title=None, creator=None):
    """
    전체 빌드 파이프라인.

    Args:
        json_path: 입력 JSON 파일 경로
        output: 출력 HWPX 파일 경로
        template: 템플릿 이름 (base, report, gonmun 등)
        ref_hwpx: 참조 양식 HWPX (있으면 secPr/colPr + header 추출)
        title: 문서 제목 (메타데이터)
        creator: 작성자 (메타데이터)
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    secpr, colpr = None, None
    header_arg = []

    if ref_hwpx:
        secpr, colpr = extract_secpr_and_colpr(ref_hwpx)
        # 양식의 header.xml도 사용
        import zipfile
        with zipfile.ZipFile(ref_hwpx, "r") as zf:
            if "Contents/header.xml" in zf.namelist():
                header_tmp = output + ".header.xml"
                with open(header_tmp, "wb") as hf:
                    hf.write(zf.read("Contents/header.xml"))
                header_arg = ["--header", header_tmp]

    # [1] section0.xml 생성
    section_xml = build_section_xml(data, secpr, colpr)
    section_tmp = output + ".section0.xml"
    with open(section_tmp, "w", encoding="utf-8") as f:
        f.write(section_xml)

    # [2] build_hwpx.py 호출
    cmd = [
        sys.executable,
        os.path.join(SCRIPT_DIR, "build_hwpx.py"),
        "--template", template,
        "--section", section_tmp,
        "--output", output,
    ]
    cmd.extend(header_arg)
    if title:
        cmd.extend(["--title", title])
    if creator:
        cmd.extend(["--creator", creator])

    subprocess.run(cmd, check=True)

    # [3] fix_namespaces.py 후처리
    subprocess.run([
        sys.executable,
        os.path.join(SCRIPT_DIR, "fix_namespaces.py"),
        output,
    ], check=True)

    # [4] 임시 파일 정리
    os.remove(section_tmp)
    if header_arg:
        header_tmp = output + ".header.xml"
        if os.path.exists(header_tmp):
            os.remove(header_tmp)

    print(f"DONE: {output}")


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="시험 문제지 HWPX 생성기 (Workflow J)"
    )
    parser.add_argument(
        "json_input",
        help="입력 JSON 파일 경로",
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="출력 HWPX 파일 경로",
    )
    parser.add_argument(
        "--template", "-t",
        default="report",
        help="템플릿 이름 (기본: report)",
    )
    parser.add_argument(
        "--ref",
        help="참조 양식 HWPX (스타일 ID + secPr/colPr 추출)",
    )
    parser.add_argument(
        "--title",
        help="문서 제목 (메타데이터)",
    )
    parser.add_argument(
        "--creator",
        help="작성자 (메타데이터)",
    )
    args = parser.parse_args()

    build_exam(
        json_path=args.json_input,
        output=args.output,
        template=args.template,
        ref_hwpx=args.ref,
        title=args.title,
        creator=args.creator,
    )


if __name__ == "__main__":
    main()
