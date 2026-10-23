# 실시간 경매 서비스 — 경매 엔진 (Auction Engine)

> 🚧 **진행 중인 프로젝트입니다.** 아래 내용은 작성 시점(2026-10) 기준이며, 프로젝트 종료 후 최종 정리될 예정입니다.

팀 프로젝트 **"실시간 경매 서비스"**에서 제가 담당한 백엔드(경매 엔진) 파트를 정리한 저장소입니다.
실제 코드와 커밋 히스토리는 팀 저장소에 있습니다 → **[ThreeRoun/Realtime-Auction-Service](https://github.com/ThreeRoun/Realtime-Auction-Service)**

## 프로젝트 개요

물건 하나를 여러 사용자가 동시에 입찰해 최고가로 낙찰받는 실시간 경매 서비스. 4인 팀(경매 엔진 / 실시간 중계 / 프론트엔드 / DevOps)으로 역할을 나눠 진행했고, 저는 팀장과 **경매 엔진(백엔드)** 을 맡았습니다.

- **기술 스택**: Java 21, Spring Boot, PostgreSQL, Redis
- **담당 범위**: 데이터 모델 설계, 입찰/상품 API, 동시 입찰 처리, 마감 연장 로직, 낙찰 처리, 상품 상태 전이

## 핵심 기술 과제

1. **동시 입찰의 정확한 순서 판정** — 여러 사용자가 같은 순간에 입찰해도 DB 트랜잭션과 비관적 락(`SELECT ... FOR UPDATE`)으로 정확히 하나만 최고가로 확정되도록 처리. 20개 스레드가 동시에 입찰하는 상황을 자동화 테스트로 재현해 검증함.
2. **마감 직전 입찰 처리(안티 스나이핑)** — 마감 임박 시점에 유효한 입찰이 들어오면 마감 시각을 자동 연장하는 로직 구현.

## 지금까지 한 일

- Product / Bid / User 데이터 모델 설계 및 Flyway 마이그레이션
- `POST /api/products` — 상품 등록
- `GET /api/products` — 상품 목록 조회 (상태 필터링, 마감 임박순 정렬)
- `POST /api/bids` — 입찰 등록, 비관적 락 기반 동시성 처리
- 마감 연장(안티 스나이핑) 로직
- Redis Pub/Sub으로 실시간 중계 서비스(Node.js)에 입찰/연장 이벤트 발행

## 진행 중 / 예정

- 낙찰 확정 및 크레딧 차감 처리 (차순위 입찰자 승계 포함)
- 상품 상태 자동 전이 스케줄러
- 상품 상세 조회 등 API 보강

## 관련 PR (팀 저장소)

- [#5 DB 스키마 + 입찰 API 명세 + 동시성 처리 착수](https://github.com/ThreeRoun/Realtime-Auction-Service/pull/5)
- [#13 상품 등록/목록 조회 API + 입찰 등록 API 컨트롤러](https://github.com/ThreeRoun/Realtime-Auction-Service/pull/13)
- [#24 마감 연장(안티 스나이핑) 로직](https://github.com/ThreeRoun/Realtime-Auction-Service/pull/24)

> 이 저장소에는 PR마다 테스트를 돌리고 실패 시 AI가 원인을 분석해 코멘트를 남기는 파이프라인(`.github/workflows/test-ai-triage.yml`)도 추가돼 있습니다.
