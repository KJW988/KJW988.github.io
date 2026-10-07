# About home

- `/`: 한국어 About me 홈 화면. `/en/`: 영어 버전. `/about/`: 언어 설정을 고려한 기존 주소 연결.
- `/blog/`: 기존 Chirpy 글 목록. 페이지 나누기는 `_config.yml`의 `/blog/page:num/`를 사용합니다.
- `_data/about.yml`: 공개 소개 내용. `_layouts/about-home.html`: 공통 레이아웃. `assets/css/about.css`: 홈 전용 스타일.
- 기존에 공개된 프로필 사진을 그대로 사용합니다. 전화번호·생년월일, 전체 이력서, 산학 내부 문서는 업로드하지 않습니다.
- 2026-02-16 학기 목표 글은 `published: false`로 사이트 출력에서 제외합니다. 공개 저장소의 원문과 Git 이력을 비공개로 만드는 것은 아닙니다.
- Jekyll 빌드 후 `python3 tools/about/check.py`로 홈·내부 링크·제외한 글을 검증합니다.
- 배포 후 `python3 tools/about/verify_live.py`로 한·영 홈, 실제 탐색, 원문 글 404, 검색·RSS·목록 제외 여부를 검증합니다.
- 기존 논문 6편의 본문·그림·데이터·Google Drive 링크는 변경하지 않습니다.
