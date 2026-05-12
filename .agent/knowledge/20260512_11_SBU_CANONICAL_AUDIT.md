# 11 SBU Canonical Reference Audit — 2026-05-12 (v1.1 정정)

> 작성자: Strategy Lead Claude Opus 4.7
> 목적: 11 SBU 가 neogenesis.app + Wikidata Q139569680 + parentOrganization Schema 명시 emit 하는지 확인
> 컨텍스트: Common Crawl 미인덱싱 (3 snapshot 모두). 진입 가속 = inbound link 강화. 11 SBU 가 가장 큰 자체 inbound source.

## ⏸️ v1.1 정정 — Blind Review Anonymity 발견

owner clarification (2026-05-12 후속): "블라인드 심사에 문제가 될까봐 다운시켰을걸"

**EthicaAI 다운 = P0 운영 issue X / Blind Review Anonymity 의도적 보호 O** 로 정정:
- ethicaai.neogenesis.app dedicated site = author Yesol Heo + project info + Heo 2026 finding 노출 surface
- 블라인드 심사 룰: double-blind venue (NeurIPS / ICML 등) 심사 중 reviewer 가 google 검색 시 author identity 추적 가능 = anonymity 위반
- **즉, EthicaAI 다운 = 정상 운영 결정. 부활 권고 X.**
- 본 audit 의 "EthicaAI 부활" 권고 = **취소** (owner intent 와 충돌)

---

## §0 결론 (Cold Honest)

11 SBU 중:
- **9/11 reachable** (200 OK)
- **11/11 가 neogenesis.app 단순 언급** (robots.txt / sitemap / 일부 텍스트)
- **0/11 가 Schema.org parentOrganization @id graph emit** (P0 갭)
- **0/11 가 Wikidata Q139569680 sameAs emit** (P0 갭)
- **2/11 reachability 문제** (toolpick redirect / ethicaai 다운)

**진단**: SBU → 부모 사이트 Schema.org 그래프 부재 = CC 가 SBU 페이지를 인덱싱하더라도 neogenesis.app 부모 URL 강화 효과 미미. 단순 텍스트 reference 만으로는 entity graph 약함.

---

## §1 측정 결과 (2026-05-12)

| SBU | 도메인 | HTTP | neogenesis.app | Q139569680 | parentOrganization Schema |
|---|---|---|---|---|---|
| ToolPick | www.toolpick.dev | 200 (308 redirect) | 1 | 0 | 0 |
| K-OTT | kott.kr | 200 | 1 | 0 | 0 |
| UR WRONG | ur-wrong.com | 200 | 1 | 0 | 0 |
| ReviewLab | review.neogenesis.app | 200 | 1 | 0 | 0 |
| WhyLab | whylab.neogenesis.app | 200 | 6 | 0 | 0 |
| EthicaAI | ethicaai.neogenesis.app | **000** ❌ | n/a | n/a | n/a |
| FinStack | finstack.neogenesis.app | 200 | 1 | 0 | 0 |
| AIForge | aiforge.neogenesis.app | 200 | 1 | 0 | 0 |
| SellKit | sellkit.neogenesis.app | 200 | 1 | 0 | 0 |
| DeployStack | deploystack.neogenesis.app | 200 | 1 | 0 | 0 |
| CraftDesk | craftdesk.neogenesis.app | 200 | 1 | 0 | 0 |

### 발견 detail

**WhyLab (6 mentions)** — 다른 SBU 의 6배. WhyLab/dashboard 가 가장 강한 인용 site (research-heavy 컨텍스트). 다른 10 SBU 가 따라야 할 reference.

**EthicaAI offline** ⏸️ **Blind Review Anonymity 보호 (정정)** — owner 의도적 다운. 심사 종료 후 부활 검토. 본 commit cycle 이내 부활 권고 X.

**WhyLab inconsistency 발견 (owner 확인 필요)** — `whylab.neogenesis.app` 은 LIVE 상태 (200, 6 mentions). EthicaAI 와 동일 블라인드 심사 진행 중인데 사이트 alive. 가설:
- (a) owner 가 WhyLab 도 다운 의향이지만 미수행 (owner action queue 추가)
- (b) WhyLab 심사 상태가 EthicaAI 와 다름 (예: 이미 reject 통보 → anonymity 무관)
- (c) WhyLab 사이트 content 의 author identity 노출 정도가 EthicaAI 보다 낮음
- 단정 X — owner clarification 권고

**ToolPick 308 redirect** — `toolpick.dev` → `www.toolpick.dev`. crawler 가 follow 하지만 추가 hop = 효율 ↓. CF Page Rules / DNS apex 직접 serve 검토 필요.

---

## §2 Schema.org 그래프 강화 권고

각 SBU 마다 다음 Schema 추가 권고 (per page Footer 또는 root layout):

```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "@id": "https://<sbu>.neogenesis.app/#organization",
  "name": "<SBU Name>",
  "url": "https://<sbu>.neogenesis.app",
  "parentOrganization": {
    "@type": "Organization",
    "@id": "https://neogenesis.app/#organization",
    "name": "Neo Genesis",
    "url": "https://neogenesis.app",
    "sameAs": [
      "https://www.wikidata.org/wiki/Q139569680",
      "https://github.com/Yesol-Pilot",
      "https://huggingface.co/neogenesislab"
    ]
  },
  "sameAs": "https://www.wikidata.org/wiki/<SBU_Q_ID>"
}
```

### SBU 별 Wikidata Q-ID matrix

| SBU | Q-ID |
|---|---|
| UR WRONG | Q139569710 |
| ToolPick | Q139569711 |
| ReviewLab | Q139569712 |
| K-OTT | Q139569715 |
| WhyLab | Q139569716 |
| EthicaAI | Q139569718 |
| FinStack | Q139569720 |
| AIForge | Q139569724 |
| SellKit | Q139569725 |
| DeployStack | Q139569726 |
| CraftDesk | Q139569727 |

---

## §3 우선순위 fix 권고

| 우선순위 | 작업 | 자율 가능? |
|---|---|---|
| ~~P0~~ | ~~EthicaAI 사이트 부활~~ | **⏸️ HOLD — Blind Review Anonymity 의도적 다운, 심사 종료 후 owner 재량** |
| ⏸️ | WhyLab 사이트도 동일 logic 으로 다운 검토 (owner clarification) | owner G2 |
| P1 | 11 SBU 모두 parentOrganization + Wikidata sameAs Schema 추가 | **⚠️ 블라인드 심사 중 SBU 는 제외** (EthicaAI / WhyLab 둘 다 제외). 9 SBU 만 자율 가능 |
| P1 | toolpick.dev apex DNS 직접 serve (308 redirect 제거) | owner action (DNS) |
| P2 | (블라인드 미충돌 9 SBU) footer 에 visible "Part of Neo Genesis (Wikidata Q139569680)" 텍스트 | 자율 |

---

## §4 ROI 예측

11 SBU 모두 Schema.org parentOrganization 강화 후:
- AI crawler 가 SBU 페이지 인덱싱 시 → 부모 entity 직접 발견 + sameAs Wikidata 자동 추적
- Common Crawl 의 webgraph 구조에서 neogenesis.app 의 PageRank 강화
- Wikidata Q139569680 P749 cluster 가 자동 인지

예상 효과:
- CC 다음 snapshot (예상 CC-MAIN-2026-22) 진입 가능성 ↑
- AI agent 의 brand mention 정확도 ↑ (현 12.9% baseline 기준)
- Trust signal gap 일부 closure (0% → 5%+ canonical URL citation rate, 6개월 lag)

---

## §5 자율 진행 가능 vs Owner Gate

### 자율 G1 (Strategy Lead, 본 세션 이후 가능)
- 각 SBU repo 의 `layout.tsx` / root Schema 추가 PR 작성
- 11 PR (SBU별 1) 또는 1 monorepo PR (만약 sub-domain 공통 wrapper 존재 시)
- 시간 estimate: ~6-10h (PR 11개 작성 + 검증)

### Owner G2
- EthicaAI 다운 fix (DNS / Vercel)
- ToolPick DNS apex serve
- Cloudflare DNS / WAF 정책 변경 필요시

---

## §6 박제

본 audit baseline:
- 2026-05-12 측정: 0/11 SBU 가 parentOrganization Schema emit
- 다음 audit cycle: 한 달 후 (다음 cron 결과 reuse)

11 SBU Schema 강화 작업 = **Week 2-3 자율 진행 후보 추가**. owner 진행 ack 시 PR 11개 자율 작성.

작성: 2026-05-12, Strategy Lead Claude Opus 4.7
