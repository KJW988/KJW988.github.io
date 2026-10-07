# 한·영 연구 프로젝트 페이지

논문 6편을 `/projects/<논문>/ko/`, `/projects/<논문>/en/`으로 생성합니다. 기존 Chirpy 블로그를 교체하지 않습니다.

## 생성과 검사

```bash
python3 tools/research/publish.py
python3 tools/research/check.py
node --check tools/research/site.js
```

외부 Python 패키지는 필요 없습니다. `publish.py`는 원문 그림의 무결성을 검사하고, 기본 생성기를 실행한 뒤 저자가 지정한 구글 드라이브 링크를 연결합니다. 생성된 `projects/`는 Jekyll 빌드에서 정적 파일로 복사됩니다. `main` 병합 시 기존 Pages 워크플로가 자동 배포합니다.

- `content.py`: 한·영 설명, 저자, 원문 표 데이터
- `site.css` / `site.js`: 공통 디자인과 결과 탐색기
- `figures/`: 저자 제공 논문에서 추출한 원문 그림
- `publish.py`: 6개 원문 링크, 그림 무결성, 공개용 빌드
- `check.py`: 언어·상대 경로·원문 링크·그림·핵심 수치 검사

원문 링크를 수정할 때는 `publish.py`의 `PAPER_IDS`를 갱신합니다. 링크의 공유 권한을 이 코드가 변경하지 않습니다. 전체 논문 PDF, 연구 코드의 비공개 저장소, CV, 산업 협력 자료와 개인 전화번호는 사이트에 포함하지 않습니다. 공개 코드 버튼은 EndCache와 STAR에만 연결합니다.

## 결과의 해석

실험값과 설명용 상호작용을 구분합니다. EndCache와 IEIE 원고의 측정값, 호출 횟수와 실제 시간 가속, 시뮬레이션과 실로봇을 혼동하지 않습니다. STAR의 공동 제1저자 표기를 보존하고, Lift3D의 기본 지시문에서 하락한 과업 및 미보고 조건을 유지합니다. 패치 크기의 한 변 비율과 면적 비율도 구분합니다.

## 페이지 구성 참고

Nerfies (https://nerfies.github.io/), OpenVLA (https://openvla.github.io/), OpenVLA-OFT (https://openvla-oft.github.io/), Diffusion Policy (https://diffusion-policy.cs.columbia.edu/). 코드는 별도로 작성했으며 다른 연구의 실험 영상·출력을 재사용하지 않습니다. 원문 그림의 권리는 논문 저자에게 있습니다.
