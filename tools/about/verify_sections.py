"""Regression checks for the approved biography, publication heading and award links."""
from pathlib import Path

BASE = 'https://kjw988.github.io'
PROBEE = 'https://kookmin-sw.github.io/capstone-2024-14/'
BIO_KO = [
    '로봇 팔과 사족보행 로봇을 중심으로 Embodied AI와 Robot Learning을 연구하고 있습니다. 인지·추론·행동을 연결하는 연구 경험을 바탕으로, “학습한 모델을 실제 환경에서 어떻게 효율적이고 안정적으로 사용할 수 있을까?”라는 질문을 탐구합니다.',
    '문제를 구체적인 가설로 정리하고, 아이디어를 구현과 실험으로 검증하는 데 강점이 있습니다. 성능 향상 자체에 그치지 않고, 왜 개선되었는지, 어떤 조건에서 한계가 나타나는지를 함께 살피며 모델의 동작을 이해하고 개선해 나갑니다.',
    '실패는 그 원인을 분석하고 과정을 돌아볼 때 배움이 될 수 있다고 생각합니다. 그래서 협업에서는 성과뿐 아니라 시도한 방법과 겪었던 어려움, 그에 대한 분석과 고민도 함께 나누는 것을 중요하게 여깁니다. 지난 2년간의 연구 과정에서 서로 다른 전문성을 가진 동료들과의 토론을 통해 협업의 가치를 느꼈습니다. 이제는 산업 현장에서 동료들과 자유롭게 의견을 나누며, 정해진 답이 없는 문제에 대한 새로운 해결책을 함께 찾아가고자 합니다.'
]
BACKGROUND_KO = [
    ('2024.09 — 현재', '국민대학교 · 컴퓨터공학과 석사과정', '인공지능 연구실(MI Lab) | 지도교수: 이재구 · 2027.02 졸업 예정'),
    ('2025.06 — 2025.12', 'University of California, Irvine · 방문연구원', 'Dutt Research Group | 지도교수: Nikil Dutt · 온디바이스 VLA 추론 가속·효율화'),
    ('2024.01 — 2024.08', '국민대학교 · 학부연구생', '인공지능 연구실(MI Lab) | 지도교수: 이재구 · 컴퓨터 비전 논문 리뷰 및 딥러닝·CS231n 스터디'),
    ('2018.03 — 2024.08', '국민대학교 · 경제학 학사 / 소프트웨어 복수전공', None)
]


def verify_sections(page, lang: str, width: int) -> None:
    """Check every layout; follow the new links on desktop in each language."""
    home = BASE + ('/' if lang == 'ko' else '/en/')
    heading = page.locator('#research-title > a.publication-heading-link')
    assert heading.count() == 1
    assert heading.get_attribute('href') == f'/projects/{lang}/'
    assert ' '.join(heading.text_content().split()) == ('논문 전체보기 ↗' if lang == 'ko' else 'View all publications ↗')
    assert page.locator('#research .section-heading > a').count() == 0
    assert page.locator('.research-card').count() == 3
    assert page.locator('.research-card .venue').all_text_contents() == [
        'Mathematics (MDPI) · 2026', 'IPIU · 2026',
        'ISET · 2025 · 우수논문상' if lang == 'ko' else 'ISET · 2025 · Best Paper Award'
    ]
    paragraphs = page.locator('#about .prose > p')
    assert paragraphs.count() == 3
    assert paragraphs.nth(2).locator('strong').count() == 1
    if lang == 'ko':
        assert paragraphs.all_text_contents() == BIO_KO
        rows = page.locator('#background .timeline-row')
        assert rows.count() == len(BACKGROUND_KO)
        for index, (date, title, detail) in enumerate(BACKGROUND_KO):
            row = rows.nth(index)
            assert row.locator('.date').inner_text() == date
            assert row.locator('h3').inner_text() == title
            if detail is None:
                assert row.locator('div > p').count() == 0
            else:
                assert row.locator('div > p').inner_text() == detail
    else:
        background = page.locator('#background').inner_text()
        assert 'Dutt Research Group | Advisor: Prof. Nikil Dutt' in background
        assert 'CS231n' in background
        assert page.locator('#background .timeline-row').last.locator('div > p').count() == 0
    expected_links = ['https://www.autopilot-cvpr.net/', f'/projects/lift3d-film/{lang}/', PROBEE, PROBEE]
    awards = page.locator('#awards .award')
    assert awards.count() == 4
    assert awards.first.locator('.award-detail').inner_text() == ('106개 팀 중 6위' if lang == 'ko' else '6th place out of 106 teams')
    assert '108' not in page.locator('#awards').inner_text()
    for index, target in enumerate(expected_links):
        link = awards.nth(index).locator('.award-link')
        assert link.count() == 1 and link.is_visible()
        assert link.get_attribute('href') == target
        assert ' '.join(link.text_content().split()) == ('관련 링크 ↗' if lang == 'ko' else 'Related link ↗')
        if index == 0 or index >= 2:
            assert link.get_attribute('target') == '_blank'
            assert 'noopener' in link.get_attribute('rel')
    if width in (1440, 390):
        out = Path('live-check-results')
        out.mkdir(exist_ok=True)
        for section in ('research', 'background', 'awards'):
            page.locator('#' + section).screenshot(path=str(out / f'{section}-{lang}-{width}.png'))
    if width != 1440:
        return
    heading.click()
    page.wait_for_url(BASE + f'/projects/{lang}/')
    assert page.locator('.card').count() == 6
    # The ACCIDENT award opens the official workshop site (no STAR detail is exposed).
    assert page.locator('#awards .award-link').first.get_attribute('href') == expected_links[0]
    page.goto(home, wait_until='load')
    page.locator('#awards .award-link').nth(1).click()
    page.wait_for_url(BASE + expected_links[1])
    assert page.locator('.paper-link').count() == 1
    page.goto(home, wait_until='load')
    # Open the supplied external project once, without submitting any form.
    if lang == 'ko':
        with page.expect_popup() as popup_info:
            page.locator('#awards .award-link').nth(2).click()
        popup = popup_info.value
        try:
            popup.wait_for_load_state('domcontentloaded', timeout=30000)
            assert popup.url == PROBEE
            assert 'PROBEE' in popup.locator('h1').inner_text()
        finally:
            popup.close()
    print(f'PASS profile sections {lang} {width}: biography, heading, metadata, background and award links', flush=True)
