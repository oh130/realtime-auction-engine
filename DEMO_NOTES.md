# 데모 작업 기록 (중간고사 대체 발표)

목표: PR마다 `auction-engine` 테스트를 돌리고, 실패하면 AI가 원인을 분석해 PR에 코멘트를 다는 파이프라인을 이 개인 저장소에서 만든다. 팀 저장소(`ThreeRoun/Realtime-Auction-Service`)에는 읽기(clone)만 하고 아무것도 올리지 않는다.

## 1. auction-engine 가져오기 + DB/Redis용 compose 작성

- 팀 저장소 `baseline` 브랜치를 임시 폴더에 clone(커밋 `2bcc0bb`), `auction-engine` 폴더만 이 저장소로 복사. 임시 clone은 작업 끝나고 삭제.
- `docker-compose.yml`을 새로 작성 — 팀 레포 것에서 `db`(postgres:16-alpine)/`redis`(redis:7-alpine)만 가져오고, 계정·DB명·포트는 동일하게 맞춤.
- **막힌 점**: 처음엔 팀 레포 compose처럼 `container_name: auction-db`/`auction-redis`를 그대로 썼는데, 팀 레포 컨테이너랑 이름이 겹쳐서 충돌남. → `container_name` 지정을 빼서 Compose가 프로젝트별로 자동 네이밍하게 바꿈. (포트(5432/6379)는 그래도 겹치므로, 로컬에서 두 레포를 동시에 띄우려면 둘 중 하나는 잠깐 내려야 함 — CI에서는 어차피 서로 다른 머신이라 문제 없음.)

## 2. 개인 저장소 연결

- 새로 만들 필요 없이 기존에 있던 개인 저장소 `oh130/realtime-auction-engine`(README만 있던 상태)을 재활용. origin도 이미 연결돼 있었음.
- 원래 지침은 비공개 저장소였는데, 이 저장소는 원래 포트폴리오용으로 public이었고 공개로 둬도 이후 단계(GitHub Models/Secrets)에 영향이 없어서 public 유지로 결정.

## 3~4. 워크플로 + AI 분석 스크립트

- `.github/workflows/test-ai-triage.yml`: `main`으로의 PR마다 postgres/redis 서비스 컨테이너를 띄우고 Java 21(temurin, gradle 캐시)로 `auction-engine`에서 `./gradlew test` 실행. 테스트 결과 XML은 항상 artifact로 업로드하고, 실패했을 때만(`if: failure()`) AI 분석 스크립트 실행. 권한은 `contents: read` / `pull-requests: write`만.
- **막힌 점 1**: 원래 계획은 GitHub Models를 `GITHUB_TOKEN`으로 쓰는 거였는데, 공식 변경 로그(<https://github.blog/changelog/2026-07-30-github-models-is-now-retired/>)를 확인해보니 **GitHub Models가 2026-07-30에 완전히 폐지**됨(playground/추론 API/BYOK 전부 중단). → 지침대로 OpenAI API 방식으로 1차 구현.
- **막힌 점 2**: OpenAI API는 무료 등급이 없고 결제수단 등록이 필수라, 결제/구독을 쓸 수 없는 상황이라 다시 바꿔야 했음. → Google Gemini API로 최종 변경. 공식 문서(<https://ai.google.dev/gemini-api/docs/rate-limits>)에 "Free tier → 유료 tier로 전환할 때만 결제수단 등록 필요"라고 명시돼 있어, 무료 등급 자체는 카드 등록 없이 Google 계정만으로 키 발급(<https://aistudio.google.com/apikey>) 가능함을 확인하고 적용.
- `.github/scripts/ai_triage.py`: `build/test-results/test/*.xml`(JUnit)에서 실패한 테스트 이름/메시지만 추려(최대 10건, 건당 500자로 자름) Gemini API(`gemini-2.5-flash`, `generateContent`)에 보내고, "실패한 테스트/원인 추정/수정 제안" 형식으로 한국어 답변을 받아 `gh pr comment`로 PR에 등록. 끝에 "🤖 AI 분석 결과이므로 사람이 확인 필요합니다." 문구 고정.

## 5. 로컬 검증

- Docker Desktop이 꺼져 있어서 재기동 후 진행.
- `docker compose up -d` (db/redis)로 이 저장소 전용 컨테이너 기동, healthy 확인 후 `cd auction-engine && ./gradlew test` → **전체 통과 (BUILD SUCCESSFUL)**.
- 검증 끝나고 포트 충돌 안 나게 이 저장소 컨테이너는 내리고, 팀 레포 쪽 컨테이너를 원래대로 복구함.

## 6. main에 push

- `git push origin master:main` — 원격엔 `main` 브랜치가 없었어서 새로 생김. 원래 있던 `master`(옛 README만 있던 상태)는 그대로 두고, 저장소 기본 브랜치를 `main`으로 변경(`gh repo edit --default-branch main`).

## 7. check-pass 데모

- `check-pass` 브랜치 생성, README에 파이프라인 안내 한 줄만 추가 → `main`으로 PR(#1) 생성.
- GitHub Actions 확인: `test` job의 `Initialize containers`(postgres/redis) → `Run tests` → `Upload test result XML`까지 전부 ✓, 테스트가 통과했으므로 `AI triage on failure` 스텝은 설계대로 스킵(`-`)됨. 1m18s만에 전체 통과.
- 확인 끝나고 PR은 머지 + 브랜치 삭제로 정리.

## 8. 실제 작동 확인 (일부러 테스트 깨뜨려서 시연)

- `GEMINI_API_KEY`를 저장소 Secrets에 등록(`gh secret set GEMINI_API_KEY`) — 발급은 https://aistudio.google.com/apikey (구글 계정만 있으면 됨, 카드 등록 불필요).
- `demo/break-a-test` 브랜치에서 기존 테스트 하나를 일부러 깨뜨려(`isNotFound()` → `isOk()`) PR(#2)을 만들어 실제로 AI 코멘트가 달리는지 확인. 그 과정에서 겪은 문제들:
  1. **모델명 문제**: 처음 쓴 `gemini-2.5-flash`가 "신규 사용자에게 더 이상 제공 안 됨(404)" 에러 — API 에러 메시지가 직접 `gemini-3.8-flash`로 바꾸라고 안내해줘서 교체.
  2. **타임아웃**: 60초로는 부족해서 120초로 늘림.
  3. **503(과부하)**: `gemini-3.8-flash`(최신 모델)가 요청할 때마다 "high demand" 503을 반환 — 재시도 로직(최대 4번, 5/10/15초 간격)을 넣어도 계속 실패. 공식 모델 목록 문서(<https://ai.google.dev/gemini-api/docs/models>)에서 한 세대 이전 안정판인 `gemini-3.6-flash`로 바꾸니 바로 해결됨.
- 최종적으로 PR #2에 AI가 실패한 테스트/원인(테스트 코드가 200을 기대하도록 잘못 작성됨)/수정 제안(코드 예시 포함)을 정확하게 분석해서 코멘트로 남기는 것까지 확인. 확인 끝나고 PR은 머지하지 않고 닫음(브랜치도 삭제) — 이 과정 자체가 발표에서 그대로 재현 가능한 시연 시나리오.

## 9. break-lock 데모 (핵심 로직 회귀 탐지 시연)

AI 코멘트 파이프라인이 "테스트 코드 오타" 수준이 아니라 **실제 핵심 로직(동시성 락) 회귀**도 잡아내는지 확인.

- `break-lock` 브랜치에서 `BidService.placeBid()`의 `productRepository.findByIdForUpdate(productId)`(비관적 락)를 `productRepository.findById(productId)`(락 없음) 한 줄로 교체 → PR #3 생성(머지 금지).
- Actions에서 `BidServiceConcurrencyTest.같은_금액으로_동시에_입찰하면_하나만_최고가로_확정된다()`가 **한 번에** 실패함(재실행 불필요): `expected: 1, but was: 7` — 락 없이 20명이 동시 입찰하면 7명이나 동시에 "성공" 처리됨.
- AI 코멘트가 실제 코드 diff를 보지 않고 테스트 이름+실패 메시지만으로도 "동시성 제어(Race Condition) 미흡"을 정확히 진단하고, 원래 코드가 쓰던 바로 그 해법(`@Lock(LockModeType.PESSIMISTIC_WRITE)`, `SELECT ... FOR UPDATE`)까지 제안함.
- 확인 끝나고 PR #3는 머지하지 않고 닫음 + 브랜치 삭제.

## 남은 것

- Actions 로그에 `setup-java@v4` deprecated, Node.js 20 deprecated 경고가 뜨는데 동작엔 지장 없어서 지금은 안 고침 (나중에 `actions/setup-java@v5`로 올리면 사라짐).
- `gemini-3.8-flash`(최신 모델)는 지금 시점에 과부하가 잦아서 안 쓰고 `gemini-3.6-flash`로 고정해둠 — 나중에 안정화되면 바꿔도 됨.

## 알아둘 점 / 한계

- README.md는 예전(초반) 버전 그대로라 지금 팀 프로젝트 진행 상황과 안 맞음 — 이번 작업 범위 밖이라 손 안 댔음, 나중에 갱신 필요.
- 로컬에서 이 저장소와 팀 저장소의 db/redis를 동시에 띄우려면 포트(5432/6379)가 겹쳐서 하나는 내려야 함.
