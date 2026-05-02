# Claude Code Harness Workshop — 글로벌 지침

> 2026 몽당분필 오픈 연수 *The Core, Masterclass* — "클로드 코드 하네스 활용" 강의용 슬림판입니다.
> 강사 임세범의 풀버전 하네스에서 **워크숍에 필요한 핵심만** 발췌했습니다.
> 강의 후에는 본인 작업에 맞게 자유롭게 수정/확장하세요.

## 기본 원칙
- **한국어로 사고하고 대화하라.**
- 모델은 sonnet 고정. (Claude Code Pro 요금제 한도 보호)
- thinking effort는 medium 권장. 새 세션 시작 시 `/effort` → 메뉴에서 medium 선택. (Pro 5시간 한도 보호 — high는 thinking 토큰을 많이 태운다. xhigh는 정말 어려운 한 문제에만 한 번 쓰고 끄는 용도)
- 파일 수정 전 반드시 먼저 읽을 것.
- 복잡한 작업은 plan 모드로 시작.

## Windows 한국어 환경
- Python 실행 시 `PYTHONIOENCODING=utf-8` 환경변수 사용. 한글 파일명/텍스트 인코딩 오류 방지.
- 스크립트 내부에서는 `sys.stdout.reconfigure(encoding='utf-8')` 가능.

## 도구 선호
- **HTML ebook 변환** (PDF/DOCX → 모바일 친화 HTML): `/html` 스킬
- **PDF 변환** (HWP/HWPX → PDF, PDF → 이미지): `/pdf` 스킬
- **마크다운 변환** (PDF/논문/영상 → AI가 읽기 좋은 마크다운): `/md` 스킬
- **한글 문서(.hwpx) 작성·편집**: `/hwpx` 스킬
- **학술 다이어그램·삽화**: `/paperbanana` 스킬

## 하네스 엔지니어링 원칙

### 완료 조건 합의 (강사 셋팅 용어로는 "스프린트 계약")
- 복잡한 작업(3단계 이상, 파일 3개 이상) 착수 전, **완료 조건 3줄**을 먼저 제시하고 합의하라.
- 형식: `## 완료 조건` → 체크리스트 3항목 (측정 가능한 기준)
- 모호한 조건("잘 동작하면")은 계약 무효. 구체적 기준("X 파일 생성, Y 함수 동작, Z 출력 확인")으로 작성.

### 컨텍스트 앵커
- 다중 세션 작업 시 프로젝트 `CLAUDE.md`에 다음 4줄을 유지하라:
  ```
  ## 컨텍스트 앵커
  - intent: 현재/마지막 세션 목적
  - changes_made: 완료된 변경 사항
  - decisions: 핵심 결정과 이유
  - next_steps: 다음 세션에서 할 일
  ```
- 세션 종료 또는 작업 단계 완료 시 갱신.

### 품질 체크포인트
- 스크립트 50줄 이상 작성 시, 완성 후 한번 실행하여 기본 동작 확인.
- 문서 생성(hwpx/docx/pptx) 후 시각적 확인 권장.

## Git 규칙
- 프로젝트 폴더 작업 시작 전, `.git`이 없으면 `git init`.
- 의미 있는 단위로 커밋. 형식: `<type>: <한국어 설명>` (feat/fix/docs/refactor/chore)

## Firebase 배포
- 정적 사이트(HTML ebook 등) 배포는 Firebase Hosting 사용.
- `npm i -g firebase-tools` → `firebase login` → `firebase init hosting` → `firebase deploy`
- public 폴더에 `index.html` 배치 → 한국어 파일명 주의.

## 작업 기록 원칙
- 프로젝트에 `CLAUDE.md`가 없으면 첫 작업 시 생성.
- 각 단계가 끝날 때마다 진행 상황을 프로젝트 `CLAUDE.md`에 반영.
- 완료/미완료 상태, 핵심 결정 사항, 파일 변경 이력을 기록.
