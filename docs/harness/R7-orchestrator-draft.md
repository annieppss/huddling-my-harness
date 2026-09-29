# R7 — AGENTS.md / CLAUDE.md에 추가할 초안

아직 루트 지침에 반영하지 않았다. 최종 사용자 승인 후 OMA 관리 블록 **밖에만** 추가한다.

```markdown
## Huddling design harness

- 서비스 목적과 제약: PRD.md, story-service.md. 실제 수작업 경험: story-work.md. 섞지 않는다.
- 실행 안내: harness/README.md. 규칙 SSOT: harness/rules.json.
- “허들링 디자인 시작”: 화면 ID·실제 레퍼런스 발췌가 포함된 brief를 확인하고 새 run을 init한다.
- “허들링 디자인 계속”: 먼저 status를 확인하고 처음 미완료/무효화된 단계 1개만 진행한다.
- “허들링 디자인 검사”: status와 review를 수행한다. 원본 디자인을 판정자가 수정하지 않는다.
- “허들링 디자인 수정”: 판정 결과의 return_to에 따라 rewind하고 영향을 받는 후속 단계를 다시 수행한다.
- 기본 실행은 manual이다. 현재 런타임의 작업 에이전트에게 prompt를 주고 JSON을 submit한다.
- 원격 CLI 실행이 요청되면 next --provider codex 또는 claude를 사용한다. 성공을 추정하지 않고 종료 코드와 상태를 확인한다.
- concept 뒤 awaiting_approval이면 운영진에게 명세와 해시를 제시하고 멈춘다. 에이전트가 approve하거나 운영진 이름을 대신 입력하지 않는다.
- 레퍼런스·승인·근거가 없으면 발명하지 않는다. unknown은 통과가 아니다.
- 초기 단계 변경 시 영수증·컨셉 승인 무효화를 존중한다. state.json을 직접 고쳐 통과시키지 않는다.
- structured_design_passed는 구조화 명세 검사 완료다. Figma 화면 작성, 실제 권한 검사나 출시 완료로 표현하지 않는다.
- .agents/ 및 OMA 관리 블록을 수정하지 않는다.
```
