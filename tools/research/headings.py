"""Publication display titles; experiments and citation data are left unchanged."""
INTRO_KO = '지난 2년 간 로봇 제어의 전 주기에 걸친 연구를 수행하였습니다.\n제1저자, 공동 제1저자 논문 6편의 문제 정의와 방법론, 실험 결과를 살펴보세요.'
INTRO_EN = 'Over the past two years, my research has spanned the full robot-control pipeline.\nExplore the problem formulations, methods, and experimental results of six papers on which I am a first or co-first author.'
KOREAN_TITLES = {
    'velocity-reuse': '속도 재사용을 통한 흐름 매칭 기반 시각-언어-행동 모델의 추가 학습 없는 추론 가속',
    'navila-patch': '자연어 행동 기반 시각-언어 내비게이션 과업에서의 적대적 패치 공격',
    'lift3d-film': '언어 조건 기반 3D 표현 학습을 통한 로봇 제어 성능 향상',
    'act-cbam': '개선된 시각적 어텐션 어댑터를 통한 로봇 제어 성능 향상',
}
def publication_title(paper, language):
    return KOREAN_TITLES.get(paper['slug'], paper['formal_title']) if language == 'ko' else paper['formal_title']
