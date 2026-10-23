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
- **중요한 막힌 점**: 원래 계획은 GitHub Models를 `GITHUB_TOKEN`으로 쓰는 거였는데, 공식 변경 로그(<https://github.blog/changelog/2026-07-30-github-models-is-now-retired/>)를 확인해보니 **GitHub Models가 2026-07-30에 완전히 폐지**됨(playground/추론 API/BYOK 전부 중단). → 지침대로 OpenAI API 방식으로 전환. `OPENAI_API_KEY`는 저장소 Secrets에 직접 등록(코드/대화 어디에도 키 값 없음).
- `.github/scripts/ai_triage.py`: `build/test-results/test/*.xml`(JUnit)에서 실패한 테스트 이름/메시지만 추려(최대 10건, 건당 500자로 자름) OpenAI Chat Completions API(`gpt-4o-mini`)에 보내고, "실패한 테스트/원인 추정/수정 제안" 형식으로 한국어 답변을 받아 `gh pr comment`로 PR에 등록. 끝에 "🤖 AI 분석 결과이므로 사람이 확인 필요합니다." 문구 고정.

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

## 8. 남은 것

- `OPENAI_API_KEY`를 저장소 Secrets에 아직 등록 안 함 — AI 분석 스텝이 실제로 작동하는지는 "일부러 테스트를 깨뜨리는 PR"을 하나 만들어서 확인해야 함(다음 데모 때 시연용으로 남겨둠).
- Actions 로그에 `setup-java@v4` deprecated, Node.js 20 deprecated 경고가 뜨는데 동작엔 지장 없어서 지금은 안 고침 (나중에 `actions/setup-java@v5`로 올리면 사라짐).

## 알아둘 점 / 한계

- README.md는 예전(초반) 버전 그대로라 지금 팀 프로젝트 진행 상황과 안 맞음 — 이번 작업 범위 밖이라 손 안 댔음, 나중에 갱신 필요.
- 로컬에서 이 저장소와 팀 저장소의 db/redis를 동시에 띄우려면 포트(5432/6379)가 겹쳐서 하나는 내려야 함.
