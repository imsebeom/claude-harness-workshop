---
name: paperbanana
description: "학술 삽화(다이어그램, 플롯) 자동 생성 스킬. 논문/PPT 품질의 방법론 다이어그램, 프레임워크 아키텍처, 흐름도, 통계 플롯을 gpt-image-2로 생성한다. 사용 시점 - (1) PPT에 삽화/다이어그램을 넣을 때, (2) 문서에 학술 그림이 필요할 때, (3) 프레임워크/아키텍처 다이어그램을 만들 때, (4) 데이터 시각화 플롯이 필요할 때. 책이나 PPT 삽화 제작 시 기본적으로 사용한다."
invoke: "/paperbanana [설명 또는 텍스트파일 경로]"
---

# /paperbanana — 학술 삽화 자동 생성 (gpt-image-2)

## 개요

텍스트 설명으로부터 논문·PPT 품질의 학술 다이어그램, 통계 플롯, 프레임워크 아키텍처, 흐름도를 생성한다. 내부 엔진은 OpenAI **gpt-image-2** (2026-04 출시, 한글 텍스트 렌더링·월드 지식 강점).

> 역사적으로 이 스킬은 `paperbanana` Python 패키지(Gemini 5-에이전트 파이프라인)를 사용했으나, gpt-image-2가 단발 호출만으로도 학술 다이어그램 품질을 충분히 확보하여 2026-04 이후 직접 API 호출 방식으로 단순화했다. 레거시 PaperBanana 패키지 사용법은 `legacy-paperbanana.md` 참조.

## 사전 요구사항

- OpenAI API 키: `/apikeys`에서 `gpt` 키 참조
- Python SDK: `openai >= 2.29`

## 사용법

### 1. 기본 호출

```python
"""/paperbanana: gpt-image-2로 학술 삽화 생성."""
from __future__ import annotations

import base64
import pathlib
import sys

from openai import OpenAI

sys.stdout.reconfigure(encoding="utf-8")

client = OpenAI(api_key="{{GPT_API_KEY}}")

# 사용자 설명 + 학술 스타일 접두
user_desc = "{{사용자 설명}}"
caption = "{{캡션 또는 의도 설명}}"
korean_labels = True  # 한글 라벨 여부

style_prefix = (
    "Academic diagram, publication quality, clean vector illustration style, "
    "IEEE/CVPR figure aesthetic. White background, minimal ornamentation, "
    "clear labels, logical spatial layout, directional arrows where meaningful."
)
lang_hint = (
    "All labels and text must be in Korean (한국어). Use clear sans-serif Korean font."
    if korean_labels else
    "All labels in English, serif or sans-serif academic font."
)

prompt = f"{style_prefix}\n\n{user_desc}\n\nCaption/intent: {caption}\n\n{lang_hint}"

res = client.images.generate(
    model="gpt-image-2",
    prompt=prompt,
    size="1536x1024",      # 가로 다이어그램 기본. 세로면 1024x1536
    quality="high",        # 학술 삽화는 텍스트·디테일이 중요하므로 high 기본
    n=1,
)

item = res.data[0]
out_path = pathlib.Path("{{저장경로}}")
if getattr(item, "b64_json", None):
    out_path.write_bytes(base64.b64decode(item.b64_json))
elif getattr(item, "url", None):
    import urllib.request
    urllib.request.urlretrieve(item.url, out_path)
print(f"학술 삽화 저장: {out_path} ({out_path.stat().st_size/1024:.1f}KB)")
```

### 2. 삽화 유형별 프롬프트 템플릿

사용자 요청 성격에 따라 아래 템플릿을 조합한다.

**방법론 다이어그램 / 프레임워크**
- 스타일 접두에 `methodology diagram, modular boxes connected by arrows, hierarchical layout, numbered stages` 추가

**시스템 아키텍처**
- 스타일 접두에 `system architecture diagram, layered boxes (input / processing / output), icons for each component, data flow arrows` 추가

**흐름도 (Flowchart)**
- 스타일 접두에 `flowchart with decision diamonds and process rectangles, top-to-bottom flow, clear branching` 추가

**통계 플롯** (막대/라인/산점도)
- 스타일 접두에 `academic statistical plot, matplotlib-like aesthetic, axis labels, legend, gridlines, no 3D effects` 추가
- 실제 수치가 필요하면 사용자에게 CSV·숫자 제공 요청

### 3. 반복 개선 (선택)

한 번에 원하는 결과가 안 나오면 프롬프트를 다듬어 재생성한다. gpt-image-2는 같은 seed가 없으므로 매번 새 이미지가 나온다.

프롬프트 다듬기 체크리스트:
- 레이아웃 방향을 명시했는가 (top-to-bottom / left-to-right / radial)
- 박스/노드 개수를 구체적으로 썼는가 (3, 5, 7 등)
- 색상 팔레트를 지정했는가 (monochrome blue / pastel / corporate)
- 텍스트 위치를 지정했는가 (inside box / below arrow)

## 품질·비용

- 1536×1024 `high` 품질: 약 $0.25~0.30 / 장
- 1024×1024 `high`: 약 $0.211 / 장
- 1024×1024 `medium`: 약 $0.053 / 장 (초안용)

생성 시간: 60~90초 / 장

## 한글 지원

gpt-image-2는 한글 제목·헤더·단계 라벨을 또렷하게 렌더링한다. 다만 **본문 설명 같은 작은 글씨는 일부 깨질 수 있으므로**, 중요한 설명 텍스트는 PPT/문서에서 덮어 얹는 방식을 권장한다.

## 제한사항

- OpenAI API 호출 비용 발생
- 인터넷 연결 필요
- 매우 복잡한 수식·특수 기호는 LaTeX 렌더링이 더 정확 (matplotlib·TikZ 병행 고려)
- 정확한 수치가 필요한 통계 플롯은 실제 데이터 기반 matplotlib 스크립트가 더 적합
