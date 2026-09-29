# R6 — 역할과 실행

구현 기본값. 다섯 역할의 프롬프트는 harness/roles/에 있다.

| 역할 | 유일한 산출물 폴더 | 읽을 수 있는 입력 |
|---|---|---|
| research | research/ | brief, 서비스·디자인 기준 |
| plan | plan/ | 기준, research |
| concept | concept/ | 기준, research, plan |
| design | design/ | 기준, 선행 명세, 컨셉 승인 완료 상태 |
| review | review/ | 기준과 모든 선행 산출물. 원본 편집 금지 |

작업 에이전트는 JSON만 반환한다. 하네스가 단계별 고정 경로에만 저장하므로 에이전트 응답으로 파일 경로를 지정할 수 없다.
기계 판정자 harness/gates.py는 파일 쓰기 기능이 없는 순수 함수다. review는 별도 AI 호출 또는 독립 검토자의 JSON 제출이며 디자인 산출물을 고치지 않는다.

기본 provider는 manual: prompt를 현재 Codex/Claude 대화에 전달하고 JSON을 submit한다.
`next --provider codex` 또는 `--provider claude`는 로컬 CLI를 1회 실행한다. 모델은 CLI 기본값을 사용한다.
Codex는 read-only sandbox·개인 설정 제외·임시 작업 폴더를, Claude는 safe-mode·도구 없음·MCP 제한·임시 작업 폴더를 사용한다.
두 경로 모두 프로젝트 파일 쓰기는 하네스가 담당한다. 모델 응답은 사실을 보장하지 않으며 판정과 검토를 통과해야 한다.
CLI 설치·인증·네트워크는 사용자의 환경이 필요하다. 실패·시간 초과·잘못된 JSON은 다음 단계로 진행시키지 않는다.

자연어 트리거의 연결 초안은 R7 문서에 있다. 문자열만으로 승인이나 외부 배포를 자동 수행하지 않는다.
