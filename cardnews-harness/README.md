# 람이·이미지 중심 카드뉴스 하네스 사용법

Codex 채팅이 조사·장별 구성·이미지 생성·Figma 제작·검수를 진행하고, Python 실행기가 버전·수정 예산·파일 대응·검수 증거를 관리하는 구조입니다. 독립 Python 명령만으로 AI 제작 전체가 실행되지는 않습니다.

## 준비

- Python3.10 이상. 실행기와 테스트는 표준 라이브러리만 사용합니다.
- 미리보기 생성에는 Pillow가 필요합니다: `python3 -m pip install Pillow`.
- Figma와 이미지 생성 도구를 사용할 수 있는 Codex 환경, 본인이 사용할 권한이 있는 캐릭터 이미지가 필요합니다.
- `settings/figma-target.json`의 fileKey / pageId / allowedWritePageIds를 자신의 작업 파일·전용 페이지로 설정합니다. 공개 파일의 값은 비워 두었습니다.
- 캐릭터 개별 자산과 업로드된 imageHash는 직접 준비합니다. 공개된 최종 카드뉴스에서 캐릭터를 추출하는 절차는 제공하지 않습니다.

## 실행

```sh
python3 -m unittest discover -s cardnews-harness -p 'test_*.py'
python3 cardnews-harness/harness.py init runs/cardnews/example '자동화에서 트리거와 액션은 뭘까?'
```

Codex에 다음과 같이 요청합니다.

> cardnews-harness/WORKFLOW.md와 settings의 설정을 읽고, 이 하네스로 주제에 맞는6장 카드뉴스를 제작해줘. 람이 또는 내가 제공한 캐릭터의 행동·이미지·도식을 먼저 설계하고 짧은 풀이를 붙여줘. 실제 이미지와 근거를 확인하기 전에는 검수 통과로 기록하지 마.

조사·문구 파일이 준비된 뒤 다음 명령을 사용합니다. init 직후에는 필요한 산출물이 없으므로 render-script/check가 완료되지 않는 것이 정상입니다.

```sh
python3 cardnews-harness/harness.py render-script runs/cardnews/example
python3 cardnews-harness/preview.py runs/cardnews/example/v0
python3 cardnews-harness/harness.py check runs/cardnews/example
python3 cardnews-harness/harness.py revise runs/cardnews/example --reason 'QA-05 그림 설명 보완'
```

생성된 render.js를 Figma 연결 도구로 실행합니다. `use_figma`를 쓰는 환경에서는 해당 도구의 필수 스킬을 먼저 읽습니다. 캐릭터 그림을 업로드하고 파일·이미지 해시·노드를 대응시킨 뒤 실제 PNG를 내보냅니다. 주요 글자·화살표·도식은 편집 레이어로 유지합니다.

`render-visual-story.js`는 설문→알림 예시용입니다. 새로운 주제는 labels, 장면, 장별 구성과 문구를 함께 바꿔야 합니다. submit / notification / thinking 키에 대응하는 자기 이미지의 해시를 content.json의 asset_hashes에 넣습니다. 새 Figma 파일에서는 해시를 재사용하지 말고 자산을 다시 업로드합니다.

## 파일 계약

- `sources.json`: sources에 source_id / access_status=read / content_summary / locator / author_or_publisher, claims에 claim_id / kind / source_ids. 검색 요약만 보고 read라고 쓰지 않습니다.
- `content.json`: template_id=visual_story, slides에 order(1~6) / role / role_reason / key_message / title / body_blocks / claim_ids / visual_intent / panels / layout / mascot_required. 첫 role은 cover, 마지막은 saveable_summary이며 summary_items가 필요합니다.
- 본문2~5장에는 visual_explanation의 kind / communicates / elements / ramy_role이 필요합니다. kind는 ramy_scene, annotated_screenshot, comparison, process_diagram 중 하나입니다.
- `figma.json`: run_id / version / page_id / frames와 실제 노드·경계·텍스트·이미지 대응. 렌더러 반환 정보를 보존합니다. image_assets는 실제 업로드 후 추가합니다.
- `review.json`: version, content_sha256 / sources_sha256 / figma_sha256, png_sha256, image_widths_reviewed=[1080,375,432], criteria의 QA-01~06별 status / completed / evidence. 파일 해시는 SHA256입니다.
- `review.json.visual_checks`: 02~05 각각 status / evidence / node_ids / paragraph_boxes_absent / visual_carries_meaning. 실제 그림과 의미를 확인한 뒤에만 pass/true를 씁니다.
- `01.png`~`06.png`, `preview.png`: 실제 최종 출력. 예시 검수 기록은 공개하지 않으므로 이 파일들만으로 check가 통과하지 않습니다.

## 검수와 종료

QA-01 근거 정확성, QA-02 이해도·그림과 설명 일치, QA-03 저장용 요약, QA-04 글자 잘림·가독성, QA-05 그림 중심 구성, QA-06 출력·편집 가능성을 확인합니다. 풀이1~2줄, 핵심48px 이상, 안전 여백72px를 기본값으로 사용합니다.

긴 문단을 상자에 나누거나 작은 캐릭터만 장식으로 붙이면 수정합니다. 문구의 줄 수 검사는 실제 화면에서 읽히는지 판단하는 검토를 대신하지 않습니다.

자동 수정은 최대2회, 일시 오류는 같은 작업1회 추가 재시도입니다. 쓰기 결과가 불명확하면 실제 상태를 읽고 기록한 뒤 복구합니다. `ready_for_final_review`는 최종 확인 준비 상태이며 게시 승인이나 독자 반응 보장이 아닙니다.

공개 테스트는 임시 합성 데이터를 사용하는 계약 검사이며, 실제 Figma·이미지 생성 연결 테스트가 아닙니다. 현재 예시는 추가 디자인 개선과 다른 주제 검증이 필요합니다.
