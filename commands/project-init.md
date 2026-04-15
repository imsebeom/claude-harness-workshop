---
description: "새 프로젝트 표준 구조 초기화. /project-init [유형] [주제]. 유형: webapp, document, research (기본: webapp)"
allowed-tools: Bash(mkdir *), Bash(git *), Write, Read, Glob
---

# 프로젝트 초기화 커맨드

사용자가 지정한 유형과 주제로 표준 프로젝트 구조를 생성한다.

## 인자 파싱
- 첫 번째 인자: 유형 (webapp | document | research). 없으면 webapp
- 나머지: 주제 설명 (한국어 가능)

## 폴더명
- 형식: `YYYYMMDD-HHMMSS-주제` (현재 시각 기준)
- 현재 작업 디렉토리 하위에 생성

## 유형별 구조

### webapp (기본)
```
YYYYMMDD-HHMMSS-주제/
├── CLAUDE.md
├── .gitignore
└── (빈 상태, 사용자가 파일 추가)
```

### document (문서 생성)
```
YYYYMMDD-HHMMSS-주제/
├── CLAUDE.md
├── .gitignore
├── sources/        # 원본 자료
└── output/         # 생성된 문서
```

### research (리서치/분석)
```
YYYYMMDD-HHMMSS-주제/
├── CLAUDE.md
├── .gitignore
├── data/           # 수집 데이터
└── analysis/       # 분석 결과
```

## .gitignore 내용
```
node_modules/
__pycache__/
*.pyc
.env
*.bak
*.tmp
.DS_Store
Thumbs.db
```

## CLAUDE.md 템플릿
```markdown
# [주제]

## 프로젝트 정보
- 유형: [webapp | document | research]
- 생성일: YYYY-MM-DD
- 목적: [사용자가 제공한 주제 설명]

## 규칙
- [유형별 특화 규칙이 있으면 추가]

## 작업 이력
<!-- 각 작업 단계 완료 시 여기에 기록 -->
```

## 실행 절차
1. 현재 시각으로 폴더명 생성
2. 유형에 따른 하위 폴더 생성
3. CLAUDE.md 작성
4. .gitignore 작성
5. `git init` 실행
6. 초기 커밋: `chore: 프로젝트 초기화`
7. 생성된 경로와 구조를 사용자에게 보고
