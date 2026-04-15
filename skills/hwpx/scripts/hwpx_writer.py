#!/usr/bin/env python3
"""
HWPX 문서 작성기 - 줄간격 수정 버전
hp:switch 구조를 사용하여 긴 문단의 줄간격이 올바르게 적용되도록 함
"""

import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET


# 네임스페이스 정의
NAMESPACES = {
    'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
    'hp10': 'http://www.hancom.co.kr/hwpml/2016/paragraph',
    'hh': 'http://www.hancom.co.kr/hwpml/2011/head',
    'hs': 'http://www.hancom.co.kr/hwpml/2011/section',
    'hc': 'http://www.hancom.co.kr/hwpml/2011/core',
    'hwpunitchar': 'http://www.hancom.co.kr/hwpml/2016/HwpUnitChar',
}


def create_line_spacing_xml(value: int = 160) -> str:
    """
    줄간격 XML 생성 - hp:switch 구조 사용
    
    Args:
        value: 줄간격 값 (130=좁음, 160=기본, 180=넉넉함, 200=넓음)
    
    Returns:
        줄간격 XML 문자열
    """
    return f'''<hp:switch xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:case hp:required-namespace="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar">
    <hh:margin xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" left="0" right="0" indent="0" prev="0" next="0"/>
    <hh:lineSpacing xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" type="PERCENT" value="{value}" unit="HWPUNIT"/>
  </hp:case>
  <hp:default>
    <hh:margin xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" left="0" right="0" indent="0" prev="0" next="0"/>
    <hh:lineSpacing xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" type="PERCENT" value="{value}" unit="HWPUNIT"/>
  </hp:default>
</hp:switch>'''


def create_paragraph_property(para_id: int, line_spacing: int = 160) -> str:
    """
    문단 속성 XML 생성
    
    Args:
        para_id: 문단 속성 ID
        line_spacing: 줄간격 값
    
    Returns:
        문단 속성 XML 문자열
    """
    return f'''<hh:paraPr id="{para_id}" xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head">
  <hh:align horizontal="JUSTIFY" vertical="BASELINE"/>
  <hp:switch xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
    <hp:case hp:required-namespace="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar">
      <hh:margin left="0" right="0" indent="0" prev="0" next="0"/>
      <hh:lineSpacing type="PERCENT" value="{line_spacing}" unit="HWPUNIT"/>
    </hp:case>
    <hp:default>
      <hh:margin left="0" right="0" indent="0" prev="0" next="0"/>
      <hh:lineSpacing type="PERCENT" value="{line_spacing}" unit="HWPUNIT"/>
    </hp:default>
  </hp:switch>
  <hh:border borderFillIDRef="1"/>
  <hh:autoSpacing eAsianEng="0" eAsianNum="0"/>
</hh:paraPr>'''


def patch_hwpx_line_spacing(hwpx_path: str, output_path: str, line_spacing: int = 160):
    """
    기존 HWPX 파일의 줄간격을 수정
    
    Args:
        hwpx_path: 입력 HWPX 파일 경로
        output_path: 출력 HWPX 파일 경로
        line_spacing: 줄간격 값
    """
    with zipfile.ZipFile(hwpx_path, 'r') as zf_in:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf_out:
            for item in zf_in.namelist():
                data = zf_in.read(item)
                
                # header.xml에서 줄간격 수정
                if item == 'Contents/header.xml':
                    content = data.decode('utf-8')
                    # 기존 lineSpacing을 hp:switch 구조로 교체
                    # (실제 구현시 XML 파싱하여 수정 필요)
                    zf_out.writestr(item, content)
                else:
                    zf_out.writestr(item, data)


# 줄간격 상수
LINE_SPACING_NARROW = 130   # 좁은 간격 - 공간 절약
LINE_SPACING_DEFAULT = 160  # 기본 간격 - 한글 프로그램 기본값
LINE_SPACING_COMFORTABLE = 180  # 넉넉한 간격 - 가독성 중요한 본문
LINE_SPACING_WIDE = 200     # 넓은 간격 - 제목, 강조 문단


if __name__ == "__main__":
    # 테스트: 줄간격 XML 출력
    print("=== 기본 줄간격 (160) ===")
    print(create_line_spacing_xml(160))
    print()
    print("=== 문단 속성 예시 ===")
    print(create_paragraph_property(0, 160))
