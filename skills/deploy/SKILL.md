---
name: deploy
description: "Firebase Hosting 배포 스킬. 'firebase 배포', 'firebase 올려', '공개 URL 만들어 줘', '/deploy' 등 현재 폴더의 정적 결과물(HTML·ebook 등)을 인터넷에 올려야 할 때 사용. /deploy"
---

다음 절차로 Firebase Hosting 배포를 수행하라.

## 사전 점검
1. `firebase-tools`가 설치되어 있는지 확인: `firebase --version`
   - 없으면 `npm install -g firebase-tools` 안내 후 중단.
2. 로그인 상태 확인: `firebase projects:list`
   - 인증 실패 시 `firebase login` 안내 후 중단.

## 배포 절차
1. 현재 폴더에 `firebase.json`이 없으면 `firebase init hosting`을 안내하라.
   - public 폴더는 `public` 또는 결과물이 있는 폴더로 설정
   - SPA 여부는 단순 ebook이면 `No`
   - GitHub 자동 배포는 `No` (워크숍에서는 수동)
2. 배포 대상 파일이 public 폴더 안에 있는지 확인.
   - 한국어 파일명은 `index.html`로 리네임 권장 (URL 인코딩 이슈 회피).
3. `firebase deploy --only hosting` 실행.
4. 출력의 **Hosting URL**을 사용자에게 명확하게 표시하라.

## 후처리
- 배포 성공 시 URL을 한 줄로 강조해서 보여줘라.
- 실패 시 가장 흔한 원인 3개(로그인 만료 / project ID 충돌 / public 폴더 비어있음)를 진단 항목으로 제시하라.
