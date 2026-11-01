# 오보 아카이브 (Obo Archive)

전 세계 언론사가 공식적으로 정정·해명한 보도를 모아 보는 공개 아카이브 실험 프로젝트입니다.

## 공개 사이트
- GitHub Pages: https://ghlee6-wq.github.io/obo-archive/
- 저장소: https://github.com/ghlee6-wq/obo-archive

## 주요 기능
- 상단 검색, 카테고리별 추천 카드, 랜덤 탐색
- 공식 정정 → 최초 보도 순서의 역순 타임라인
- 기사 본문 복제 대신 원문 링크 제공
- 검증된 정정 사례와 미검토 RSS 발견 항목 분리

## 자동 수집 방식
- GitHub Actions가 UTC 00:17, 06:17, 12:17, 18:17에 `scripts/update_feed.py`를 실행하도록 예약되어 있습니다.
- The Guardian 공식 정정 RSS에서 글의 제목·날짜·원문 URL만 가져와 `data.json`의 `feed_items`에 축적합니다.
- 중복 항목은 제외하며 기존 기록을 유지합니다. RSS 접속 실패 시 이미 저장된 데이터는 삭제하지 않습니다.
- 사이트는 방문 시 `data.json`을 불러오며, 열린 상태에서는 10분마다 확인합니다.
- RSS로 새로 발견된 항목은 검증된 오보가 아니라 **미검토 정정·해명 공지**로만 표시합니다.
- 최초 기사를 정확히 연결해 검증하는 절차는 아직 자동화되지 않았습니다.

## 사이트 공개 설정
1. 저장소 `Settings → Pages`로 이동
2. `Build and deployment → Source`를 **GitHub Actions**로 변경
3. `Actions → Auto collect corrections and publish website → Run workflow` 실행
4. 성공 후 https://ghlee6-wq.github.io/obo-archive/ 접속

## 주의
- 이 저장소는 테스트 버전이며, 실제 RSS 네트워크 접속 및 GitHub Pages 배포 성공 여부를 확인해야 합니다.
- The Guardian RSS 및 각 사이트의 이용 조건을 확인한 뒤 비상업적 범위에서 시범 운영해야 합니다.
- 공식 정정·해명 공지가 공개됐다는 사실만으로 관련 원보도가 허위라고 단정할 수 없습니다.
