"""Codex 채팅용 카드뉴스 실행 기록·출력 계약. Python 표준 라이브러리만 사용."""
import argparse
import hashlib
import json
import shutil
import struct
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = Path(__file__).resolve().parent / 'settings'
CRITERIA = [f'QA-{n:02}' for n in range(1, 7)]


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def sources_path(run, folder):
    versioned = folder / 'sources.json'
    return versioned if versioned.exists() else run / 'sources.json'


def init(run, topic):
    if not topic.strip():
        raise ValueError('주제가 비어 있습니다.')
    run.mkdir(parents=True, exist_ok=False)
    snapshot = run / 'settings'
    snapshot.mkdir()
    for path in DOCS.iterdir():
        if path.suffix in ('.json', '.md'):
            shutil.copy2(path, snapshot / path.name)
    (run / 'v0').mkdir()
    write(run / 'state.json', dict(run_id=run.name, topic=topic, created_at=now(),
          version=0, revisions=[], operations={}, human_decision='pending'))


def revise(run, reason):
    state = read(run / 'state.json')
    limit = read(run / 'settings/harness-config.json')['execution']['max_revisions']
    if not reason.strip() or state['version'] >= limit:
        raise ValueError('수정 이유가 없거나 수정 상한에 도달했습니다.')
    old = run / f"v{state['version']}"
    new = run / f"v{state['version'] + 1}"
    new.mkdir()
    source = sources_path(run, old)
    if source.exists():
        if source != old / 'sources.json':
            shutil.copy2(source, old / 'sources.json')
        shutil.copy2(old / 'sources.json', new / 'sources.json')
    if (old / 'content.json').exists():
        content = read(old / 'content.json')
        content['use_seed_frames'] = False
        write(new / 'content.json', content)
    state['version'] += 1
    state['revisions'].append(dict(version=state['version'], reason=reason, at=now()))
    write(run / 'state.json', state)


def operation(run, key, outcome):
    state = read(run / 'state.json')
    op = state['operations'].setdefault(key, dict(attempts=0, outcome=None, history=[]))
    if outcome == 'recovered':
        if op['outcome'] != 'read':
            raise ValueError('실제 상태를 확인한 뒤에만 기존 결과를 복구합니다.')
    elif outcome == 'read':
        if op['outcome'] != 'uncertain':
            raise ValueError('불명확한 쓰기 작업만 상태 확인으로 복구합니다.')
    else:
        if op['outcome'] in ('uncertain', 'success', 'recovered', 'blocked'):
            raise ValueError('상태 확인이 필요하거나 이미 종료한 작업입니다.')
        maximum = 1 + read(run / 'settings/harness-config.json')['execution']['max_transient_retries_per_operation']
        if op['attempts'] >= maximum:
            raise ValueError('같은 작업의 재시도 상한에 도달했습니다.')
        op['attempts'] += 1
    op['outcome'] = outcome
    op['history'].append(dict(outcome=outcome, at=now()))
    write(run / 'state.json', state)


def content_errors(content, sources, policy=None):
    errors = []
    slides = content.get('slides', [])
    if len(slides) != 6 or [s.get('order') for s in slides] != list(range(1, 7)):
        errors.append('장수·순서가 01~06이 아닙니다.')
    if slides and (slides[0].get('role') != 'cover' or slides[-1].get('role') != 'saveable_summary'):
        errors.append('표지·저장용 요약 역할이 필요합니다.')
    source_ids = {s['source_id'] for s in sources.get('sources', []) if s.get('access_status') == 'read' and s.get('content_summary') and s.get('locator')}
    claims = {c['claim_id']: c for c in sources.get('claims', [])}
    for claim in claims.values():
        if claim.get('kind') == 'fact' and not (set(claim.get('source_ids', [])) & source_ids):
            errors.append(f"{claim['claim_id']}: 읽은 출처의 근거가 없습니다.")
    for slide in slides:
        for field in ('role_reason', 'key_message', 'title', 'body_blocks', 'visual_intent', 'panels'):
            if not slide.get(field):
                errors.append(f"{slide.get('order')}: {field} 누락")
        if any(c not in claims for c in slide.get('claim_ids', [])):
            errors.append(f"{slide.get('order')}: 알 수 없는 주장 ID")
    if slides and not slides[-1].get('summary_items'):
        errors.append('저장용 요약 항목이 없습니다.')
    if policy and policy.get('mode') == 'visual_first_ramy':
        for slide in slides[1:-1]:
            visual = slide.get('visual_explanation', {})
            if visual.get('kind') not in policy['allowed_visual_kinds'] or not all(
                visual.get(key) for key in ('communicates', 'elements', 'ramy_role')
            ):
                errors.append(f"{slide.get('order')}: 설명 그림 계획 누락·텍스트 중심 구성")
            if not isinstance(slide.get('mascot_required'), bool):
                errors.append(f"{slide.get('order')}: 람이 배치 여부 미기록")
            lines = [line for block in slide.get('body_blocks', []) for line in block.splitlines() if line.strip()]
            if len(lines) > policy['max_explanation_lines']:
                errors.append(f"{slide.get('order')}: 본문 풀이 줄 수 초과")
    return errors


def check(run):
    state = read(run / 'state.json')
    version = state['version']
    folder = run / f'v{version}'
    errors = []
    try:
        content, sources = read(folder / 'content.json'), read(sources_path(run, folder))
        config = read(run / 'settings/harness-config.json')
        policy = config.get('visual_policy')
        errors.extend(content_errors(content, sources, policy))
        figma, review = read(folder / 'figma.json'), read(folder / 'review.json')
        if review.get('version') != version or figma.get('version') != version or figma.get('run_id') != state['run_id']:
            errors.append('실행·버전 불일치')
        for key, path in [('content', folder / 'content.json'), ('sources', sources_path(run, folder)), ('figma', folder / 'figma.json')]:
            if review.get(key + '_sha256') != sha(path):
                errors.append(key + ' 검수 이후 변경됨')
        frames = figma.get('frames', [])
        for asset in content.get('image_assets', []):
            if not (folder / asset['path']).is_file() or not any(
                record.get('key') == asset['key'] and record.get('image_hash') == asset['image_hash']
                for record in figma.get('image_assets', [])
            ):
                errors.append(f"{asset['key']}: 그림 자산·Figma 대응 누락")
        target = read(run / 'settings/figma-target.json')
        if figma.get('page_id') not in target['allowedWritePageIds'] or len(frames) != 6:
            errors.append('Figma 대상 페이지·장수 불일치')
        for i, frame in enumerate(frames):
            b = frame['bounds']
            if (b['width'], b['height']) != (1080, 1350) or not frame.get('texts'):
                errors.append(f'{i+1}: Figma 규격·편집 텍스트 누락')
            expected = content['slides'][i].get('mascot_required', i in (0, 5))
            if bool(frame.get('mascot_id')) != expected:
                errors.append(f'{i+1}: 캐릭터 배치 위반')
            expected_layout = content['slides'][i].get('layout')
            if expected_layout and frame.get('role_layout') != expected_layout:
                errors.append(f'{i+1}: 역할별 레이아웃 불일치')
            reference = content['slides'][i].get('template_reference')
            if reference and frame.get('template_reference') != reference:
                errors.append(f'{i+1}: 템플릿 기준 불일치')
            if frame.get('layout_issue'):
                errors.append(f'{i+1}: 내용·캐릭터 또는 푸터 간격 위반')
            expected_text = [content['slides'][i]['title'], '\n'.join(content['slides'][i]['body_blocks'])]
            actual_text = [t['characters'] for t in frame.get('texts', [])]
            if any(t not in actual_text for t in expected_text):
                errors.append(f'{i+1}: 문구와 Figma 불일치')
            for t in frame.get('texts', []):
                tb = t['bounds']
                decorative = t['name'] in ('장식 장수', '장식 푸터')
                if not decorative and (tb['x'] < b['x'] + 72 or tb['x']+tb['width'] > b['x']+1008 or tb['y'] < b['y']+72 or tb['y']+tb['height'] > b['y']+1278):
                    errors.append(f'{i+1}: 텍스트 안전 여백 위반')
                if t['name'] in ('핵심', '도입', '풀이') and t['font_size'] < 48:
                    errors.append(f'{i+1}: 핵심 본문 크기 위반')
                if t['name'] == '장식 장수' and tb['height'] > t['font_size'] * 1.5:
                    errors.append(f'{i+1}: 장수 표시 줄바꿈')
            if i == 0 and content['slides'][i].get('scene_asset'):
                asset = content['slides'][i]['scene_asset']
                records = figma.get('image_assets', [])
                if not (folder / asset).is_file() or not any(a.get('node_id') == frame.get('scene_id') and a.get('image_hash') == content['slides'][i].get('scene_image_hash') for a in records):
                    errors.append('표지 장면 자산·Figma 대응 누락')
            for other in frames[:i]:
                a = other['bounds']
                if b['x'] < a['x']+a['width'] and a['x'] < b['x']+b['width'] and b['y'] < a['y']+a['height'] and a['y'] < b['y']+b['height']:
                    errors.append('Figma 프레임 겹침')
        for n in range(1, 7):
            name = f'{n:02}.png'
            path = folder / name
            data = path.read_bytes()
            if data[:8] != b'\x89PNG\r\n\x1a\n' or struct.unpack('>II', data[16:24]) != (1080, 1350):
                errors.append(name + ' PNG 규격 불일치')
            if review.get('png_sha256', {}).get(name) != sha(path):
                errors.append(name + ' 검수 이후 변경됨')
        if not (folder / 'preview.png').is_file():
            errors.append('전체 미리보기 누락')
        if review.get('image_widths_reviewed') != [1080, 375, 432]:
            errors.append('원본·축소 이미지 검수 미완료')
        criteria = review.get('criteria', {})
        for key in CRITERIA:
            item = criteria.get(key, {})
            if item.get('status') != 'pass' or item.get('completed') is not True or not item.get('evidence'):
                errors.append(key + ' 필수 검수 미통과')
        if policy and policy.get('mode') == 'visual_first_ramy':
            for order in range(2, 6):
                visual = review.get('visual_checks', {}).get(f'{order:02}', {})
                if (visual.get('status') != 'pass' or not visual.get('evidence')
                        or not visual.get('node_ids') or visual.get('paragraph_boxes_absent') is not True
                        or visual.get('visual_carries_meaning') is not True):
                    errors.append(f'{order}: 그림 중심 설명 검수 미통과')
    except (OSError, ValueError, KeyError, TypeError, struct.error) as exc:
        errors.append('산출물 확인 실패: ' + str(exc))
    result = dict(run_id=state['run_id'], version=version,
                  status='ready_for_final_review' if not errors else 'needs_human_review',
                  human_decision=state['human_decision'], errors=errors, checked_at=now())
    if not all((folder / f'{n:02}.png').exists() for n in range(1, 7)):
        result['status'] = 'blocked'
    write(folder / 'gate.json', result)
    return result


def render_script(run):
    state = read(run / 'state.json')
    folder = run / f"v{state['version']}"
    content = read(folder / 'content.json')
    policy = read(run / 'settings/harness-config.json').get('visual_policy')
    errors = content_errors(content, read(sources_path(run, folder)), policy)
    if errors:
        raise ValueError('; '.join(errors))
    publishers = sorted({s.get('author_or_publisher', '공식 자료') for s in read(sources_path(run, folder))['sources']})
    footer = '출처: ' + ' · '.join(publishers) + ' 공식 도움말 · ' + now()[:10]
    data = dict(run_id=state['run_id'], version=state['version'], slides=content['slides'], footer=footer,
                target=read(run / 'settings/figma-target.json'), seed=content.get('use_seed_frames', False))
    data['asset_hashes'] = content.get('asset_hashes', {})
    code = 'const DATA = ' + json.dumps(data, ensure_ascii=False) + ';\n'
    if content.get('template_id', 'visual_story') != 'visual_story':
        raise ValueError('공개 배포판은 visual_story 렌더러만 포함합니다.')
    template = 'render-visual-story.js'
    code += (Path(__file__).parent / template).read_text()
    (folder / 'render.js').write_text(code)
    return str(folder / 'render.js')


def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest='command', required=True)
    for command in ('init', 'revise', 'check', 'render-script', 'operation'):
        p = subs.add_parser(command)
        p.add_argument('run', type=Path)
        if command == 'init':
            p.add_argument('topic')
        if command == 'revise':
            p.add_argument('--reason', required=True)
        if command == 'operation':
            p.add_argument('--key', required=True)
            p.add_argument('--outcome', choices=['transient','uncertain','read','recovered','success','blocked'], required=True)
    args = parser.parse_args()
    try:
        if args.command == 'init': init(args.run, args.topic)
        elif args.command == 'revise': revise(args.run, args.reason)
        elif args.command == 'operation': operation(args.run, args.key, args.outcome)
        elif args.command == 'check':
            result = check(args.run)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if result['status'] != 'ready_for_final_review': parser.exit(2)
        else: print(render_script(args.run))
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
