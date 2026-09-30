"""Editorial presentation only: preserve paper titles, methods, results and citations."""
from __future__ import annotations
from html import escape
import json
from pathlib import Path
import re

COPY = {
    'endcache': {
        'name': 'EndCache',
        'note': {'ko': '(Velocity Reuse 후속 연구)', 'en': '(Follow-up to Velocity Reuse)'},
        'question': {'ko': 'Flow Matching의 속도 재사용을 확산 모델에도 적용할 수 있을까?', 'en': 'Can velocity reuse in flow matching be extended to diffusion models?'},
        'detail': {'ko': '잡음 예측과 깨끗한 행동 추정값(endpoint)의 재사용을 비교하고, 수치 솔버에 따른 오차 전파와 재사용 안정성을 분석합니다.', 'en': 'We compare reusing noise predictions with clean-action endpoint estimates, analyzing error propagation and reuse stability across numerical solvers.'},
        'tags': ['VLA', 'Diffusion', 'Flow Matching', 'Output Caching', 'Training-free'],
    },
    'velocity-reuse': {
        'name': 'Velocity Reuse',
        'question': {'ko': '모델 내부 특징(feature)이 아닌 출력(output), 즉 속도를 다음 생성 단계에서도 재사용할 수 있을까?', 'en': 'Can the model output—velocity, rather than internal features—be reused at subsequent generation steps?'},
        'detail': {'ko': '생성 단계 간 속도의 안정성을 분석하고, 추가 학습 없이 행동 생성기의 반복 호출을 줄입니다.', 'en': 'We analyze velocity stability across generation steps and reduce repeated action-generator calls without additional training.'},
        'tags': ['VLA', 'Flow Matching', 'Output Caching', 'Training-free'],
    },
    'star': {
        'name': 'STAR',
        'question': {'ko': 'CCTV 영상의 특성을 고려한 사고 탐지 방법은 무엇일까?', 'en': 'How can accident detection account for the characteristics of CCTV footage?'},
        'points': {
            'ko': ['사고 시점 우선 추론과 관련 구간 추출', '광학 흐름 기반 움직임 단서 활용', '시간·공간 LoRA 학습과 유형 zero-shot 분류'],
            'en': ['Temporal-first reasoning and accident-centered video trimming', 'Optical-flow motion cues for temporal reasoning', 'Temporal/spatial LoRA with zero-shot collision-type classification'],
        },
        'tags': ['VLM', 'Video Understanding', 'Optical Flow', 'Stage-wise Reasoning', 'LoRA'],
    },
    'navila-patch': {
        'name': 'Adversarial Patch',
        'question': {'ko': '언어 지시를 따르는 내비게이션 모델은 적대적 패치에 얼마나 취약할까?', 'en': 'How vulnerable are instruction-following navigation models to adversarial patches?'},
        'detail': {'ko': '자연어 행동 출력을 겨냥한 적대적 패치를 설계하고, 시뮬레이션에서 패치의 생성 방식·크기·노출 조건에 따른 내비게이션 성능 변화를 분석합니다.', 'en': 'We design patches targeting natural-language action outputs and evaluate how patch construction, size, and exposure conditions affect navigation performance in simulation.'},
        'tags': ['VLA', 'VLN', 'Adversarial Attack', 'Adversarial Patch', 'Robustness'],
    },
    'lift3d-film': {
        'name': 'Lift3D + FiLM',
        'question': {'ko': '언어 지시를 3D 시각 표현에 반영하면 로봇의 행동 예측이 더 정확해질까?', 'en': 'Can language-conditioned 3D visual representations improve robot action prediction?'},
        'detail': {'ko': 'FiLM으로 과업 목표를 시각 특징에 반영하고, 지시문의 구체성에 따른 로봇 제어 성능 변화를 분석합니다.', 'en': 'We use FiLM to condition visual features on task goals and analyze how instruction specificity affects robot-control performance.'},
        'tags': ['Imitation Learning', '3D Representation', 'Language Conditioning', 'FiLM', 'LoRA'],
    },
    'act-cbam': {
        'name': 'ACT + CBAM',
        'question': {'ko': '추가 시연 없이, 중요한 시각 정보에 집중하도록 학습해 로봇 제어 성능을 높일 수 있을까?', 'en': 'Can learning to focus on relevant visual information improve robot control without additional demonstrations?'},
        'detail': {'ko': '동결된 시각 인코더에 채널·공간 어텐션을 결합한 CBAM 어댑터를 더하고, 제어 성공률과 학습 가능한 매개변수 수를 함께 평가합니다.', 'en': 'We add a CBAM adapter with channel and spatial attention to a frozen visual encoder, evaluating task success alongside the number of trainable parameters.'},
        'tags': ['Imitation Learning', 'Visual Attention', 'Adapter Tuning', 'CBAM'],
    },
}


def tag_html(tags, extra_class=''):
    cls = 'tags' + (' ' + extra_class if extra_class else '')
    return f'<div class="{cls}">' + ''.join(f'<span>{escape(t)}</span>' for t in tags) + '</div>'


def summary_html(item, lang, detailed=False):
    lead_class = 'lead' if detailed else 'summary-question'
    text = '<div class="paper-summary">'
    if item.get('note'):
        text += '<p class="summary-note">' + escape(item['note'][lang]) + '</p>'
    text += f'<p class="{lead_class}">' + escape(item['question'][lang]) + '</p>'
    if item.get('detail'):
        text += '<p class="summary-detail">' + escape(item['detail'][lang]) + '</p>'
    if item.get('points'):
        text += '<ul class="summary-points">' + ''.join('<li>' + escape(p) + '</li>' for p in item['points'][lang]) + '</ul>'
    return text + '</div>'


def once(text, old, new, label):
    if text.count(old) != 1:
        raise ValueError(f'Expected one editorial anchor ({label}), got {text.count(old)}')
    return text.replace(old, new, 1)


def refine_output(out: Path, papers: list[dict]) -> None:
    """Update the generated presentation, failing closed if template anchors change."""
    from headings import publication_title
    if {p['slug'] for p in papers} != set(COPY):
        raise ValueError('Editorial metadata and publication slugs differ')
    updates = {}
    for lang in ('ko', 'en'):
        path = out / lang / 'index.html'
        page = path.read_text(encoding='utf-8')
        label = '선택된 연구' if lang == 'ko' else 'Selected research'
        page = once(page, f'<div class="eyebrow">{label} / 2024—2026</div>', '<div class="eyebrow">2024-2026</div>', 'year')
        for p in papers:
            item = COPY[p['slug']]
            page = once(page, '<p>' + escape(p['lead'][lang]) + '</p>', summary_html(item, lang), p['slug'] + ' summary')
            page = once(page, tag_html(p['tags']), tag_html(item['tags']), p['slug'] + ' tags')
            old_search = (p['name'] + ' ' + publication_title(p, 'ko') + ' ' + publication_title(p, 'en') + ' ' + ' '.join(p['tags'])).lower()
            new_search = (item['name'] + ' ' + publication_title(p, 'ko') + ' ' + publication_title(p, 'en') + ' ' + ' '.join(item['tags'])).lower()
            page = once(page, 'data-search="' + escape(old_search, quote=True) + '"', 'data-search="' + escape(new_search, quote=True) + '"', p['slug'] + ' search')
            if item['name'] != p['name']:
                page = once(page, '<p class="paper-alias">' + escape(p['name']) + '</p>', '<p class="paper-alias">' + escape(item['name']) + '</p>', 'alias')
        updates[path] = page
        for p in papers:
            item = COPY[p['slug']]
            path = out / p['slug'] / lang / 'index.html'
            page = path.read_text(encoding='utf-8')
            page = once(page, '<p class="lead">' + escape(p['lead'][lang]) + '</p>', summary_html(item, lang, True), p['slug'] + ' lead')
            page = once(page, '<div class="links">', tag_html(item['tags'], 'paper-tags') + '<div class="links">', 'detail tags')
            if item['name'] != p['name']:
                page = once(page, '<div class="eyebrow">' + escape(p['name']) + ' / ', '<div class="eyebrow">' + escape(item['name']) + ' / ', 'detail alias')
            for r in papers:
                page = page.replace('<span>' + escape(r['lead'][lang]) + '</span>', '<span>' + escape(COPY[r['slug']]['question'][lang]) + '</span>')
            match = re.search(r'(<script type="application/json" id="paper-data">)(.*?)(</script>)', page, flags=re.S)
            if not match:
                raise ValueError('Missing paper data: ' + p['slug'])
            data = json.loads(match.group(2))
            data.update(name=item['name'], lead=item['question'], tags=item['tags'])
            data['summary'] = {k: item[k] for k in ('detail', 'note', 'points') if k in item}
            payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
            page = page[:match.start(2)] + payload + page[match.end(2):]
            updates[path] = page
    for path, page in updates.items():
        path.write_text(page, encoding='utf-8')
    print('Editorial copy: six bilingual summaries; model-family/method tags; Adversarial Patch alias; year label.')
