# 4차시 강의 커리큘럼

> **2026 몽당분필 오픈 연수 *The Core, Masterclass*** — 클로드 코드 하네스 활용
> 강사: **임세범** / 일시: 2026-05-09(토) 13:00–17:30 / 장소: 서울교육대학교

## 개요

- **대상**: Claude Code Pro 요금제 사용자 ~30명 (설치만 해 본 사람 ~ 매일 쓰는 사람)
- **핵심 메시지**: *"AI가 못해서가 아니라, 일할 환경(=하네스)이 부족해서다."*
- **모델**: sonnet 고정 (Pro 한도 보호)
- **관통 자료**: Nature 논문 `s41467-025-59906-9` 한 편 → 변환 → 배포까지 단일 스토리

---

## 1교시 (13:00–13:50) — 기초 + 초반 셋팅

### 도입 (5분, 13:00–13:05) — 동기유발
- **영상**: 앤트로픽 Drew Bent, *"남들보다 빨리 쓴다고 AI 잘 쓰는 게 아니에요"* https://youtu.be/XwjfzwR4XO0
- 한 줄 멘트: *"오늘은 빨리 쓰는 법이 아니라, 오래 쓰는 법을 배웁니다."*

### 강사 결과물 갤러리 (5분, 13:05–13:10) — "오늘 끝나면 만들 수 있는 것"
강사가 클로드 코드로 만든 웹앱들을 화면으로 빠르게:
1. **앙부일구** — 천문 시뮬레이터
2. **지층과 화석 시뮬레이션** — 과학 수업 도구
3. **한강물의여정** — 사회·환경 인터랙티브
4. **elesurvey** — 초등 설문 플랫폼
5. **easyup** — EleUp 과제·질문판
6. **e-gpt (egpt.kr)** — 강사 본인 사이트

> *"이거 다 클로드 코드로 만들었습니다. 오늘 셋팅 끝나면 여러분도 시작할 수 있습니다."*

### 개념 (10분, 13:10–13:20)
- 답을 받는 일 ≠ 일을 끝내는 일 (오픈클로 책 프롤로그 인용 — **출처: 호암중 교사 박권**)
- "AI 눈에 안 보이는 것은 존재하지 않는다"
- 하네스 정의: 썰매 마구처럼 AI를 둘러싼 환경 전체 (egpt.kr/harness-engineering)

### Claude Code 설치 from zero (15분, 13:20–13:35)
1. Node.js 설치 확인 (`node --version`)
2. `npm install -g @anthropic-ai/claude-code`
3. `claude` 첫 실행 → 로그인
4. **sonnet 모델 고정 확인** — `/model` 명령

### 강사 하네스 끌어오기 (15분, 13:35–13:50)
1. `git --version` 확인 (없으면 https://git-scm.com/)
2. ```bash
   git clone https://github.com/imsebeom/claude-harness-workshop.git
   cd claude-harness-workshop
   ```
3. Windows: `.\install\install.ps1` / Mac·Linux: `bash install/install.sh`
4. 폴더 구조 라이브 투어 — `CLAUDE.md`, `settings.json`, `skills/`, `commands/`
5. `claude` 실행 → "안녕! 너는 어떤 모델이야?" → sonnet 응답 확인

---

## 2교시 (14:00–14:50) — 딥리서치 → 파일 생성 (PDF·HTML·PPT)

### 딥리서치 시키기 (15분, 14:00–14:15)
- 주제 1개 (예: "초등 AI 리터러시 최근 동향")
- Claude Code에게 웹 검색 → 마크다운 보고서 자동 작성 요청
- 결과물 시연

### PDF 논문 → 모바일 HTML ebook 변환 (20분, 14:15–14:35) ⭐ **핵심 데모**
- 자료: `workshop-assets/s41467-025-59906-9.pdf` (Nature Communications 논문)
- `/html` 스킬 호출 → 한 줄로 변환
- 결과물: Pretendard 폰트, 다크모드, TOC, 진행률 바가 있는 단일 `index.html`
- 휴대폰으로도 열어 확인

### PPT 자동 생성 (15분, 14:35–14:50)
- 1교시 결과물(딥리서치 마크다운) → `/pptx` 스킬로 슬라이드 10장 자동 작성
- `/paperbanana` 로 다이어그램 1개 추가

---

## 휴식 + 네트워킹 (14:50–15:30, 30분)

---

## 3교시 (15:30–16:20) — Firebase 배포

### firebase-tools 설치 + 로그인 (15분, 15:30–15:45)
1. `npm install -g firebase-tools`
2. `firebase login` (브라우저 인증)
3. Firebase 콘솔에서 새 프로젝트 생성 (`mdbf-workshop-<본인이름>`)

### 2교시 HTML ebook 배포 (25분, 15:45–16:10) ⭐ **성공 체험**
1. `cd <2교시 결과물 폴더>`
2. `firebase init hosting` — public 폴더 지정, SPA No, GitHub 연동 No
3. `firebase deploy --only hosting`
4. 받은 **Hosting URL**을 본인 휴대폰으로 열기
5. 카톡으로 본인에게 URL 전송 → 성공 인증

### 트러블슈팅 라운드 (10분, 16:10–16:20)
가장 자주 막히는 5가지:
- 로그인 만료 → `firebase login --reauth`
- project ID 충돌 → 다른 ID로 재시도
- public 폴더 비어있음 → `firebase.json` 확인
- 한국어 파일명 → `index.html`로 리네임
- 캐시 → 시크릿 모드로 확인

---

## 4교시 (16:30–17:20) — 하네스 안내 + 적용 실습 + 쇼케이스

### 하네스 4축 해설 (10분, 16:30–16:40)
1. **CLAUDE.md** (지침층) — 글로벌 + 프로젝트 두 층
2. **settings.json** (권한·훅층) — `defaultMode`, `permissions.allow`, `hooks`
3. **hooks** (자동화층) — PreToolUse / PostToolUse / Stop / Notification
4. **skills · commands · agents** (확장층) — 절차 / 단축 / 다른 두뇌

### 스프린트 계약 + 컨텍스트 앵커 (10분, 16:40–16:50)
- **스프린트 계약**: 복잡한 작업 착수 전 *완료 조건 3줄* 합의
- **컨텍스트 앵커**: 프로젝트 CLAUDE.md에 `intent / changes_made / decisions / next_steps` 4줄

### 본인 하네스 1개 추가 실습 (15분, 16:50–17:05)
셋 중 택1 — 강사가 실시간으로 같이 만듦:
- (A) 본인 분야 커맨드 1개 (`/회의록`, `/오늘의수업` 등)
- (B) 본인 분야 스킬 1개 (학습지 자동 생성)
- (C) Stop 훅에 본인 멘트 추가 (`settings.json`)

### 🎬 쇼케이스 (15분, 17:05–17:20)

#### 🟢 묶음 A — fork 가능 스킬 (이 저장소에 포함, 7분)
| # | 스킬 | 한 줄 |
|---|------|------|
| 1 | `/html` | (오늘 실습) PDF/DOCX → 모바일 HTML ebook |
| 2 | `/pdf` | HWP/HWPX↔PDF, PDF→이미지 |
| 3 | `/md` | PDF·논문·영상·HWP·PPT → 통일 마크다운 |
| 4 | `/hwpx` | 마크다운 → 한글 보고서·공문 |
| 5 | `/docx` | 워드 문서 자동 작성·편집 |
| 6 | `/pptx` | 슬라이드 자동 작성 |
| 7 | `/paperbanana` | 학술 다이어그램 자동 생성 |
| 8 | `/video-transcript` | 영상·YouTube → 자막 마크다운 |

#### 🟡 묶음 B — 강사 사례 스킬·커맨드 (저장소 미포함, 4분)
"이런 식으로 본인 분야에 맞춰 만들 수 있습니다" — 30초씩 컷

| # | 항목 | 한 줄 |
|---|------|------|
| 1 | `/quest-학습지` | 차시 한 줄 → HTML→PNG→PDF 학습지 |
| 2 | `/수업페이지` | 백워드 수업설계 + Notion 페이지 통째 |
| 3 | `/회의록` | 협의회 메모 → 결과 보고서 자동 |
| 4 | `/초등설문` | 문항 입력 → 검사지 5분 배포 |
| 5 | `/교수학습과정안` | 교과+차시 → 약안 HTML |
| 6 | `/expense-report` | 경비 Excel 여러 개 → 통합 보고서 |
| 7 | `/notion` | 로컬 파일 → 노션 DB 자동 등록 |
| 8 | `/backup-status` | 매일 백업 상태 점검 |

#### 🟦 묶음 C — 강사 배포 웹앱 (4분)
"하네스가 잡히면 이런 게 일주일에 하나씩 나옵니다"
| # | 웹앱 | 성격 |
|---|------|------|
| 1 | **앙부일구** | 천문/시계 시뮬레이터 |
| 2 | **지층과 화석 시뮬레이션** | 과학 수업 시뮬레이터 |
| 3 | **한강물의여정** | 사회·환경 학습 |
| 4 | **elesurvey** | 초등 설문 플랫폼 |
| 5 | **easyup** | EleUp 과제·질문판 |
| 6 | **science-data-explorer** | 과학 데이터 탐색 |
| 7 | **하루기록 / 일기** | 학생용 기록 도구 |
| 8 | **e-gpt (egpt.kr)** | 강사 본인 사이트 |

#### 🎬 클로징 (1분)
> *"오늘 본 모든 것 중에서 **딱 1개만 fork** 해 가서 7일 안에 본인 작업에 붙여 보세요. 그 1개가 다음 1년의 작업 속도를 바꿉니다."*

→ 강사 GitHub `imsebeom` + 워크숍 저장소 `claude-harness-workshop` QR 1장으로 마무리

---

## 출처 및 참고

- 오픈클로 책 인용 — **출처: 호암중 교사 박권**
- 하네스 엔지니어링 개념 — https://egpt.kr/harness-engineering/
- 도입 영상 — Anthropic, Drew Bent: https://youtu.be/XwjfzwR4XO0
- 실습 PDF — Nature Communications, `s41467-025-59906-9`
