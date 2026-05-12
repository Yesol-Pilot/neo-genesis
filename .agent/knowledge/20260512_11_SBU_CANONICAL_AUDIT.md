# 11 SBU Canonical Reference Audit — 2026-05-12

> 작성자: Strategy Lead Claude Opus 4.7
> 목적: 11 SBU 가 neogenesis.app + Wikidata Q139569680 + parentOrganization Schema 명시 emit 하는지 확인
> 컨텍스트: Common Crawl 미인덱싱 (3 snapshot 모두). 진입 가속 = inbound link 강화. 11 SBU 가 가장 큰 자체 inbound source.

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

**EthicaAI offline** ⚠️ P0 — 다음 commit cycle 이내 fix. NeurIPS 2026 submission 박제 사이트가 다운 = citation graph credibility 손상.

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
| P0 | EthicaAI 사이트 부활 (다운 상태 fix) | owner action (DNS / Vercel deploy 점검) |
| P0 | 11 SBU 모두 parentOrganization + Wikidata sameAs Schema 추가 | per-SBU repo 별 PR (자율 가능, 시간 소요) |
| P1 | toolpick.dev apex DNS 직접 serve (308 redirect 제거) | owner action (DNS) |
| P1 | WhyLab 의 6-mention 패턴을 다른 10 SBU 에 복제 | SBU repo edit (자율) |
| P2 | 11 SBU footer 에 visible "Part of Neo Genesis (Wikidata Q139569680)" 텍스트 | 자율 |

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
