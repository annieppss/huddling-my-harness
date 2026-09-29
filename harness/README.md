# 허들링 디자인 작업 하네스

Python 3.10 이상, 외부 Python 패키지 없음. 실제 수작업 7단계를 5개 역할과 검증 가능한 JSON 계약으로 실행한다.
**현재 구현 범위는 구조화 디자인 명세의 생성·승인·검토**다. uibowl 수집과 Figma 노드 생성은 자동화하지 않았다.
수집한 레퍼런스 내용을 입력으로 제공하고, 생성된 명세를 실제 Figma 시안에 반영하는 작업은 별도로 수행한다.

## 빠른 시작

프로젝트 루트에서 실행한다. examples/brief.json을 복사해 실제 화면 ID와 레퍼런스 발췌로 채운다.
예시의 REPLACE_ME가 남아 있으면 시작하지 않는다. 최소 2개 화면이 필요하며 출처의 URL만으로 분석하지 않는다.

```sh
cp examples/brief.json /tmp/huddling-brief.json
# /tmp/huddling-brief.json을 실제 내용으로 편집
python3 scripts/harness.py --run first init --brief /tmp/huddling-brief.json
python3 scripts/harness.py --run first status
python3 scripts/harness.py --run first prompt > /tmp/huddling-task.txt
```

manual 모드는 현재 Codex/Claude 대화에 prompt 내용을 전달하고, 응답 JSON을 파일에 저장한 뒤 제출한다.
단계 이름은 research → plan → concept → design → review다. 다른 단계로 건너뛸 수 없다.

```sh
python3 scripts/harness.py --run first submit --stage research --file /tmp/research.json
# 다음 단계도 prompt → JSON 작성 → submit 순서로 진행
```

설치·로그인된 CLI를 사용해 다음 단계 한 개를 자동 실행할 수도 있다. 각 호출은 모델 사용량을 소비한다.

```sh
python3 scripts/harness.py --run first next --provider codex
# 또는
python3 scripts/harness.py --run first next --provider claude
```

기본 `next`는 manual이므로 prompt만 출력한다. 별도 백그라운드 작업이나 무한 재시도는 없다.
모델 출력은 엄격한 JSON이어야 한다. 코드 펜스·잘못된 타입·규칙 위반은 저장 승인되지 않는다.
작업 중 입력이 바뀌면 이전 응답을 폐기한다. 네트워크/인증 오류 때 단계 기록은 전진하지 않는다.

## 컨셉 승인과 재개

concept를 통과하면 awaiting_approval로 멈춘다. 운영진 본인이 인터랙티브 터미널에서 실행한다.

```sh
python3 scripts/harness.py --run first approve --reviewer '운영진 이름'
python3 scripts/harness.py --run first next --provider codex
python3 scripts/harness.py --run first status
```

승인은 현재 명세와 선행 입력의 해시에 묶인다. 문서를 수정하고 승인을 재사용할 수 없다.
위반 시 보고된 원인을 고친 JSON을 다시 submit하거나 필요한 앞 단계로 돌아간다.

```sh
python3 scripts/harness.py --run first rewind --stage plan
```

출력 파일은 보존하고 완료 기록만 무효화한다. 규칙/문서 스냅샷은 run별 고정되므로 새 규칙 적용은 새 run으로 시작한다.
`status`는 읽기 전용이며 코드/입력/산출물 해시와 게이트를 재검사한다.
종료 코드: 0 정상 실행/완료, 2 게이트 실패·승인 대기·stale, 1 입력/CLI/환경 오류.
성공 상태는 `structured_design_passed`다. 실제 시안이나 앱이 완성됐다는 의미가 아니다.

## 규칙과 역할

- `rules.json`: 토큰 값·서비스 정책·단계·검토 항목의 SSOT
- `schemas/`: 산출물 필드 계약
- `roles/`: 다섯 작업/검토 역할
- `gates.py`: 산출물을 변경하지 않는 기계 판정자
- `../scripts/harness.py`: CLI·원자적 저장·해시 영수증·승인·재개
- `../docs/harness/R4-artifacts.md` ~ `R7-orchestrator-draft.md`: 기본값과 오케스트레이터 추가 초안

runs/는 Git에서 제외한다. 승인 기록은 로컬 감사 기록이며 사용자 인증 시스템은 아니다.
픽셀·Figma 노드·실제 앱 권한·저작권은 이 검사로 인증되지 않는다. 기계 검사와 독립 AI 검토의 한계를 R5에 명시했다.

## 테스트

```sh
python3 -m unittest discover -s tests -v
```

테스트는 임시 디렉터리와 합성 자료를 사용한다. 운영진의 실제 승인이나 실제 디자인 실행 기록을 만들지 않는다.
