---
name: deploy
description: "Firebase Hosting 배포 스킬. 'firebase 배포', 'firebase 올려', '공개 URL 만들어 줘', '/deploy' 등 현재 폴더의 정적 결과물(HTML·ebook 등)을 인터넷에 올려야 할 때 사용. /deploy"
---

# Firebase Hosting 한 줄 배포

> **원칙**: 사전 점검·정보 조회는 최소한. **`firebase deploy --only hosting`까지 직진**.

## 흐름 (4단계, 평균 30초~1분)

### 1. CLI 동작 한 줄로만 확인

```bash
firebase --version
```

- 한 줄 응답이 오면 통과. **`firebase projects:list`처럼 시간 걸리는 정보 조회는 부르지 않는다**(불필요한 네트워크 왕복).
- 명령이 없으면 1교시 4-7번 부탁(`Python, Node, firebase CLI를 winget으로 깔아 줘`)을 한 번 더 안내.

### 2. 프로젝트 결정 — 신규/재사용 분기

**(a) 현재 폴더에 `.firebaserc`가 있다면** 그 프로젝트로 그대로 사용. 다음 단계로.

**(b) 없고 사용자가 "X 프로젝트로 배포" / "X 새로 만들어 배포"라고 했다면** 신규 생성:

- project ID는 **자동으로 슬러그 + 랜덤 6자리**로 만든다 (display name `test` → `test-a4b9c2` 같이). project ID는 전 세계 유일해야 하므로 사용자가 준 이름을 그대로 쓰면 충돌 확률이 높다.
- 한 명령으로 끝낸다:
  ```bash
  firebase projects:create <project-id> --display-name "<display-name>"
  ```
- 성공하면 `.firebaserc`를 직접 작성 (Write):
  ```json
  {"projects": {"default": "<project-id>"}}
  ```

**(c) 둘 다 아니면** 사용자에게 어느 프로젝트로 배포할지 한 번 묻는다.

### 3. firebase.json 준비

`firebase init hosting`은 **interactive 프롬프트**라 비대화형 환경에서 막힌다. 호출하지 말고 다음 JSON을 Write로 직접 만든다.

```json
{
  "hosting": {
    "public": "<배포 폴더>",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"]
  }
}
```

배포 폴더 결정:
- 사용자가 **단일 HTML 파일**을 가리키면 → `public/`을 만들고 그 파일을 `public/index.html`로 복사. firebase.json의 `public`은 `"public"`.
- 사용자가 **폴더**를 가리키면 → 그 폴더를 그대로 `public`에 등록 (복사 없음).
- 한국어 파일명이 있으면 `index.html`로 리네임 (URL 인코딩 회피).

### 4. 배포 + 결과 보고

```bash
firebase deploy --only hosting
```

- Hosting URL 한 줄을 굵게 강조해서 사용자에게 보여준다.
- 실패 시 가장 흔한 원인 3개로 즉시 진단:
  - `Failed to authenticate` → `firebase login --reauth`
  - `Project ... already exists` → project ID 자동 슬러그가 충돌. 6자리를 다른 값으로 재생성 후 재시도.
  - `404 / public 폴더 비어 있음` → 3단계의 파일 복사가 빠졌거나 폴더 경로가 틀림.

## 하지 말 것

- **사전 점검을 두 번 부르지 않는다**. `firebase --version` 한 번이면 충분. `projects:list`는 시간만 잡아먹는다.
- **`firebase init hosting`의 interactive 모드를 부르지 않는다**. firebase.json은 직접 Write가 가장 빠르고 결정적이다.
- **PowerShell 전용 명령**(`Test-Path`, `Get-ChildItem` 등)을 Bash에서 부르지 않는다. 파일 존재 확인은 `ls` 또는 `[ -f path ]`.
- **사용자에게 4번 이상 묻지 않는다**. 신규 프로젝트면 자동 슬러그로 바로 만들고, firebase.json은 직접 Write로 만들고, deploy까지 직진.
