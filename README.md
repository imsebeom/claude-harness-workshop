# Claude Harness Workshop

> **2026 몽당분필 오픈 연수 *The Core, Masterclass*** — "클로드 코드 하네스 활용" 강의용 스타터 키트
> 강사: **임세범** (호암중 교사 박권 님 *오픈클로* 책 인용 포함)
> 일시: 2026년 5월 9일(토) 13:00–17:30 / 장소: 서울교육대학교

이 저장소는 **Claude Code만 깔린 빈 PC**에서 강사의 하네스 셋팅 핵심을 5분 만에 적용할 수 있게 해 줍니다.

## 무엇이 들어 있나

| 폴더/파일 | 설명 |
|----------|------|
| `CLAUDE.md` | 글로벌 지침 슬림판 (한국어, sonnet 고정, 스프린트 계약, 컨텍스트 앵커) |
| `settings.json` | sonnet 모델 강제 + acceptEdits 권한 + Stop 비프 훅 1개 |
| `skills/html` | PDF/DOCX → 모바일 친화 HTML ebook 변환 |
| `skills/pdf` | HWP/HWPX → PDF, PDF → 이미지 변환 |
| `skills/rag` | PDF/논문/영상 → RAG용 마크다운 변환 |
| `skills/hwpx` | 한글 문서(.hwpx) 생성·편집 |
| `skills/paperbanana` | 학술 다이어그램·삽화 자동 생성 |
| `skills/pptx` | 슬라이드 자동 작성·편집 |
| `skills/docx` | 워드 문서 자동 작성·편집 |
| `skills/video-transcript` | 영상·YouTube → 자막 마크다운 |
| `commands/배포.md` | Firebase Hosting 한 줄 배포 |
| `commands/verify.md` | 결과물 경량 검증 |
| `commands/wrap.md` | 세션 마무리 (학습점·다음 할 일 정리) |
| `commands/project-init.md` | 새 프로젝트 표준 구조 초기화 |
| `commands/rag.md` | `/rag <파일>` 단축 명령 |
| `install/install.ps1` | Windows 설치 스크립트 |
| `install/install.sh` | macOS/Linux 설치 스크립트 |

## 사전 준비물

1. **Node.js 18 이상** — https://nodejs.org/
2. **Claude Code** — `npm install -g @anthropic-ai/claude-code`
3. **Claude Code Pro 요금제** — 로그인 후 sonnet 모델 사용 가능 확인
4. **Git** — https://git-scm.com/
5. **(선택) Firebase 계정** — 3교시 배포 실습용

## 5분 설치

### Windows (PowerShell)

```powershell
# 1. 저장소 클론
git clone https://github.com/imsebeom/claude-harness-workshop.git
cd claude-harness-workshop

# 2. 설치 스크립트 실행 (기존 ~/.claude는 자동 백업됩니다)
.\install\install.ps1
```

### macOS / Linux

```bash
git clone https://github.com/imsebeom/claude-harness-workshop.git
cd claude-harness-workshop
bash install/install.sh
```

설치 스크립트는 다음을 수행합니다:
1. 기존 `~/.claude` 폴더가 있으면 `~/.claude.bak.YYYYMMDD-HHMMSS`로 자동 백업
2. 이 저장소의 `CLAUDE.md`, `settings.json`, `skills/`, `commands/`를 `~/.claude`에 복사
3. 끝.

## 첫 실행

```bash
claude
> 안녕! 너는 어떤 모델이야?
```

`claude-sonnet` 계열로 답변하면 정상 동작입니다.

## 4차시 강의 구성 (요약)

| 차시 | 주제 | 핵심 활동 |
|------|------|----------|
| 1교시 | 기초 + 초반 셋팅 | 하네스 정의 / Claude Code 설치 / 이 저장소 git clone |
| 2교시 | 딥리서치 → 파일 생성 | `/html`로 PDF 논문 → 모바일 HTML 변환, PPT 자동 생성 |
| 3교시 | Firebase 배포 | `firebase deploy`로 2교시 결과물 공개 URL 얻기 |
| 4교시 | 하네스 안내 + 적용 실습 | 본인 커맨드/스킬/훅 1개씩 만들어 보기 |

상세 커리큘럼: [`CURRICULUM.md`](./CURRICULUM.md)

## 강의 후 활용

- 이 저장소를 **fork** 해서 본인 작업에 맞게 수정하세요.
- 새 스킬·커맨드를 추가하면서 본인만의 하네스로 키워 가세요.
- CLAUDE.md가 100줄을 넘기면 정리 신호입니다.

## 참고 자료

- 강사 풀버전 셋팅: (비공개)
- 하네스 엔지니어링 개념: https://egpt.kr/harness-engineering/
- 오픈클로 책: 호암중 교사 박권 외 (집필 중)
- 몽당분필: https://mdbf.co.kr/

## 라이선스

MIT
