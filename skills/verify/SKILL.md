---
name: verify
description: "결과물 경량 검증 스킬. '결과물 검증', '제대로 만들어졌는지 확인', '/verify' 등 파일 유형별로 빠르게 검증할 때 사용. /verify [파일경로]"
---

# 결과물 검증 커맨드

지정된 파일(또는 마지막 생성 파일)의 무결성을 검증한다.

## 인자
- 파일 경로가 주어지면 해당 파일 검증
- 없으면 현재 디렉토리에서 가장 최근 수정된 결과물 파일 자동 탐지

## 파일 유형별 검증

### Python (.py)
1. `ruff check <file>` — 린트 오류 확인
2. `python -c "import ast; ast.parse(open('<file>').read())"` — 문법 검증
3. 50줄 이상이면 `python <file>` 실행 시도 (import 오류 확인)

### HWPX (.hwpx)
1. `unzip -t <file>` — ZIP 구조 무결성
2. ZIP 내 `Contents/content.hpf` 존재 확인
3. 파일 크기 > 0 확인

### DOCX (.docx)
1. `unzip -t <file>` — ZIP 구조 무결성
2. `python -c "from docx import Document; Document('<file>')"` — 로드 테스트
3. 파일 크기 > 0 확인

### PPTX (.pptx)
1. `unzip -t <file>` — ZIP 구조 무결성
2. `python -c "from pptx import Presentation; p=Presentation('<file>'); print(f'슬라이드 {len(p.slides)}장')"` — 로드 + 슬라이드 수
3. 파일 크기 > 0 확인

### HTML (.html)
1. 파일 크기 > 0 확인
2. `<html` 또는 `<!DOCTYPE` 태그 존재 확인
3. 로컬 서버 열기 제안 (`python -m http.server`)

### 이미지 (.png, .jpg, .gif, .svg)
1. 파일 크기 > 0 확인
2. `file <file>` — MIME 타입 확인

### PDF (.pdf)
1. 파일 크기 > 0 확인
2. `file <file>` — PDF 헤더 확인

## 공통 검증
- 파일 크기 0이면 **실패**
- 파일이 존재하지 않으면 **실패**
- 예상 대비 10배 이상 크면 **경고**

## 출력 형식
```
검증 결과: [파일명]
- 유형: [감지된 유형]
- 크기: [파일 크기]
- 구조: OK / FAIL
- 내용: OK / FAIL / WARNING
- 종합: PASS / FAIL
```
