---
name: paperbanana
description: "학술 삽화(다이어그램, 플롯) 자동 생성 스킬. 논문/PPT 품질의 방법론 다이어그램, 프레임워크 아키텍처, 흐름도, 통계 플롯을 Gemini 3.1 Flash Image로 생성한다. 사용 시점 - (1) PPT에 삽화/다이어그램을 넣을 때, (2) 문서에 학술 그림이 필요할 때, (3) 프레임워크/아키텍처 다이어그램을 만들 때, (4) 데이터 시각화 플롯이 필요할 때. 책이나 PPT 삽화 제작 시 기본적으로 사용한다."
invoke: "/paperbanana [설명 또는 텍스트파일 경로]"
---

# /paperbanana — 학술 삽화 자동 생성 (Gemini 3.1 Flash Image)

## 개요

텍스트 설명으로부터 논문·PPT 품질의 학술 다이어그램, 통계 플롯, 프레임워크 아키텍처, 흐름도를 생성한다. 내부 엔진은 **Gemini 3.1 Flash Image Preview** (`gemini-3.1-flash-image-preview`).

> **2026-05-04 갱신** — 강사 본인 셋팅에서 Gemini 3.1 Flash Image Preview vs OpenAI gpt-image-2 비교(같은 한국어 4단계 워크플로 도식 프롬프트) 결과, Gemini 3.1이 속도(약 7배 빠름)·가독성·비용(약 7배 저렴)·강의장 동시 호출 안전성 모두 우세로 판정되어 Gemini 라인을 기본으로 한다.

## 사전 요구사항

- **Gemini API 키**. 다음 중 한 곳에서 자동 로드:
  - 환경변수 `GEMINI_API_KEY`
  - 파일 `~/.claude/apikeys/gemini` (한 줄에 키만)
  - 강의 당일은 강사가 일회용 키를 공유 → 위 파일에 저장하면 바로 사용 가능
- **Python SDK**: `pip install -U google-genai`

## 사용법

### 1. 기본 호출

```python
"""/paperbanana: Gemini 3.1 Flash Image로 학술 삽화 생성."""
from __future__ import annotations

import os
import pathlib
import sys

from google import genai
from google.genai import types

sys.stdout.reconfigure(encoding="utf-8")


def _load_gemini_key() -> str:
    """환경변수 우선, 없으면 ~/.claude/apikeys/gemini."""
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key.strip()
    p = pathlib.Path.home() / ".claude" / "apikeys" / "gemini"
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    raise RuntimeError(
        "Gemini API 키를 찾을 수 없습니다. "
        "환경변수 GEMINI_API_KEY 또는 ~/.claude/apikeys/gemini 파일에 키를 저장하세요."
    )


client = genai.Client(api_key=_load_gemini_key())

# 사용자 설명 + 학술 스타일 접두 + 한글 명시
user_desc = "{{사용자 설명}}"
caption = "{{캡션 또는 의도 설명}}"
korean_labels = True

style_prefix = (
    "Academic diagram, publication quality, clean vector illustration style, "
    "IEEE/CVPR figure aesthetic. White background, minimal ornamentation, "
    "clear labels, logical spatial layout, directional arrows where meaningful."
)
lang_hint = (
    "All labels and text must be in Korean (한국어). Use clear sans-serif Korean font (Pretendard style). "
    "Korean text must be rendered correctly and legibly."
    if korean_labels else
    "All labels in English, serif or sans-serif academic font."
)

prompt = f"{style_prefix}\n\n{user_desc}\n\nCaption/intent: {caption}\n\n{lang_hint}"

response = client.models.generate_content(
    model="gemini-3.1-flash-image-preview",
    contents=prompt,
    config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
)

out_path = pathlib.Path("{{저장경로}}")
saved = False
for cand in response.candidates or []:
    for part in (cand.content.parts if cand.content else []):
        inline = getattr(part, "inline_data", None)
        if inline and inline.data:
            out_path.write_bytes(inline.data)
            saved = True
            break
    if saved:
        break

if not saved:
    raise RuntimeError(f"이미지 응답 없음: {response}")

print(f"학술 삽화 저장: {out_path} ({out_path.stat().st_size/1024:.1f}KB)")
```

### 2. 삽화 유형별 프롬프트 템플릿

**방법론 다이어그램 / 프레임워크**
- 스타일 접두에 `methodology diagram, modular boxes connected by arrows, hierarchical layout, numbered stages` 추가

**시스템 아키텍처**
- 스타일 접두에 `system architecture diagram, layered boxes (input / processing / output), icons for each component, data flow arrows` 추가

**흐름도 (Flowchart)**
- 가로 흐름: `left-to-right horizontal workflow flowchart`
- 세로 흐름: `top-to-bottom flowchart with decision diamonds and process rectangles`

**통계 플롯**
- 스타일 접두에 `academic statistical plot, matplotlib-like aesthetic, axis labels, legend, gridlines, no 3D effects` 추가
- 실제 수치가 필요하면 matplotlib 직접 호출이 더 정확

### 3. 색·해상도 힌트

가로 다이어그램은 프롬프트 끝에 `(Landscape 16:9 aspect ratio, wide horizontal layout)`, 세로 포스터는 `(Portrait 9:16 aspect ratio)` 추가.

색상 지정은 hex로:
```
Color palette:
- Box fill: deep teal #0F3D44
- Box text: cream #F5F2ED
- Background: cream #F5F2ED
- Arrows: orange #E08A4E
```

### 4. 반복 개선

한 번에 안 나오면 프롬프트를 다듬어 재생성. 같은 seed가 없으므로 매번 새 이미지.

체크리스트:
- 레이아웃 방향 명시 (top-to-bottom / left-to-right)
- 박스 개수 구체적 (3, 5, 7 등)
- 색상 팔레트 hex로
- 캡션 별도 명시

## 품질·비용

- Gemini 3.1 Flash Image Preview: **약 $0.039 / 장**
- 생성 시간: **15~25초 / 장**
- 해상도: 모델 자동 결정, aspect ratio 힌트로 비율만 유도

## 한글 지원

Gemini 3.1은 한글 제목·헤더·단계 라벨·캡션을 또렷한 큰 폰트로 렌더링한다. 매우 작은 본문 글씨는 PPT/문서에서 덮어 얹는 방식 권장.

## 폴백 (선택)

Gemini가 지속 실패하거나 사용자가 명시 요청하면 OpenAI `gpt-image-2`로 폴백. 환경변수 `OPENAI_API_KEY` 또는 `~/.claude/apikeys/gpt`에서 키 로드. 폴백은 **사용자 승인 후에만**.

## 제한사항

- API 호출 비용 발생 (저렴)
- 인터넷 연결 필요
- 매우 복잡한 수식·특수 기호는 LaTeX 렌더링이 더 정확
- 정확한 수치 통계 플롯은 matplotlib 직접이 더 적합

## SDK 설치

```bash
pip install -U google-genai
```
