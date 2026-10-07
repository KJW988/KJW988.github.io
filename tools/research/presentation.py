"""Editorial presentation; scientific content, original titles and results are preserved."""
from __future__ import annotations
from html import escape
from pathlib import Path
import json
import re
from content import PAPERS
from english_copy import apply_paper_copy

apply_paper_copy(PAPERS)

COPY = {
    'endcache': {
        'name': 'EndCache',
        'note': {'ko': '(Velocity Reuse 후속 연구)', 'en': '(Follow-up to Velocity Reuse)'},
        'question': {'ko': 'Flow Matching의 속도 재사용을 확산 모델에도 적용할 수 있을까?', 'en': 'Can velocity reuse in flow matching be extended to diffusion models?'},
        'points': {
            'ko': ['noise prediction과 endpoint 재사용 비교', 'solver별 error propagation과 재사용 안정성 분석', 'Training-free output caching의 추론 가속 검증'],
            'en': ['Comparison of noise-prediction and endpoint reuse', 'Solver-dependent error propagation and reuse stability', 'Evaluation of training-free output caching for faster inference'],
        },
        'tags': ['VLA', 'Diffusion', 'Flow Matching', 'Output Caching', 'Training-free'],
    },
    'velocity-reuse': {
        'name': 'Velocity Reuse',
        'question': {'ko': '내부 feature가 아닌 output, 즉 velocity를 다음 생성 단계에서도 재사용할 수 있을까?', 'en': 'Can we reuse the model’s output velocity—not its internal features—across generation steps?'},
        'points': {
            'ko': ['생성 단계 간 velocity의 방향·크기 안정성 분석', 'output 재사용으로 action generator 호출 축소', '추가 학습 없이 성공률과 inference latency 평가'],
            'en': ['Analysis of velocity direction and magnitude across generation steps', 'Fewer action-generator calls through output reuse', 'Success-rate and inference-latency evaluation without retraining'],
        },
        'tags': ['VLA', 'Flow Matching', 'Output Caching', 'Training-free'],
    },
    'star': {
        'name': 'STAR',
        'question': {'ko': 'AUTOPILOT Workshop @ CVPR 2026 · Non-archival',
                     'en': 'AUTOPILOT Workshop @ CVPR 2026 · Non-archival'},
        'points': {'ko': [], 'en': []},
        'tags': ['VLM', 'Video Understanding', 'Non-archival'],
    },
    'navila-patch': {
        'name': 'Adversarial Patch',
        'question': {'ko': '언어 지시를 따르는 내비게이션 모델은 적대적 패치에 얼마나 취약할까?', 'en': 'How vulnerable are instruction-following navigation models to adversarial patches?'},
        'points': {
            'ko': ['자연어 action output을 겨냥한 adversarial patch 설계', '패치 생성 방식·크기·노출 조건별 영향 비교', '시뮬레이션에서 주행 성공률과 경로 효율 분석'],
            'en': ['Adversarial patches targeting natural-language action outputs', 'Effects of patch construction, size, and exposure conditions', 'Navigation success and path efficiency evaluated in simulation'],
        },
        'tags': ['VLA', 'VLN', 'Adversarial Attack', 'Adversarial Patch', 'Robustness'],
    },
    'lift3d-film': {
        'name': 'Lift3D + FiLM',
        'question': {'ko': '언어 지시를 3D 시각 표현에 반영하면 로봇의 행동 예측이 더 정확해질까?', 'en': 'Can language-conditioned 3D visual representations improve robot action prediction?'},
        'points': {
            'ko': ['FiLM 기반 language conditioning 적용', '과업 목표를 반영한 3D representation 학습', '지시문의 구체성에 따른 제어 성능 비교'],
            'en': ['FiLM-based language conditioning', 'Task-conditioned 3D representation learning', 'Control performance compared across levels of instruction detail'],
        },
        'tags': ['Imitation Learning', '3D Representation', 'Language Conditioning', 'FiLM', 'LoRA'],
    },
    'act-cbam': {
        'name': 'ACT + CBAM',
        'question': {'ko': '추가 시연 없이, 중요한 시각 정보에 집중해 로봇 제어 성능을 높일 수 있을까?', 'en': 'Can focusing on relevant visual information improve robot control without more demonstrations?'},
        'points': {
            'ko': ['동결된 visual encoder에 CBAM adapter 결합', 'Channel·spatial attention의 개별·결합 효과 비교', '제어 성공률과 학습 가능한 parameter 수 평가'],
            'en': ['A CBAM adapter added to a frozen visual encoder', 'Ablations of channel attention, spatial attention, and their combination', 'Evaluation of task success rates and trainable parameter counts'],
        },
        'tags': ['Imitation Learning', 'Visual Attention', 'Adapter Tuning', 'CBAM'],
    },
}


def tag_html(tags, extra_class=''):
    cls = 'tags' + (' ' + extra_class if extra_class else '')
    return f'<div class="{cls}">' + ''.join(f'<span>{escape(t)}</span>' for t in tags) + '</div>'


def summary_html(item, lang, detailed=False):
    lead_class = 'lead' if detailed else 'summary-question'
    text = '<div class="paper-summary">'
    text += f'<p class="{lead_class}">' + escape(item['question'][lang]) + '</p>'
    text += '<ul class="summary-points">' + ''.join('<li>' + escape(p) + '</li>' for p in item['points'][lang]) + '</ul>'
    if item.get('note'):
        text += '<p class="summary-note">' + escape(item['note'][lang]) + '</p>'
    return text + '</div>'


def once(text, old, new, label):
    if text.count(old) != 1:
        raise ValueError(f'Expected one editorial anchor ({label}), got {text.count(old)}')
    return text.replace(old, new, 1)


def refine_output(out: Path, papers: list[dict]) -> None:
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
            data['summary'] = {k: item[k] for k in ('note', 'points') if k in item}
            payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
            page = page[:match.start(2)] + payload + page[match.end(2):]
            updates[path] = page
    for path, page in updates.items():
        path.write_text(page, encoding='utf-8')
    print('Editorial copy: six bilingual questions and three-point summaries; trailing follow-up note.')
