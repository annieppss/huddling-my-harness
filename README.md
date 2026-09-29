# My Harness — 허들링 디자인 작업 하네스

수작업 디자인 과정을 5단계 에이전트 역할, 운영진 승인 게이트, 읽기 전용 판정 스크립트로 구성한 로컬 하네스입니다.

- [실행 방법](harness/README.md)
- [서비스 요구사항](PRD.md) · [서비스 스토리](story-service.md)
- [실제 수작업 흐름](story-work.md) · [디자인 기준](design.md)
- [목적](harness-purpose.md) · [파이프라인](harness-pipeline.md)
- [오케스트레이터 적용 초안](docs/harness/R7-orchestrator-draft.md) · [검증 결과](docs/harness/R8-verification.md)

Python 3.10 이상이 필요하며 추가 Python 패키지는 없습니다.

```sh
python3 scripts/harness.py --help
python3 -m unittest discover -s tests -v
```

현재 범위는 구조화된 디자인 명세의 생성·승인·검토입니다. uibowl 수집, 실제 Figma 화면 생성과 픽셀 검사는 연결되지 않았습니다. Codex/Claude 실행에는 해당 CLI 설치와 인증이 필요합니다.

실행 기록 `runs/`, 개인 도구 설정, 로컬 OMA 설치 파일은 저장소에서 제외합니다. 기존 AGENTS.md와 CLAUDE.md의 OMA 블록은 로컬 개발 환경용이며, 하네스 CLI 자체는 OMA 없이 실행됩니다. 하네스용 추가 지침은 아직 R7 초안이며 채택 전입니다.
