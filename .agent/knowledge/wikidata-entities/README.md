# Wikidata Q-item 등록 가이드

> 작성: 2026-04-27 by Claude Opus 4.7 (Strategy Lead)
> 목적: Neo Genesis + 11 SBU + 창업자의 Wikidata 엔티티 등록을 owner 가 web UI 로 제출하기 쉽게 데이터 준비
> 근거: `.agent/knowledge/20260427_AI_TRAFFIC_MAXIMIZATION_MASTER_v1.md` Phase 0

## 왜 Wikidata 인가

- Google Knowledge Graph + Siri/Alexa + ChatGPT/Claude entity resolution 의 **단일 진입점**
- 회사 notability 요건이 Wikipedia 보다 훨씬 약함 — 직접 생성 가능
- 무료, 1~2주, **권위 ROI 1위**
- ChatGPT 인용의 47.9% 가 Wikipedia → Wikipedia 가 Wikidata 엔티티 의존 → 결국 Wikidata 가 root signal

## 등록 절차 (각 항목당 5~10분)

1. https://www.wikidata.org/ 로그인 (계정 무료)
2. "Create a new item" 클릭
3. 아래 JSON 파일 (`q-*.json`) 의 데이터 그대로 입력:
   - **Label** (영문): "Neo Genesis"
   - **Description** (영문): 한 줄 요약
   - **Aliases** (한국어 + 영문): 필요 시 다중
   - **Statements**: 각 P-property 추가
4. Save

## 등록 우선순위

1. **Q-NeoGenesis** (회사 본체) — 가장 먼저, 다른 항목들의 reference 노드
2. **Q-YesolHeo** (창업자) — Q-NeoGenesis 의 P112 (founder) 로 연결
3. **Q-ToolPick** (FLAGSHIP SBU) — 가장 큰 도메인
4. **Q-URWrong** — 자체 도메인 ur-wrong.com
5. **Q-KOTT** — 자체 도메인 kott.kr
6. **Q-EthicaAI** — 학술 권위 (NeurIPS)
7. **Q-WhyLab** — 학술 권위
8. **Q-ReviewLab, Q-FinStack, Q-AIForge, Q-SellKit, Q-DeployStack, Q-CraftDesk** (남은 6 SBU, 일괄)

## 각 항목 등록 후

- Wikidata Q-ID 를 받음 (예: Q123456789)
- `src/landing/src/app/layout.tsx` 의 `ORGANIZATION_SCHEMA.sameAs` 배열에 `https://www.wikidata.org/wiki/Q123456789` 추가
- 각 SBU 페이지의 schema 에도 동일하게 추가 (Phase 1)

## 핵심 statement (Wikidata properties)

가장 중요한 P-property (모든 항목 공통):
- **P31 (instance of)**: Q4830453 (business) / Q166142 (application) / Q5 (human, 창업자만)
- **P17 (country)**: Q884 (South Korea)
- **P856 (official website)**: 도메인 URL
- **P112 (founder)**: 다른 Q-item 참조 (Q-YesolHeo)
- **P571 (inception)**: 2024
- **P1448 (official name)**: 영문 정식 명칭
- **P2002 (Twitter username)**: 있다면
- **P2013 (Facebook ID)**: 있다면
- **P2037 (GitHub username)**: Yesol-Pilot
- **P859 (sponsor)**: Neo Genesis (SBU 들에 대해)
- **P127 (owned by)**: Q-NeoGenesis (SBU 들에 대해)

## 주의사항

- **출처 (reference)** 는 가능한 한 추가 — verifiable source 가 없으면 community 가 statement 삭제
- **회사 직접 편집은 OK** (Wikidata 는 Wikipedia 와 달리 COI 규정이 약함). 단 Wikipedia 와 다르게 **Wikidata 도 verifiable source 는 요구함**
- **이미지** 는 Commons 에 별도 업로드 필요 (CC0/CC-BY 라이선스만 가능)

## 다음 단계

등록 완료 후 owner 는 Q-ID 들을 다음 파일들에 반영:
- `src/landing/src/app/layout.tsx` ORGANIZATION_SCHEMA.sameAs
- `.agent/knowledge/wikidata-entities/registered.json` (새로 생성, Q-ID 매핑 보관)
- 각 SBU README / package.json metadata
