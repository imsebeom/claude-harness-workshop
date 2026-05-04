---
name: paperbanana
description: "학술 삽화(다이어그램, 플롯) 자동 생성 스킬. 논문/PPT 품질의 방법론 다이어그램, 프레임워크 아키텍처, 흐름도, 통계 플롯을 paperbanana 7-에이전트 파이프라인(VLM + Image Gen + Critic)으로 생성한다. 사용 시점 - (1) PPT에 삽화/다이어그램을 넣을 때, (2) 문서에 학술 그림이 필요할 때, (3) 프레임워크/아키텍처 다이어그램을 만들 때, (4) 데이터 시각화 플롯이 필요할 때. 책이나 PPT 삽화 제작 시 기본적으로 사용한다."
invoke: "/paperbanana [설명 또는 텍스트파일 경로]"
---

# /paperbanana — 학술 삽화 자동 생성 (paperbanana 7-에이전트 파이프라인)

## 개요

텍스트 설명으로부터 논문·PPT 품질의 학술 다이어그램, 통계 플롯, 프레임워크 아키텍처, 흐름도를 생성한다. 내부 엔진은 [llmsresearch/paperbanana](https://github.com/llmsresearch/paperbanana) Python 패키지 — **7-에이전트 파이프라인 + Critic 자기 비평 루프 내장**.

> **2026-05-04 갱신** — 단발 Gemini Flash 호출에서 paperbanana 패키지로 전면 복귀. 비교 테스트(같은 분기형 워크플로 도식)에서 Flash 단발은 분기·아키텍처 같은 복잡 도식을 한 번에 못 잡았으나, 패키지의 7-에이전트 + Critic 자동 비평이 그 자리에서 정리. 정보 밀도·학술 완성도·반복 안정성 모두 우세.
>
> 트레이드오프: 한 장당 60~180초 (Flash 18~25초 대비 7~9배 느림). 강의장 동시 호출 시 `max_iterations=1` 압축 모드 권장 (4번 참조).

## 7-에이전트 파이프라인

| Phase | 에이전트 | 역할 |
|-------|---------|------|
| Phase 0 (선택) | Context Enricher + Caption Sharpener | 입력 정제 (`optimize_inputs=True`) |
| Phase 1 | Retriever + Planner + Stylist | 참조 검색 + NeurIPS 스타일 계획 |
| Phase 2 | Visualizer + **Critic** | 렌더 → 자기 비평 → 반복 (`auto_refine=True`) |

## 사전 요구사항

- **Python 패키지**: `pip install paperbanana` (첫 호출 시 자동 설치 가능)
- **Gemini API 키**: 다음 중 한 곳에서 자동 로드
  - 환경변수 `GOOGLE_API_KEY` 또는 `GEMINI_API_KEY`
  - 파일 `~/.claude/apikeys/gemini`
  - 강의 당일은 강사가 일회용 키를 공유 → 위 파일에 저장하면 바로 사용

## 사용법

### 1. 표준 호출 (방법론 다이어그램, 학술급 품질)

```python
"""/paperbanana: paperbanana 7-에이전트 파이프라인."""
from __future__ import annotations

import asyncio
import os
import pathlib
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")


def _load_gemini_key():
    """환경변수 우선, 없으면 ~/.claude/apikeys/gemini."""
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if key:
        return key.strip()
    p = pathlib.Path.home() / ".claude" / "apikeys" / "gemini"
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    raise RuntimeError(
        "Gemini API 키를 찾을 수 없습니다. "
        "환경변수 GOOGLE_API_KEY 또는 ~/.claude/apikeys/gemini 파일에 키를 저장하세요."
    )


os.environ["GOOGLE_API_KEY"] = _load_gemini_key()

from paperbanana import PaperBananaPipeline, GenerationInput, DiagramType
from paperbanana.core.config import Settings

settings = Settings(
    vlm_provider="gemini",
    vlm_model="gemini-2.0-flash",
    image_provider="google_imagen",
    image_model="gemini-3-pro-image-preview",
    optimize_inputs=True,    # Phase 0 입력 정제
    auto_refine=True,        # Critic 자동 비평 루프
    max_iterations=3,        # 기본 3회 반복
)

pipeline = PaperBananaPipeline(settings=settings)

source = """{{사용자 도식 설명 — 풍부한 맥락이 핵심}}"""
intent = "{{한 줄 캡션 + 시각 의도 + 색상·폰트·레이아웃 힌트}}"


async def main():
    result = await pipeline.generate(GenerationInput(
        source_context=source,
        communicative_intent=intent,
        diagram_type=DiagramType.METHODOLOGY,  # 또는 STATISTICAL_PLOT
    ))
    out = pathlib.Path("{{저장경로}}")
    shutil.copy(result.image_path, out)
    print(f"saved: {out} ({out.stat().st_size/1024:.1f}KB)")


asyncio.run(main())
```

### 2. 다이어그램 유형

```python
from paperbanana import DiagramType

DiagramType.METHODOLOGY      # 시스템 다이어그램, 아키텍처, 워크플로
DiagramType.STATISTICAL_PLOT # 막대/선/산점도 등 데이터 시각화
```

### 3. source_context 작성 가이드

`source_context`는 paperbanana의 핵심 입력. **단순 한 줄 묘사가 아니라 풍부한 맥락**을 넣어야 7-에이전트가 제대로 동작한다.

좋은 예시 구조:
```
[작업명] 자동화 워크플로 — [도메인 한 줄 설명].

트리거: [무엇이 시작 신호인가, 누가 어떻게 호출하는가]

분기 (해당 시): [3-way / 2-way 등 분기 조건과 각 경로 설명]

처리: [각 단계 1~N의 구체적 동작]

검증: [어떤 식으로 결과가 검증되는가]

저장: [결과가 어디에 어떻게 저장되는가]
```

### 4. 강의장 동시 호출 압축 모드

연수·강의장에서 30명이 동시 호출하면 표준 모드(60~180초/장)는 부담. 압축 모드:

```python
settings = Settings(
    vlm_provider="gemini",
    image_provider="google_imagen",
    image_model="gemini-3-pro-image-preview",
    optimize_inputs=False,   # Phase 0 생략
    auto_refine=False,       # Critic 비평 생략
    max_iterations=1,        # 1회만
)
```

이 경우 한 장당 약 30~50초. 학술 완성도는 표준 모드보다 낮지만 강의장 흐름엔 적합.

### 5. 결과 재개 (Resume)

복잡 도식이라 한 번에 마음에 안 들면 추가 반복:

```python
from paperbanana.core.resume import load_resume_state

state = load_resume_state("outputs", "run_20260504_224424_bc34c3")
result = await pipeline.continue_run(
    resume_state=state,
    additional_iterations=3,
    user_feedback="검증 박스에서 처리 박스로 가는 화살표를 더 굵게",
)
```

## 색·해상도 힌트

`communicative_intent`에 hex 색상 명시:
```
색은 짙은 청록 #0F3D44 박스 + 크림 #F5F2ED 배경/텍스트 + 주황 #E08A4E 화살표.
박스 안 텍스트 모두 한글. Pretendard 한글 산세리프, 학술 다이어그램 깔끔한 벡터.
```

가로/세로 비율도 intent 안에 한 줄로 (Landscape 16:9 / Portrait 3:4 등).

## 품질·비용·시간

| 모드 | 시간/장 | 품질 | 추천 사용처 |
|------|--------|------|------------|
| 표준 (`max_iterations=3` + Critic) | 60~180초 | 학술 논문급 | 본인 작업, 논문 그림, 복잡 분기·아키텍처 |
| 압축 (`max_iterations=1`) | 30~50초 | 발표 자료급 | 강의장 동시 호출, 빠른 시연 |

비용: Gemini 무료 티어 한도 내면 사실상 0원. 한도 초과 시 `gemini-3-pro-image-preview` 단가 적용.

## MCP 서버 통합 (선택)

Claude Code 설정에서 paperbanana를 MCP 서버로 직접 등록 가능:

```json
{
  "mcpServers": {
    "paperbanana": {
      "command": "uvx",
      "args": ["--from", "paperbanana[mcp]", "paperbanana-mcp"],
      "env": { "GOOGLE_API_KEY": "{{키}}" }
    }
  }
}
```

MCP 도구: `generate_diagram`, `generate_plot`, `evaluate_diagram`, `evaluate_plot`.

## 폴백 (선택)

패키지 호출 실패하거나 시간 부족 시 단발 Gemini Flash 호출(`gemini-3.1-flash-image-preview`)로 폴백 가능. 사용자 승인 후에만.

## 제한사항

- 한 장당 최대 3분 (auto_refine 시)
- 인터넷 연결 필요
- 매우 복잡한 수식·특수 기호는 LaTeX 렌더링이 더 정확
- 정확한 수치 통계 플롯은 matplotlib 직접이 더 적합

## 첫 호출 시 자동 설치

스킬이 호출될 때 `import paperbanana`가 ImportError를 던지면, 자동으로 `pip install paperbanana`를 한 번 실행한 뒤 재시도한다 (사용자 승인 후).
