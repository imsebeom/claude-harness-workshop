---
name: paperbanana
description: "PaperBanana를 사용하여 학술 삽화(다이어그램, 플롯)를 자동 생성하는 스킬. 텍스트 설명으로부터 논문/PPT 품질의 방법론 다이어그램, 통계 플롯 등을 생성한다. 사용 시점 - (1) PPT에 삽화/다이어그램을 넣을 때, (2) 문서에 학술 그림이 필요할 때, (3) 프레임워크/아키텍처 다이어그램을 만들 때, (4) 데이터 시각화 플롯이 필요할 때. 책이나 PPT 삽화 제작 시 기본적으로 사용한다."
invoke: "/paperbanana [설명 또는 텍스트파일 경로]"
---

# PaperBanana - 학술 삽화 자동 생성

## 개요

PaperBanana는 텍스트 설명으로부터 논문 품질의 학술 다이어그램과 통계 플롯을 자동 생성하는 도구이다.
5개 에이전트(Retriever, Planner, Stylist, Visualizer, Critic)가 협업하여 반복적으로 품질을 개선한다.

- GitHub (커뮤니티): https://github.com/llmsresearch/paperbanana
- 라이선스: MIT

## 사전 요구사항

```bash
pip install paperbanana
```

- Gemini API 키 필요: `/apikeys`에서 `gemini` 키 참조
- 환경변수 `GOOGLE_API_KEY` 설정 필요

## 사용법

### 1. 다이어그램 생성 (기본)

사용자가 설명 텍스트를 직접 제공한 경우:

```python
import os
import sys
import shutil
import asyncio

os.environ["GOOGLE_API_KEY"] = "GEMINI_API_KEY_HERE"

from paperbanana.core.config import Settings
from paperbanana import PaperBananaPipeline, GenerationInput

# Settings로 모델과 출력 경로를 설정한다 (image_model, output_dir 등)
settings = Settings(
    image_model="gemini-3.1-flash-image-preview",
    refinement_iterations=2,
    output_dir="출력_폴더_경로",
)

pipeline = PaperBananaPipeline(settings=settings)
result = asyncio.run(pipeline.generate(
    GenerationInput(
        source_context="프레임워크 설명 텍스트",
        communicative_intent="다이어그램 캡션. 모든 라벨과 텍스트를 한국어로 작성할 것."
    )
))
# result.image_path에 생성된 이미지 경로
# 원하는 위치로 복사: shutil.copy2(result.image_path, "output.png")
```

**주의**: `image_model`, `refinement_iterations` 등은 반드시 `Settings` 객체로 전달한다. `pipeline.generate()`에 직접 전달하면 오류 발생.

### 2. CLI 방식 (권장)

```python
import os
import subprocess

os.environ["GOOGLE_API_KEY"] = "GEMINI_API_KEY_HERE"

# 방법 텍스트를 파일로 저장
method_file = "method.txt"
with open(method_file, "w", encoding="utf-8") as f:
    f.write("프레임워크 설명 텍스트")

# paperbanana CLI 실행
subprocess.run([
    sys.executable, "-c",
    f"import sys; sys.argv = ['paperbanana', 'generate', "
    f"'-i', '{method_file}', "
    f"'-c', '캡션. 모든 라벨과 텍스트를 한국어로 작성할 것.', "
    f"'-o', 'output.png', "
    f"'-n', '2']; "
    f"from paperbanana.cli import app; app()"
], env={**os.environ})
```

### 3. 플롯 생성

```python
# CSV 데이터에서 플롯 생성
subprocess.run([
    sys.executable, "-c",
    f"import sys; sys.argv = ['paperbanana', 'plot', "
    f"'--data', 'results.csv', "
    f"'--intent', '벤치마크별 모델 정확도 비교']; "
    f"from paperbanana.cli import app; app()"
], env={**os.environ})
```

## 실행 워크플로우

1. **작업 폴더 준비**: 출력할 경로를 확정한다.
2. **환경변수 설정**: `/apikeys`에서 gemini 키를 가져와 `GOOGLE_API_KEY`로 설정한다.
3. **입력 텍스트 준비**: 사용자의 설명을 텍스트 파일로 저장하거나 직접 전달한다.
4. **캡션 구성**:
   - 한글 다이어그램이 필요하면 캡션 끝에 "모든 라벨과 텍스트를 한국어로 작성할 것." 추가
   - 영어 다이어그램은 캡션만 지정
5. **생성 실행**: CLI 또는 Python API로 실행 (iterations 기본값: 2)
6. **결과 확인**: 생성된 PNG 이미지를 확인하고 필요 시 PPT/문서에 삽입한다.

## 주요 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--input` / `-i` | 방법론 텍스트 파일 경로 | (필수) |
| `--caption` / `-c` | 그림 캡션 / 의도 설명 | (필수) |
| `--output` / `-o` | 출력 이미지 경로 | 자동 생성 |
| `--iterations` / `-n` | 개선 반복 횟수 | 3 |
| `--vlm-model` | VLM 모델명 | gemini-2.0-flash |
| `--image-model` | 이미지 생성 모델명 | gemini-3.1-flash-image-preview |

## 한글 지원

캡션에 "모든 라벨과 텍스트를 한국어로 작성할 것."을 포함하면 다이어그램 내 모든 텍스트가 한글로 렌더링된다.
입력 텍스트(method)는 한글 또는 영어 모두 가능하다.

## 제한사항

- Gemini API 호출 비용 발생 (이미지 생성당 ~30초)
- 반복 횟수에 따라 1~3분 소요
- 인터넷 연결 필요
- 참조 인덱스(reference_sets) 없이도 동작하나, 있으면 품질 향상
