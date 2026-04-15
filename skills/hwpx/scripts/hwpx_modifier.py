"""
HWPX 파일 수정 모듈
- 기존 HWPX 양식을 읽어서 내용만 수정
- 원본 서식/레이아웃 유지
"""

import zipfile
import shutil
import os
import re
import tempfile
from copy import deepcopy
from typing import Dict, List, Tuple, Optional
from lxml import etree


class HwpxModifier:
    """
    HWPX 파일을 읽고 수정하는 클래스
    
    사용법:
        with HwpxModifier("/path/to/template.hwpx") as doc:
            # 문서 내용 확인
            print(doc.get_text_summary())
            
            # 텍스트 치환
            doc.replace_text("기존텍스트", "새텍스트")
            
            # 저장
            doc.save("/path/to/output.hwpx")
    """
    
    HP = 'http://www.hancom.co.kr/hwpml/2011/paragraph'
    HH = 'http://www.hancom.co.kr/hwpml/2011/head'
    HC = 'http://www.hancom.co.kr/hwpml/2011/core'

    def __init__(self, hwpx_path: str):
        """
        Args:
            hwpx_path: HWPX 파일 경로
        """
        self.hwpx_path = hwpx_path
        self.temp_dir = None
        self.section_xml = None
        self.section_tree = None
        self.header_tree = None
        self._header_modified = False
        self._indent_style_cache = {}  # left_value -> paraPrID
        self._max_parapr_id = None
        
    def open(self) -> 'HwpxModifier':
        """HWPX 파일 열기"""
        # 임시 디렉토리 생성
        self.temp_dir = tempfile.mkdtemp(prefix='hwpx_mod_')
        
        # ZIP 압축 해제
        with zipfile.ZipFile(self.hwpx_path, 'r') as zf:
            zf.extractall(self.temp_dir)
        
        # section0.xml 파싱
        section_path = os.path.join(self.temp_dir, 'Contents', 'section0.xml')
        with open(section_path, 'rb') as f:
            self.section_xml = f.read()
        
        # lxml로 파싱 (네임스페이스 보존)
        self.section_tree = etree.fromstring(self.section_xml)

        # header.xml 파싱
        header_path = os.path.join(self.temp_dir, 'Contents', 'header.xml')
        if os.path.exists(header_path):
            with open(header_path, 'rb') as f:
                self.header_tree = etree.fromstring(f.read())

        return self
    
    def get_all_texts(self) -> List[Tuple[int, str]]:
        """
        모든 텍스트 요소를 인덱스와 함께 반환
        
        Returns:
            [(인덱스, 텍스트), ...] 형태의 리스트
        """
        texts = []
        for idx, elem in enumerate(self.section_tree.iter('{http://www.hancom.co.kr/hwpml/2011/paragraph}t')):
            if elem.text:
                texts.append((idx, elem.text))
        return texts
    
    def get_text_summary(self, max_items: int = 50) -> str:
        """
        문서 텍스트 요약 반환 (Claude가 분석용으로 사용)
        
        Args:
            max_items: 최대 출력 항목 수
            
        Returns:
            텍스트 요약 문자열
        """
        texts = self.get_all_texts()
        lines = []
        for idx, text in texts[:max_items]:
            # 긴 텍스트는 축약
            display = text[:60] + "..." if len(text) > 60 else text
            # 개행 제거
            display = display.replace('\n', '\\n')
            lines.append(f"[{idx}] {display}")
        
        if len(texts) > max_items:
            lines.append(f"... 외 {len(texts) - max_items}개 텍스트 요소")
        
        return "\n".join(lines)
    
    def replace_text(self, old_text: str, new_text: str, count: int = -1) -> int:
        """
        텍스트 치환 (부분 일치)
        
        Args:
            old_text: 찾을 텍스트
            new_text: 바꿀 텍스트
            count: 치환 횟수 제한 (-1이면 모두)
            
        Returns:
            치환된 횟수
        """
        replaced = 0
        for elem in self.section_tree.iter('{http://www.hancom.co.kr/hwpml/2011/paragraph}t'):
            if elem.text and old_text in elem.text:
                elem.text = elem.text.replace(old_text, new_text)
                replaced += 1
                if count > 0 and replaced >= count:
                    break
        return replaced
    
    def replace_text_exact(self, old_text: str, new_text: str) -> int:
        """
        정확히 일치하는 텍스트만 치환
        
        Args:
            old_text: 찾을 텍스트 (정확히 일치해야 함)
            new_text: 바꿀 텍스트
            
        Returns:
            치환된 횟수
        """
        replaced = 0
        for elem in self.section_tree.iter('{http://www.hancom.co.kr/hwpml/2011/paragraph}t'):
            if elem.text == old_text:
                elem.text = new_text
                replaced += 1
        return replaced
    
    def replace_text_by_index(self, index: int, new_text: str) -> bool:
        """
        특정 인덱스의 텍스트 전체를 교체
        
        Args:
            index: 텍스트 요소 인덱스 (get_text_summary()에서 확인)
            new_text: 새 텍스트
            
        Returns:
            성공 여부
        """
        for idx, elem in enumerate(self.section_tree.iter('{http://www.hancom.co.kr/hwpml/2011/paragraph}t')):
            if idx == index:
                elem.text = new_text
                return True
        return False
    
    def replace_by_pattern(self, pattern: str, replacement: str) -> int:
        """
        정규식 패턴으로 치환
        
        Args:
            pattern: 정규식 패턴
            replacement: 치환 문자열 (그룹 참조 가능: \\1, \\2 등)
            
        Returns:
            치환된 요소 수
        """
        replaced = 0
        regex = re.compile(pattern)
        for elem in self.section_tree.iter('{http://www.hancom.co.kr/hwpml/2011/paragraph}t'):
            if elem.text and regex.search(elem.text):
                elem.text = regex.sub(replacement, elem.text)
                replaced += 1
        return replaced
    
    def find_text(self, search_text: str) -> List[Tuple[int, str]]:
        """
        텍스트 검색
        
        Args:
            search_text: 검색할 텍스트
            
        Returns:
            [(인덱스, 전체텍스트), ...] 형태의 리스트
        """
        results = []
        for idx, elem in enumerate(self.section_tree.iter('{http://www.hancom.co.kr/hwpml/2011/paragraph}t')):
            if elem.text and search_text in elem.text:
                results.append((idx, elem.text))
        return results
    
    def batch_replace(self, replacements: Dict[str, str]) -> Dict[str, int]:
        """
        여러 텍스트를 한번에 치환
        
        Args:
            replacements: {찾을텍스트: 바꿀텍스트} 딕셔너리
            
        Returns:
            {텍스트: 치환횟수} 딕셔너리
        """
        results = {}
        for old_text, new_text in replacements.items():
            count = self.replace_text(old_text, new_text)
            results[old_text] = count
        return results
    
    # ── 문단 들여쓰기 (왼쪽 여백) ──

    def _find_base_parapr(self) -> Optional[etree._Element]:
        """heading=NONE인 paraPr을 찾아 반환 (복제 원본용)"""
        if self.header_tree is None:
            return None
        for ppr in self.header_tree.iter(f'{{{self.HH}}}paraPr'):
            for child in ppr:
                if child.tag.split('}')[-1] == 'heading':
                    if child.get('type') == 'NONE':
                        return ppr
        return None

    def _get_max_parapr_id(self) -> int:
        """header.xml에서 paraPr 최대 id 반환 (캐싱)"""
        if self._max_parapr_id is not None:
            return self._max_parapr_id
        max_id = 0
        if self.header_tree is None:
            return max_id
        for ppr in self.header_tree.iter(f'{{{self.HH}}}paraPr'):
            pid = int(ppr.get('id', '0'))
            if pid > max_id:
                max_id = pid
        self._max_parapr_id = max_id
        return max_id

    def _create_indent_style(self, left_value: int) -> str:
        """
        주어진 왼쪽 여백 값으로 새 paraPr을 header.xml에 생성한다.

        HWPX의 paraPr 안에는 hp:switch 분기가 있다:
        - hp:case (HwpUnitChar): 새 엔진용 값
        - hp:default: 이전 엔진용 값 (case의 2배)
        한글이 두 분기를 모두 참조하므로, 양쪽에 올바른 값을 넣어야 한다.

        Args:
            left_value: 왼쪽 여백 (HWPUNIT). 한글 UI의 "왼쪽 10" = 1000.

        Returns:
            새로 생성된 paraPr의 id 문자열
        """
        if left_value in self._indent_style_cache:
            return self._indent_style_cache[left_value]

        base = self._find_base_parapr()
        if base is None:
            raise RuntimeError("header.xml에서 heading=NONE인 paraPr을 찾을 수 없습니다")

        new_id = self._get_max_parapr_id() + 1
        self._max_parapr_id = new_id
        new_ppr = deepcopy(base)
        new_ppr.set('id', str(new_id))

        # hp:switch 내의 case/default 분기에서 hc:left 값 설정
        for sw_child in new_ppr.iter():
            tag = sw_child.tag.split('}')[-1]
            if tag == 'case':
                for left_elem in sw_child.iter(f'{{{self.HC}}}left'):
                    left_elem.set('value', str(left_value))
            elif tag == 'default':
                for left_elem in sw_child.iter(f'{{{self.HC}}}left'):
                    left_elem.set('value', str(left_value * 2))

        base.getparent().append(new_ppr)

        # paraPrList count 업데이트
        for elem in self.header_tree.iter():
            if elem.tag.split('}')[-1] == 'paraPrList':
                elem.set('count', str(int(elem.get('count', '0')) + 1))
                break

        self._header_modified = True
        self._indent_style_cache[left_value] = str(new_id)
        return str(new_id)

    def _get_all_paragraphs(self, table_index: int = -1, row_index: int = -1
                            ) -> List[etree._Element]:
        """문단 요소 리스트 반환. table/row 지정 시 해당 셀 내부만."""
        if table_index >= 0:
            tables = self.section_tree.findall(f'.//{{{self.HP}}}tbl')
            if table_index >= len(tables):
                return []
            tbl = tables[table_index]
            rows = tbl.findall(f'{{{self.HP}}}tr')
            if row_index >= 0:
                if row_index >= len(rows):
                    return []
                cells = rows[row_index].findall(f'{{{self.HP}}}tc')
                paras = []
                for cell in cells:
                    paras.extend(cell.findall(f'.//{{{self.HP}}}p'))
                return paras
            else:
                return tbl.findall(f'.//{{{self.HP}}}p')
        return list(self.section_tree.iter(f'{{{self.HP}}}p'))

    def set_indent_rules(self, rules: Dict[str, int],
                         table_index: int = -1, row_index: int = -1) -> int:
        """
        정규식 패턴별로 문단 왼쪽 여백(들여쓰기)을 일괄 설정한다.

        Args:
            rules: {정규식패턴: 왼쪽여백값(HWPUNIT)} 딕셔너리.
                   한글 UI 기준 "왼쪽 10" = 1000 HWPUNIT.
                   예: {r'^\\d+\\.': 0, r'^[가-힣]\\.': 1000, r'^-': 2000}
            table_index: 특정 표 내부만 적용 (-1이면 문서 전체)
            row_index: 특정 행 내부만 적용 (table_index 필요, -1이면 표 전체)

        Returns:
            변경된 문단 수

        Example:
            with HwpxModifier("회의록.hwpx") as doc:
                doc.set_indent_rules({
                    r'^\\d+\\.': 0,       # "1." "2." → 들여쓰기 없음
                    r'^[가-힣]\\.': 1000,  # "가." "나." → 왼쪽 10
                    r'^-': 2000,          # "-" 항목 → 왼쪽 20
                })
                doc.save("output.hwpx")
        """
        if self.header_tree is None:
            raise RuntimeError("header.xml이 없습니다")

        # 각 left_value에 대응하는 paraPr id 준비
        compiled = []
        for pattern, left_value in rules.items():
            regex = re.compile(pattern)
            if left_value == 0:
                # left=0: heading=NONE인 기존 base paraPr 사용
                base = self._find_base_parapr()
                prid = base.get('id') if base is not None else '0'
            else:
                prid = self._create_indent_style(left_value)
            compiled.append((regex, prid))

        paras = self._get_all_paragraphs(table_index, row_index)
        modified = 0
        for p in paras:
            texts = ''.join(
                t.text or '' for t in p.findall(f'.//{{{self.HP}}}t'))
            t = texts.strip()
            if not t:
                continue
            for regex, prid in compiled:
                if regex.match(t):
                    if p.get('paraPrIDRef') != prid:
                        p.set('paraPrIDRef', prid)
                        modified += 1
                    break
        return modified

    def set_paragraph_indent(self, search_text: str, left_value: int) -> int:
        """
        특정 텍스트를 포함하는 문단의 왼쪽 여백을 설정한다.

        Args:
            search_text: 찾을 텍스트 (부분 일치)
            left_value: 왼쪽 여백 (HWPUNIT). 0이면 들여쓰기 제거.

        Returns:
            변경된 문단 수
        """
        if self.header_tree is None:
            raise RuntimeError("header.xml이 없습니다")

        if left_value == 0:
            base = self._find_base_parapr()
            prid = base.get('id') if base is not None else '0'
        else:
            prid = self._create_indent_style(left_value)

        modified = 0
        for p in self.section_tree.iter(f'{{{self.HP}}}p'):
            texts = ''.join(
                t.text or '' for t in p.findall(f'.//{{{self.HP}}}t'))
            if search_text in texts:
                if p.get('paraPrIDRef') != prid:
                    p.set('paraPrIDRef', prid)
                    modified += 1
        return modified

    def save(self, output_path: str) -> str:
        """
        수정된 HWPX 파일 저장

        Args:
            output_path: 저장할 파일 경로

        Returns:
            저장된 파일 경로
        """
        # linesegarray 제거 (텍스트 수정 후 레이아웃 캐시 무효화 → 한글이 자동 재계산)
        for lsa in list(self.section_tree.iter('{http://www.hancom.co.kr/hwpml/2011/paragraph}linesegarray')):
            lsa.getparent().remove(lsa)

        # section0.xml 저장
        section_path = os.path.join(self.temp_dir, 'Contents', 'section0.xml')

        # XML 선언 + 내용
        xml_bytes = etree.tostring(
            self.section_tree,
            encoding='UTF-8',
            xml_declaration=True,
            standalone=True
        )

        with open(section_path, 'wb') as f:
            f.write(xml_bytes)

        # header.xml 저장 (수정된 경우)
        if self._header_modified and self.header_tree is not None:
            header_path = os.path.join(self.temp_dir, 'Contents', 'header.xml')
            header_bytes = etree.tostring(
                self.header_tree,
                encoding='UTF-8',
                xml_declaration=True,
                standalone=True
            )
            with open(header_path, 'wb') as f:
                f.write(header_bytes)
        
        # 새 ZIP 파일로 압축 (mimetype을 첫 엔트리로, 비압축 — HWPX 표준)
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            mimetype_path = os.path.join(self.temp_dir, 'mimetype')
            if os.path.exists(mimetype_path):
                zf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
            for root, dirs, files in os.walk(self.temp_dir):
                for file in files:
                    if file == 'mimetype':
                        continue
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.temp_dir)
                    zf.write(file_path, arcname)
        
        return output_path
    
    def close(self):
        """임시 파일 정리"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def __enter__(self):
        return self.open()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def modify_hwpx_template(
    template_path: str,
    output_path: str,
    replacements: Dict[str, str]
) -> str:
    """
    HWPX 템플릿 파일의 텍스트를 치환하여 새 파일 생성
    
    Args:
        template_path: 템플릿 HWPX 파일 경로
        output_path: 출력 파일 경로
        replacements: {찾을텍스트: 바꿀텍스트} 딕셔너리
        
    Returns:
        저장된 파일 경로
        
    Example:
        modify_hwpx_template(
            "/mnt/user-data/uploads/template.hwpx",
            "/mnt/user-data/outputs/result.hwpx",
            {
                "{{학교명}}": "서울중광초등학교",
                "{{날짜}}": "2026. 1. 7.",
                "{{담당자}}": "임세범"
            }
        )
    """
    with HwpxModifier(template_path) as doc:
        results = doc.batch_replace(replacements)
        doc.save(output_path)
        
        # 결과 출력
        for old_text, count in results.items():
            print(f"'{old_text}' → {count}개 치환됨")
    
    return output_path


def analyze_hwpx_template(template_path: str, max_items: int = 100) -> str:
    """
    HWPX 템플릿 파일의 텍스트 구조 분석
    
    Args:
        template_path: HWPX 파일 경로
        max_items: 최대 출력 항목 수
        
    Returns:
        텍스트 요약 문자열
    """
    with HwpxModifier(template_path) as doc:
        return doc.get_text_summary(max_items)
