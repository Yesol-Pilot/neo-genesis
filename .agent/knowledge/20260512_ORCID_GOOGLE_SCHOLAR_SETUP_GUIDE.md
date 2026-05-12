# ORCID + Google Scholar Setup Guide — Owner Action

> 작성자: Strategy Lead Claude Opus 4.7
> 작성일: 2026-05-12
> 목적: founder (Yesol Heo) 의 ORCID + Google Scholar 학술 citation graph 진입
> Strategy v1 §3.2 #11 (ORCID) + #12 (Google Scholar) 권고 실행

---

## 🚨 Owner Action 필요 (5분, 무료)

**Safety rule 박제**: Claude 는 owner 의 계정을 직접 생성할 수 없음. 본 문서는 owner 가 직접 5분 작업으로 ORCID + Google Scholar profile 을 생성하기 위한 **pre-filled 데이터 + 단계별 가이드**.

자동 사후 처리 (Claude G1 자율):
- ORCID iD 발급 후 → Wikidata Q139569708 P496 (ORCID iD) 추가 자동 박제
- ORCID iD → Schema.org Person.sameAs 자동 추가
- ORCID iD → llms-full.txt 외부 ID graph 자동 추가
- ORCID iD → 11 OpenAlex works 자동 link 요청 (ORCID 가 OpenAlex 와 자동 sync)
- Google Scholar profile URL → 동일 graph 추가

---

## 1. ORCID Profile 생성 (3분)

### Step 1: 계정 생성
- URL: https://orcid.org/register
- Primary Email: `dpthf1537@gmail.com`
- Given Names: `Yesol`
- Family Name: `Heo`
- Password: 새로 생성 (Claude 가 알 필요 없음, owner 만 보관)

### Step 2: Profile 박제 정보 (그대로 복사 가능)

**Affiliations / Employment:**
- Organization: `Neo Genesis` (Wikidata Q139569680)
- Role: `Founder & Sole Operator`
- City: `Seoul`
- Country: `Korea, Republic of`
- Start Date: `2024-01-01`
- End Date: (Present)

**Biography (300-500 자):**
```
Yesol Heo (허예솔) is the founder and sole operator of Neo Genesis (https://neogenesis.app), an AI-native automation company operating 11 live SaaS products through a single autonomous AI engine (HIVE MIND). Heo publishes original research and operational evidence under CC-BY-4.0 license across 9 Hugging Face datasets and submitted multi-agent cooperative-constraint research to NeurIPS 2026 (EthicaAI). Research interests: multi-agent reinforcement learning, retrieval-augmented generation, causal inference for AI-generated code (WhyLab), autonomous content quality gating (V-Score formula). Wikidata: Q139569708. ORCID-linked OpenAlex: A5126028658.
```

**Keywords (5-10):**
- multi-agent reinforcement learning
- retrieval-augmented generation
- AI-native automation
- causal inference
- autonomous content publishing
- cooperative constraint learning
- generative engine optimization
- 1-person operation systems
- Trust signal manufacturing
- AI corpus citation

**Website / URLs (4):**
1. https://heoyesol.kr (Portfolio)
2. https://neogenesis.app (Neo Genesis homepage)
3. https://huggingface.co/neogenesislab (Hugging Face profile)
4. https://github.com/Yesol-Pilot (GitHub profile)

**External Identifiers (auto-add via ORCID interface):**
- OpenAlex Author ID: `A5126028658` (already exists)
- Wikidata: `Q139569708` (already exists)

### Step 3: Works 등록 (11개 OpenAlex works 자동 sync)
- Profile 설정 후 → "Add works" → "Search & link" → "OpenAlex"
- Sign in to OpenAlex (no separate account needed for read-only sync)
- 11 works 자동 발견 (이미 OpenAlex 에 등록된 EthicaAI / WhyLab papers 포함)
- "Add to ORCID record" 클릭

### Step 4: Visibility 설정
- Profile: **Everyone** (public, AI corpus inclusion 가능)
- Employment: **Everyone**
- Works: **Everyone**

### Step 5: 새 ORCID iD 보고 (Claude 에게 paste)
ORCID 가입 완료 시 발급되는 16자리 ID (`0000-0000-XXXX-XXXX` 형식)를 Claude 에게 paste 하면:
1. CREDENTIAL_BIBLE.md 자동 박제
2. Wikidata Q139569708 P496 추가 (BotPassword 사용)
3. layout.tsx ORGANIZATION_SCHEMA.sameAs + Person.sameAs 자동 추가
4. llms-full.txt external identifier table 갱신

---

## 2. Google Scholar Profile 생성 (2분)

### Step 1: 계정 생성
- URL: https://scholar.google.com/citations?view_op=new_profile
- **요구**: Google 계정 + 학술 이메일 (보통 .edu 또는 회사 도메인). `dpthf1537@gmail.com` 만으로는 unverified status 가능 — Neo Genesis 도메인 `neogenesis.research@gmail.com` 도 시도 권고

### Step 2: Profile 박제 정보

**Name**: `Yesol Heo`
**Affiliation**: `Neo Genesis` (또는 `Founder, Neo Genesis`)
**Verified Email**: `neogenesis.research@gmail.com` (선호) 또는 `dpthf1537@gmail.com`
**Homepage**: `https://heoyesol.kr` 또는 `https://neogenesis.app`

**Areas of Interest** (5):
- Multi-agent reinforcement learning
- Retrieval-augmented generation
- Causal inference
- AI automation
- Generative engine optimization

### Step 3: Articles 자동 발견
- Google Scholar 가 ORCID iD 또는 author name 기반으로 articles 자동 검색
- ORCID 가 먼저 등록되어 있으면 sync 빠름 (~24-72시간)
- 발견된 articles 검토 후 "Add" 클릭

### Step 4: ORCID 연결
- Profile → Edit → "Add ORCID iD" → ORCID 16자리 ID paste
- 양방향 sync 활성화

### Step 5: 새 Google Scholar URL 보고
profile URL 형식: `https://scholar.google.com/citations?user=<userid>`
이 URL 을 Claude 에게 paste 하면:
1. CREDENTIAL_BIBLE.md 박제
2. layout.tsx Person.sameAs 추가
3. llms-full.txt external ID 갱신

---

## 3. Auto-sync 효과 (owner action 후 자동 발생)

### 즉시 (24시간 이내)
- ORCID iD 가 OpenAlex 와 자동 sync (이미 11 works 존재)
- Google Scholar 가 ORCID 정보 가져옴

### 1-2주 이내
- Semantic Scholar 가 ORCID 발견 → author profile 자동 생성
- ResearchGate 가 ORCID 발견 → invite 도착 (선택적 가입)

### 1-3개월 이내
- 9 Zenodo DOI 가 ORCID record 에 자동 attach (이미 OpenAlex 연결 상태)
- HuggingFace 의 9 datasets 가 새 sameAs (ORCID) 인지

### Long-term 효과
- Wikipedia notability gate (WP:NBIO) 의 academic citation requirement 진전
- Google Knowledge Panel 의 founder bio 강화
- AI agent 가 "Yesol Heo" 검색 시 ORCID-anchored 정체성 graph 발견

---

## 4. Owner Action Checklist

- [ ] **ORCID 가입** (3분, https://orcid.org/register) — §1 의 박제 데이터 복사
- [ ] **ORCID Works 11개 sync** (OpenAlex 자동 import)
- [ ] **ORCID iD Claude 에 paste** (자동 후처리 트리거)
- [ ] **Google Scholar 가입** (2분, https://scholar.google.com/citations?view_op=new_profile)
- [ ] **Google Scholar 에 ORCID iD 연결**
- [ ] **Google Scholar URL Claude 에 paste** (자동 후처리 트리거)

---

## 5. 박제 위치 (owner action 완료 후 Claude 자동 update)

| 위치 | 추가 내용 |
|---|---|
| `D:/00.test/CREDENTIAL_BIBLE.md` | ORCID iD + Google Scholar URL + 로그인 email |
| `src/landing/src/app/layout.tsx` | ORGANIZATION_SCHEMA.sameAs + Person.sameAs |
| `src/landing/src/app/about/page.tsx` | PERSON_SCHEMA.sameAs (이미 12개 → +2) |
| `src/landing/src/app/llms-full.txt/route.ts` | External identifier table |
| `.agent/knowledge/20260512_AI_CORPUS_CITATION_STRATEGY_v1.md` | §2.B.B7 / §2.B.B8 상태 ✅ 갱신 |
| Wikidata Q139569708 | P496 (ORCID iD) + P1960 (Google Scholar ID) BotPassword 직접 등록 |

---

## 6. 비용 / 위험

**비용**: $0
**시간**: owner 5분 + Claude 자동 후처리 10분
**리스크**: 없음 (ORCID + Google Scholar 모두 표준 academic infrastructure)
**Reversibility**: 100% (profile 삭제 가능)

owner 5분 action 후 본 문서 마지막 섹션 (§5 박제 위치) 의 자동 후처리 진행.
