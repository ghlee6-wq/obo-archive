# 오보 아카이브 · Obo Archive

공식 정정·해명 공지와 원보도를 링크 중심으로 보여주는 뉴스 정정 기록 실험입니다.

## Netlify 공개 배포

Netlify에서 GitHub 저장소 `ghlee6-wq/obo-archive`를 가져와 배포합니다.

1. https://app.netlify.com/start 에 로그인합니다.
2. **Add new project → Import an existing project → GitHub**를 선택합니다.
3. GitHub 앱 권한으로 이 저장소만 선택합니다.
4. Production branch는 `main`을 선택합니다.
5. 저장소 루트의 `netlify.toml`이 배포 구성을 자동으로 지정합니다.
   - Build command: `mkdir -p public && cp index.html data.json public/`
   - Publish directory: `public`
   - 공개 파일: `index.html`, `data.json`만 포함
6. 배포 후 **Project overview → Customize → Manage project name and cover image**에서 원하는 사이트 이름을 선택합니다. 이 이름으로 `https://사이트명.netlify.app` 주소가 정해집니다. 이름 중복 시 다른 이름을 고릅니다.
7. 무료 시험 운영 시 Netlify 무료 플랜을 선택합니다. 처음 만든 사이트가 비공개로 설정되었다면 공개로 전환해야 방문자가 볼 수 있습니다.

## 자동 수집 운영 (기존 기능 유지)

- GitHub Actions: `.github/workflows/refresh.yml`
- 정기 실행: 매일 한국시간 **03:17 / 09:17 / 15:17 / 21:17**
- `scripts/update_feed.py`가 The Guardian 공식 정정 RSS의 날짜·제목·공식 링크를 수집합니다.
- 중복 제거 후 `data.json`을 갱신하고 `main`에 커밋합니다.
- GitHub 연결을 완료한 Netlify는 **main 브랜치의 변경을 감지하고 새 버전을 자동 배포**합니다.
- 사용자가 사이트를 열면 `data.json`을 로딩하며 열린 동안은 10분마다 새 데이터를 확인합니다.
- 수집된 RSS 항목은 **미검토 공지**이고, 최초 기사와 공식 정정을 검증한 `verified` 항목과 구분됩니다.
- RSS 접근 실패 시 수집기는 실패를 보고하고 기존 파일은 유지합니다.

## 기존 GitHub Pages

기존 GitHub Pages는 주소 이관을 완료하기 전까지 백업으로 남아 있습니다. Netlify 사이트가 정상 접속되고 자동 배포가 확인된 후 **Settings → Pages**에서 GitHub Pages 게시를 해제할 수 있습니다. GitHub 저장소 자체를 삭제하면 안 됩니다. 데이터 수집이 그곳에서 실행되기 때문입니다.

## 유의사항

- 무료 Netlify 주소는 사이트 이름의 사용 가능 여부에 따라 확정됩니다.
- 주소에서 GitHub 사용자명이 사라지지만, **공개 GitHub 저장소를 추적하면 계정 소유자를 확인할 수 있습니다**. 완전한 익명 운영은 아닙니다.
- 정정 공지가 존재한다는 사실만으로 최초 보도가 허위였다고 단정하지 않습니다.
- The Guardian RSS·기사의 이용 조건을 공개 운영 시 계속 확인해야 합니다.
