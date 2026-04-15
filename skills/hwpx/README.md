# hwpx-skill

HWPX(한컴오피스 한글 개방형 문서) 생성, 편집, 병합을 위한 Claude Code 커스텀 스킬.

## 기반

이 스킬은 [jkf87/hwpx-skill](https://github.com/jkf87/hwpx-skill)을 기반으로 하며, 추가 기능과 버그 수정을 포함합니다.

## 원본(jkf87) 대비 변경 사항

### 추가된 모듈

| 파일 | 기능 | 원본에 없는 이유 |
|------|------|------------------|
| `hwpx_modifier.py` | 기존 양식 세밀 수정 (정규식 치환, 인덱스 기반 수정, 문단 들여쓰기 제어) | 원본은 새 문서 생성 중심. 기존 문서의 문단 속성 세밀 조작 기능 없음 |
| `hwpx_form_filler.py` | 양식 부분 추출, 표 구조 분석, 좌표 기반 셀 채우기, 행 추가/복제 | 원본은 ZIP-level 문자열 치환만 지원. 표 구조 변경 불가 |
| `hwpx_writer.py` | hp:switch 구조 줄간격 XML 생성 | 원본에 줄간격 관련 함수 없음 |

### 코드 수정

| 파일 | 변경 내용 |
|------|-----------|
| `md2hwpx.py` | 표 열 너비: 균등 배분 → **내용 길이 비례 배분** (한글=2, ASCII=1 가중치). 셀 여백 확대 (좌우 1mm, 상하 0.5mm). `hasMargin="1"` 활성화 |
| `templates/report/header.xml` | 모든 paraPr의 `borderFillIDRef`를 `"1"`로 변경 (문단 가로선 제거). `diagonal type="SOLID"` → `"NONE"` |

### 추가된 워크플로우

| 워크플로우 | 용도 |
|-----------|------|
| **G** (HwpxModifier) | 기존 양식의 정규식 치환, 인덱스 수정, 들여쓰기 조정 |
| **H** (HwpxFormFiller) | 붙임/별지 섹션 추출, 표 좌표 기반 셀 채우기, 행 추가/복제 |
| **I** (병합) | 여러 HWPX 파일을 lxml 파서로 안전하게 병합 |

### SKILL.md 확장

- md2hwpx.py 직접 사용법 (`--template` 옵션) 문서화
- 이미지 인라인 삽입 전체 코드 예시 (ZIP 추가 + section0.xml hp:pic 삽입 2단계)
- HWPX 병합 코드 예시 (lxml 기반, ID 오프셋, 페이지 넘김)
- Critical Rules #16~22 추가

### 트러블슈팅 추가 (references/troubleshooting.md)

- "문단마다 가로선이 표시됨" — paraPr borderFillIDRef 원인 및 해결
- "이미지가 ZIP에는 있지만 문서에 안 보임" — 인라인 삽입 절차

## 설치

```bash
# Claude Code 스킬 디렉토리에 클론
git clone https://github.com/imsebeom/hwpx.git ~/.claude/skills/hwpx

# 의존성
pip install lxml Pillow
```

## 워크플로우 요약

| 워크플로우 | 용도 | 주요 도구 |
|-----------|------|-----------|
| A | 마크다운/텍스트 → HWPX | hwpx_helpers.py, md2hwpx.py |
| B | 템플릿 플레이스홀더 치환 | ZIP-level str.replace() |
| C | 기존 문서 XML 편집 | office/unpack.py → pack.py |
| D | 참조 양식 기반 새 문서 | analyze_template.py + build_hwpx.py |
| E | 읽기/텍스트 추출 | text_extract.py |
| F | 양식 복제 (구조 100% 보존) | clone_form.py |
| G | 세밀 수정 (정규식, 들여쓰기) | hwpx_modifier.py |
| H | 표 조작 (셀 채우기, 행 추가) | hwpx_form_filler.py |
| I | 여러 HWPX 병합 | lxml 기반 문단 복사 |

## 라이선스

원본 [jkf87/hwpx-skill](https://github.com/jkf87/hwpx-skill)의 라이선스를 따릅니다.
